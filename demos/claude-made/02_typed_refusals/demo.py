"""Demo 02 — every way the gateway can say no, as a typed exception.

`classify()` maps the proxy's rejection shapes onto an exception hierarchy, so
governance outcomes are something you branch on rather than something you parse.
The discriminator is deliberately *not* the status code: a PII block is a 403 but
is not an auth failure, and an injection block is identified by a header rather
than by its status.

This demo needs nothing — no gateway, no simulator, no credentials. It loads the
captured fixtures **out of the installed SDK** (`donkey_kit.simulator.fixtures`)
rather than keeping copies here, which is deliberate: those are the same bytes
`classify()` is unit-tested against and the same bytes `donkey mock`
serves, so if a capture ever drifts, this demo and the SDK's own tests fail
together.

    python demos/claude-made/02_typed_refusals/demo.py
"""

from __future__ import annotations

import httpx
from donkey_kit import (
    AuthError,
    ContentSafetyBlocked,
    Donkey,
    DonkeyConfig,
    GatewayUnavailable,
    PIIDetected,
    PolicyViolation,
    PromptInjectionBlocked,
    TokenBudgetExceeded,
)
from donkey_kit.core.errors import UpstreamRequestError, classify, gateway_unavailable
from donkey_kit.simulator.fixtures import load

from _harness import narrate as say
from _harness import preflight, redact

# The documented rejection shapes plus the consumer-auth 401, in the order
# that tells the story: auth, then the policy refusals, then upstream.
SHAPES: tuple[tuple[str, str], ...] = (
    ("client-id-missing", "consumer auth — a genuinely missing/wrong client id"),
    ("pii-detected", "PII policy — a 403 that is NOT an auth failure"),
    ("token-rate-limit", "token budget — a 429 with an EMPTY body; state is header-only"),
    ("injection-protection", "prompt injection — header discriminator; documented, not yet live-captured"),
    ("regex-prompt-guard", "regex prompt guard — 403 keyed on matched_patterns, not auth"),
    ("content-safety", "Azure content safety — 403 keyed on a vendor reject header"),
    ("content-moderation", "undiscriminated moderation — no live capture, left unnamed"),
    ("model-not-found", "upstream passthrough — the provider's own error, not a policy"),
    ("upstream-5xx", "provider failure — retryable, unlike every refusal above"),
)

# What each shape should classify to. Asserting this in the demo is the point:
# the taxonomy is a contract, not a suggestion.
EXPECTED: dict[str, type[Exception]] = {
    "client-id-missing": AuthError,
    "pii-detected": PIIDetected,
    "token-rate-limit": TokenBudgetExceeded,
    "injection-protection": PromptInjectionBlocked,
    "regex-prompt-guard": PromptInjectionBlocked,
    "content-safety": ContentSafetyBlocked,
    "content-moderation": PolicyViolation,
    "model-not-found": UpstreamRequestError,
}


def _rebuild(shape: str) -> httpx.Response:
    """Reconstruct the captured response exactly as the wire delivered it."""
    fixture = load(shape)
    headers = dict(fixture.headers)
    if fixture.content_type and "content-type" not in headers:
        headers["content-type"] = fixture.content_type
    # content-length from the capture would contradict the body we attach.
    headers.pop("content-length", None)
    return httpx.Response(fixture.status, headers=headers, content=fixture.body)


def _detail(error: Exception) -> list[tuple[str, object]]:
    """The attributes worth showing for whichever exception came back."""
    out: list[tuple[str, object]] = []
    for attr in (
        "policy",
        "entities",
        "categories",
        "retry_after",
        "code",
        "error_type",
        "param",
    ):
        value = getattr(error, attr, None)
        if value not in (None, [], ""):
            out.append((attr, value))
    return out


def act_1_the_taxonomy() -> None:
    say.section("Nine captured responses through classify()")
    say.code(
        """
        from donkey_kit.core.errors import classify

        governed = classify(response)     # -> a typed DonkeyError subclass
        """
    )

    for shape, description in SHAPES:
        response = _rebuild(shape)
        error = classify(response)

        print()
        say.field(shape, description)
        say.field("  HTTP", response.status_code, raw=True)
        say.field("  classified as", type(error).__name__)
        for attr, value in _detail(error):
            say.field(f"  .{attr}", value, raw=(attr != "policy"))

        expected = EXPECTED.get(shape)
        if expected is not None and not isinstance(error, expected):
            say.fail(f"expected {expected.__name__}")


def act_2_what_the_hierarchy_buys() -> None:
    say.section("Why the hierarchy is shaped this way")

    pii = classify(_rebuild("pii-detected"))
    budget = classify(_rebuild("token-rate-limit"))
    safety = classify(_rebuild("content-safety"))
    regex = classify(_rebuild("regex-prompt-guard"))
    upstream = classify(_rebuild("model-not-found"))
    unavailable = gateway_unavailable(
        base_url="http://127.0.0.1:9",
        cause=httpx.ConnectError("connection refused"),
    )

    checks = [
        (
            "a PII block is a policy refusal, not an auth error",
            isinstance(pii, PolicyViolation) and not isinstance(pii, AuthError),
        ),
        (
            "a token-budget 429 is also a policy refusal — so one `except "
            "PolicyViolation` catches both",
            isinstance(budget, PolicyViolation),
        ),
        (
            "content-safety is ContentSafetyBlocked, still a PolicyViolation",
            isinstance(safety, ContentSafetyBlocked) and isinstance(safety, PolicyViolation),
        ),
        (
            "regex-prompt-guard is PromptInjectionBlocked with its own policy name",
            isinstance(regex, PromptInjectionBlocked)
            and getattr(regex, "policy", None) == "regex-prompt-guard",
        ),
        (
            "an upstream 400 is NOT a policy refusal — it is your request that is "
            "wrong, not the gateway saying no",
            not isinstance(upstream, PolicyViolation),
        ),
        (
            "the budget refusal carries retry_after, parsed from x-token-reset "
            "(milliseconds, not an epoch)",
            getattr(budget, "retry_after", None) is not None,
        ),
        (
            "GatewayUnavailable is not a PolicyViolation — nothing was refused, "
            "the request never arrived",
            not isinstance(unavailable, PolicyViolation),
        ),
        (
            "a transport failure has no request_id — there was no response to "
            "read the gateway's id from",
            unavailable.request_id is None,
        ),
    ]
    for description, passed in checks:
        (say.ok if passed else say.fail)(description)


def act_3_how_you_write_it() -> None:
    say.section("What that looks like in your agent")
    say.code(
        """
        try:
            response = await client.responses.create(model=..., input=...)
        except openai.APIStatusError as exc:
            raise classify(exc.response) from exc

        except PIIDetected as e:          # 403, and e.entities says what tripped
            redact_and_retry(e.entities)
        except ContentSafetyBlocked as e: # 403, e.categories is the moderation analog
            revise(e.categories)
        except TokenBudgetExceeded as e:  # 429, terminal — never retry it
            await donkey.budget.wait_for_reset()
        except PolicyViolation as e:      # any other gateway refusal
            escalate(e.remediation)
        except GatewayUnavailable as e:   # NO response — not a refusal
            diagnose(e.base_url, e.cause) # checkpoint / shed / donkey doctor
        except ModelSubstituted as e:     # NOT classify() — you opted in (demo 10)
            pin_or_accept(e.served_model)
        except UpstreamRequestError as e: # your request was wrong (e.code)
            fix(e.code)
        except UpstreamModelError:        # provider 5xx — this one IS retryable
            retry_with_backoff()
        """
    )


def act_4_honesty() -> None:
    say.section("What is typed from docs, and what is still unnamed")
    say.note(
        "Six of these shapes are live-verified against a real proxy: consumer "
        "auth, PII, token rate limit, upstream passthrough, regex prompt guard, "
        "and Azure content-safety. Header-based injection-protection and Bedrock "
        "guardrails stay typed from the documented wire shapes — classify() still "
        "produces PromptInjectionBlocked / ContentSafetyBlocked — because no "
        "proxy running those policies is deployed to capture. Named because the "
        "shape is specified, not because a capture has landed yet."
    )
    print()
    moderation = classify(_rebuild("content-moderation"))
    say.field("content-moderation", type(moderation).__name__)
    say.field("remediation", redact.text(getattr(moderation, "remediation", "")))
    print()
    say.note(
        "An undiscriminated content-moderation 4xx still falls through to a generic "
        "PolicyViolation. That leftover shape has never been captured from a live "
        "gateway, so it is left unnamed rather than given a class that would imply "
        "more certainty than exists."
    )
    print()
    say.section("AuthError names two credential planes")
    say.field("data-plane default", AuthError.remediation.split(".")[0] + ".")
    say.field(
        "connected_app_remediation",
        AuthError.connected_app_remediation.split(".")[0] + ".",
    )
    say.note(
        "classify() on a CIE 401 uses the data-plane default (DONKEY_LLM_PROXY_*). "
        "A control-plane token fetch overrides it with connected_app_remediation "
        "(ANYPOINT_CLIENT_*). Same class, two next steps — mixing those pairs is "
        "the usual first-day failure. The model-wallet JWT ingress is demo 13; "
        "classify() has no dedicated JWT types yet."
    )
    print()
    say.note(
        "ModelSubstituted is not in the table above because it is not a gateway "
        "refusal and classify() never produces it. It is raised by the transport "
        "when you opt into on_model_substitution='raise' and the gateway serves a "
        "different model than you asked for. Demo 10."
    )
    print()
    say.note(
        "GatewayUnavailable is the other type classify() never produces: there is "
        "no HTTP response to classify. DNS, connection refused, TLS, timeout — "
        "the transport wraps those as a typed DonkeyError so a long-running agent "
        "can tell 'lost the gateway' from a policy refusal without matching raw "
        "httpx exceptions. It is not retried. Act 5 actually raises it."
    )


def _unwrap(exc: BaseException, cls: type[GatewayUnavailable]) -> GatewayUnavailable | None:
    """The OpenAI client wraps transport-raised DonkeyErrors as APIConnectionError."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        if isinstance(current, cls):
            return current
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return None


def act_5_when_the_gateway_is_gone() -> None:
    say.section("A refused connection, typed — not a raw httpx error")
    say.code(
        """
        donkey = Donkey(DonkeyConfig(llm_proxy_url="http://127.0.0.1:9/", ...))
        client.responses.create(...)   # nothing is listening
        # -> GatewayUnavailable, not ConnectError
        """
    )
    cfg = DonkeyConfig(
        llm_proxy_url="http://127.0.0.1:9/",
        llm_proxy_client_id="demo-client-id-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
        timeout_s=2.0,
        max_retries=0,
    )
    raised: BaseException | None = None
    error: GatewayUnavailable | None = None
    with Donkey(cfg) as donkey:
        client = donkey.openai(sync=True)
        try:
            client.responses.create(model="gpt-4o", input="hello")
            say.fail("expected GatewayUnavailable")
            return
        except Exception as exc:  # noqa: BLE001 — OpenAI wraps the transport error
            raised = exc
            error = _unwrap(exc, GatewayUnavailable)

    if error is None or raised is None:
        say.fail(
            f"raised {type(raised).__name__ if raised else 'nothing'}, "
            "not GatewayUnavailable"
        )
        return

    if type(raised) is not GatewayUnavailable:
        say.field("raised", type(raised).__name__)
        say.ok("cause is GatewayUnavailable — same wrap as ModelSubstituted (demo 10)")
    else:
        say.ok("GatewayUnavailable — the request never left the building")
    say.field("base_url", error.base_url)
    say.field("cause", type(error.cause).__name__ if error.cause else None)
    say.field("request_id", error.request_id, raw=True)
    say.field("call_id", error.call_id, raw=True)
    print()
    say.note(redact.text(error.remediation))
    print()
    if isinstance(error, PolicyViolation):
        say.fail("GatewayUnavailable must not be a PolicyViolation")
    else:
        say.ok("not a PolicyViolation — nothing was refused, because nothing arrived")


def main() -> None:
    act_1_the_taxonomy()
    say.pause()
    act_2_what_the_hierarchy_buys()
    say.pause()
    act_3_how_you_write_it()
    act_4_honesty()
    say.pause()
    act_5_when_the_gateway_is_gone()


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 02 — typed refusals",
        subtitle="The gateway's rejection shapes, mapped to exceptions you can branch on.",
        target="offline",
        extras=("openai",),
    )
