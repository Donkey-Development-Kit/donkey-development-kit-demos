"""Demo 15 — the gateway passes the provider through; the SDK absorbs the difference.

The gateway does not rewrite what the upstream provider says. It forwards the
provider's own request id, the provider's own error envelope, and — for the
guardrail policies — a vendor-named reject header. So the same question ("what
id do I quote?", "was my request wrong?", "which guardrail said no?") has a
different wire answer on OpenAI, Azure, Bedrock and Gemini routes.

This demo shows each difference and the one field or type the SDK hands you
instead. Offline: shapes the SDK packages come from `donkey_kit.simulator.fixtures`;
the Bedrock and Gemini ones are rebuilt inline from their live captures, with
only the discriminating headers kept.

    python demos/claude-made/15_provider_passthrough/demo.py
"""

from __future__ import annotations

import importlib.util
import warnings

import httpx
from donkey_kit import ContentSafetyBlocked, Donkey, DonkeyConfig, PolicyViolation
from donkey_kit.core.errors import UpstreamRequestError, classify
from donkey_kit.core.lastcall import REQUEST_ID_HEADERS, LastCall
from donkey_kit.simulator.fixtures import load

from _harness import narrate as say
from _harness import preflight, redact

# Shapes from the live captures (SDK tests/fixtures), reduced to the headers
# classify() and LastCall actually read. Ids are demo placeholders.
BEDROCK_REJECT = httpx.Response(
    403,
    headers={
        "x-llm-proxy-bedrock-guardrail-action": "reject",
        "x-llm-proxy-bedrock-guardrail-reason": "content_filter",
        "x-amzn-requestid": "demo-amzn-request-id",
    },
    json={"error": "Content blocked by Amazon Bedrock Guardrails", "categories": ["content_filter"]},
)
GEMINI_400 = httpx.Response(
    400,
    headers={
        "x-llm-proxy-model-based-routing-success": (
            "Request passed through without model-based routing."
        ),
    },
    json=[
        {
            "error": {
                "code": 400,
                "message": "Missing or invalid Authorization header.",
                "status": "INVALID_ARGUMENT",
            }
        }
    ],
)
# What each provider route sends on a 200 (live probe, docs/verified-apis.md §3).
PROVIDER_200S: tuple[tuple[str, dict[str, str]], ...] = (
    ("OpenAI", {"x-request-id": "req_demo-openai"}),
    ("Azure OpenAI", {"x-request-id": "demo-azure-id", "apim-request-id": "demo-apim-id"}),
    ("Bedrock", {"x-amzn-requestid": "demo-amzn-request-id"}),
    ("no provider id", {}),
)


def _rebuild(shape: str) -> httpx.Response:
    fixture = load(shape)
    headers = dict(fixture.headers)
    if fixture.content_type and "content-type" not in headers:
        headers["content-type"] = fixture.content_type
    headers.pop("content-length", None)
    return httpx.Response(fixture.status, headers=headers, content=fixture.body)


def act_1_request_id() -> None:
    say.step(1, "The request id is the provider's, and its header name varies")
    say.code(
        """
        donkey.last_call.request_id    # on a 200
        error.request_id               # on a refusal — same resolver
        """
    )
    for provider, headers in PROVIDER_200S:
        response = httpx.Response(200, headers=headers)
        record = LastCall.from_response(response)
        print()
        say.field(provider, ", ".join(headers) or "(none)", raw=True)
        say.field("  headers.get('x-request-id')", response.headers.get("x-request-id"), raw=True)
        say.field("  LastCall.request_id", record.request_id, raw=True)
    print()
    say.field("resolution order", " → ".join(REQUEST_ID_HEADERS), raw=True)
    bedrock = classify(BEDROCK_REJECT)
    if bedrock.request_id == "demo-amzn-request-id":
        say.ok("a Bedrock refusal carries x-amzn-requestid — not a silent None")
    say.note(
        "The gateway does not mint its own id; it forwards the upstream "
        "provider's. Bedrock routes send no x-request-id at all, so reading that "
        "one header would give None on every Bedrock call. request_id is what "
        "the provider's support team needs. The gateway-side join key is "
        "correlation_id (X-Correlation-Id, echoed — demo 06)."
    )


def act_2_two_guardrail_vendors() -> None:
    say.step(2, "Two guardrail vendors, one exception")
    say.code(
        """
        except ContentSafetyBlocked as e:   # Azure OR Bedrock
            revise(e.categories)
        """
    )
    for label, response in (
        ("Azure Content Safety", _rebuild("content-safety")),
        ("Amazon Bedrock Guardrails", BEDROCK_REJECT),
    ):
        error = classify(response)
        vendor_header = next(k for k in response.headers if k.endswith("-action"))
        print()
        say.field(label, f"HTTP {response.status_code}", raw=True)
        say.field("  reject header", vendor_header, raw=True)
        say.field("  classified as", type(error).__name__)
        say.field("  .categories", getattr(error, "categories", None), raw=True)
        say.field("  message", redact.text(str(error)))
        if not isinstance(error, ContentSafetyBlocked):
            say.fail("expected ContentSafetyBlocked")
    print()
    say.ok("both are ContentSafetyBlocked — the vendor is in the message, not the type")
    say.note(
        "Both vendors are live-verified: Azure on 2026-09-22, Bedrock on "
        "2026-09-24. The discriminator is the vendor-named ...-action: reject "
        "header, not the body, so a reject with an unexpected body is still "
        "caught. Categories are the vendor's own words — severity_* from Azure, "
        "content_filter from Bedrock — and are prompt-dependent."
    )


def act_3_two_error_envelopes() -> None:
    say.step(3, "Two provider error envelopes, one exception")
    for label, response in (
        ("OpenAI  {\"error\": {...}}", _rebuild("model-not-found")),
        ("Gemini  [{\"error\": {...}}]", GEMINI_400),
    ):
        error = classify(response)
        print()
        say.field(label, f"HTTP {response.status_code}", raw=True)
        say.field("  classified as", type(error).__name__)
        say.field("  .code", repr(getattr(error, "code", None)), raw=True)
        say.field("  .error_type", getattr(error, "error_type", None), raw=True)
        say.field("  .param", getattr(error, "param", None), raw=True)
        if not isinstance(error, UpstreamRequestError):
            say.fail("expected UpstreamRequestError")
        if isinstance(error, PolicyViolation):
            say.fail("an upstream 400 must not be a policy refusal")
    print()
    say.ok("both are UpstreamRequestError — your request was wrong, the gateway did not refuse")
    say.note(
        "Gemini wraps the error object in a JSON list, sends a numeric code and "
        "a string status instead of OpenAI's type/param. classify() unwraps the "
        "list, carries the code as a string, and uses status where OpenAI would "
        "put type. Before this, the same 400 fell through to a generic "
        "PolicyViolation — a governance refusal that never happened."
    )


def act_4_ingress_formats() -> None:
    say.step(4, "Ingress Format is chosen per proxy, and it decides the adapter")
    say.table(
        {
            "Format=OpenAI": "POST /<base>/responses — donkey.openai(), every OpenAI-compatible adapter",
            "Format=Anthropic": "POST /<base>/v1/messages — donkey.anthropic.client()",
            "Format=Gemini": "POST /<base>/models/<m>:generateContent — no SDK adapter ships",
        },
        title_="live-verified routes:",
    )
    print()
    if importlib.util.find_spec("anthropic") is None:
        say.note('anthropic is not installed: pip install "donkey-kit[anthropic]"')
    else:
        donkey = Donkey(
            DonkeyConfig(
                llm_proxy_url="https://demo-gateway.example.invalid/anthropic-sdk/",
                llm_proxy_client_id="demo-client-id-not-a-real-credential",
                llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
            )
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            client = donkey.anthropic.client()
        say.field("donkey.anthropic.client()", f"{type(client).__module__}.{type(client).__name__}")
        say.field("base_url", redact.text(str(client.base_url)))
        if not caught:
            say.ok("no UnverifiedValueWarning — the native Messages route is live-verified")
        donkey.close()
    say.note(
        "Format is fixed when the proxy is created. The SDK's own DDK proxies "
        "are Format=OpenAI, where /v1/messages is a 404 — Claude is reachable "
        "there only as an upstream provider through the OpenAI surface. Point "
        "donkey.anthropic at a Format=Anthropic proxy for the native API. Native "
        "ingress is single-route: multi-routing and fallback stay OpenAI-only. "
        "Gemini-native is verified but has no adapter; the SDK does not guess one."
    )


def main() -> None:
    act_1_request_id()
    say.pause()
    act_2_two_guardrail_vendors()
    say.pause()
    act_3_two_error_envelopes()
    say.pause()
    act_4_ingress_formats()

    print()
    say.section("What is still not verified")
    say.note(
        "Header-based Injection Protection (x-injection-protection: blocked) is "
        "the one guardrail shape still typed from documentation — no proxy "
        "running it is deployed. AsyncAnthropic's constructor signature is "
        "checked by the nightly matrix, not asserted. Every wire shape in this "
        "demo is from a live capture."
    )
    print()
    say.section("The point")
    say.note(
        "Four providers, four wire dialects, and your except blocks did not "
        "change: one request_id, one ContentSafetyBlocked, one "
        "UpstreamRequestError. The gateway stays a passthrough; the SDK is where "
        "the difference is absorbed."
    )


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 15 — provider passthrough",
        subtitle="Different providers, different wire answers — one field, one type.",
        target="offline",
        extras=("openai",),
    )
