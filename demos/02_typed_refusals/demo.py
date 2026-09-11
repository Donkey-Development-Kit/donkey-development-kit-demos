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

    python demos/02_typed_refusals/demo.py
"""

from __future__ import annotations

import httpx
from donkey_kit import (
    AuthError,
    PIIDetected,
    PolicyViolation,
    PromptInjectionBlocked,
    TokenBudgetExceeded,
)
from donkey_kit.core.errors import UpstreamRequestError, classify
from donkey_kit.simulator.fixtures import load

from _harness import narrate as say
from _harness import preflight, redact

# The six documented rejection shapes plus the consumer-auth 401, in the order
# that tells the story: auth, then the policy refusals, then upstream.
SHAPES: tuple[tuple[str, str], ...] = (
    ("client-id-missing", "consumer auth — a genuinely missing/wrong client id"),
    ("pii-detected", "PII policy — a 403 that is NOT an auth failure"),
    ("token-rate-limit", "token budget — a 429 with an EMPTY body; state is header-only"),
    ("injection-protection", "prompt injection — identified by a header, not a status"),
    ("content-moderation", "content moderation — shape not yet captured live"),
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
    for attr in ("policy", "entities", "retry_after", "code", "error_type", "param"):
        value = getattr(error, attr, None)
        if value not in (None, [], ""):
            out.append((attr, value))
    return out


def act_1_the_taxonomy() -> None:
    say.section("Seven captured responses through classify()")
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
    upstream = classify(_rebuild("model-not-found"))

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
            "an upstream 400 is NOT a policy refusal — it is your request that is "
            "wrong, not the gateway saying no",
            not isinstance(upstream, PolicyViolation),
        ),
        (
            "the budget refusal carries retry_after, parsed from x-token-reset "
            "(milliseconds, not an epoch)",
            getattr(budget, "retry_after", None) is not None,
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
        except TokenBudgetExceeded as e:  # 429, terminal — never retry it
            await donkey.budget.wait_for_reset()
        except PolicyViolation as e:      # any other gateway refusal
            escalate(e.remediation)
        except UpstreamRequestError as e: # your request was wrong (e.code)
            fix(e.code)
        except UpstreamModelError:        # provider 5xx — this one IS retryable
            retry_with_backoff()
        """
    )


def act_4_honesty() -> None:
    say.section("What is not typed yet")
    say.note(
        "Four of these shapes are live-verified against a real proxy: consumer "
        "auth, PII, token rate limit, and upstream passthrough. Injection is typed "
        "by its header, and its body is still pending a live capture. Content "
        "moderation has no captured shape at all, so it deliberately falls through "
        "to a generic PolicyViolation instead of being given a class that would "
        "imply more certainty than exists."
    )
    print()
    moderation = classify(_rebuild("content-moderation"))
    say.field("content-moderation", type(moderation).__name__)
    say.field("remediation", redact.text(getattr(moderation, "remediation", "")))
    print()
    say.note(
        "ContentSafetyBlocked exists in the taxonomy but classify() never produces "
        "it, and donkey.simulate() refuses to inject it — an unverified shape is "
        "left unclaimed rather than guessed at."
    )


def main() -> None:
    act_1_the_taxonomy()
    say.pause()
    act_2_what_the_hierarchy_buys()
    say.pause()
    act_3_how_you_write_it()
    act_4_honesty()


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 02 — typed refusals",
        subtitle="The gateway's rejection shapes, mapped to exceptions you can branch on.",
        target="offline",
    )
