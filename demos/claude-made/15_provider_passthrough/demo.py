"""Demo 15 — the gateway passes the provider through; the SDK absorbs the difference.

The gateway does not rewrite what the upstream provider says. It forwards the
provider's own request id, the provider's own error envelope, and — for the
guardrail policies — a vendor-named reject header. So the same question ("what
id do I quote?", "was my request wrong?", "which guardrail said no?") has a
different wire answer on OpenAI, Azure, Bedrock and Gemini routes.

This demo replays packaged classifier fixtures offline. Model Armor is
live-captured; CrowdStrike AIDR and the fail-closed 503 are policy-source-derived,
not live-captured. Bedrock and Gemini use reduced live-capture shapes inline.
No credentials, simulator vendor selectors, network or OTLP exports.

    python demos/claude-made/15_provider_passthrough/demo.py
"""

from __future__ import annotations

import asyncio
import importlib.util
import warnings
from unittest.mock import patch

import httpx
from donkey_kit import ContentSafetyBlocked, Donkey, DonkeyConfig, PolicyViolation
from donkey_kit._testing import http_clients, swap_transport
from donkey_kit.core.errors import UpstreamModelError, UpstreamRequestError, classify
from donkey_kit.core.lastcall import REQUEST_ID_HEADERS, LastCall
from donkey_kit.simulator.fixtures import fixture_bytes, load, parse_headers

from _harness import narrate as say
from _harness import preflight, redact

# Shapes from the live captures (SDK donkey_kit/simulator/_fixtures, tests/fixtures), reduced to the headers
# classify() and LastCall actually read. Ids are demo placeholders.
BEDROCK_REJECT = httpx.Response(
    403,
    headers={
        "x-llm-proxy-bedrock-guardrail-action": "reject",
        "x-llm-proxy-bedrock-guardrail-reason": "content_filter",
        "x-amzn-requestid": "demo-amzn-request-id",
    },
    json={
        "error": "Content blocked by Amazon Bedrock Guardrails",
        "categories": ["content_filter"],
    },
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


def _sibling(vendor: str) -> httpx.Response:
    # Classifier-contract siblings are packaged bytes, NOT SHAPES/scenario keys.
    stem = f"reject.content-safety-{vendor}"
    headers = parse_headers(fixture_bytes("rejections", f"{stem}.headers.txt").decode())
    headers.pop("content-length", None)
    return httpx.Response(
        403, headers=headers, content=fixture_bytes("rejections", f"{stem}.body.json")
    )


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
        say.field(
            "  headers.get('x-request-id')", response.headers.get("x-request-id"), raw=True
        )
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


def act_2_safety_vendors() -> None:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    say.step(2, "Four safety vendors: structured exceptions and real transport spans")
    say.code(
        """
        except ContentSafetyBlocked as e:
            print(e.provider, e.categories, e.policy)
            revise(e.categories)
        """
    )
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    async def demonstrate() -> None:
        for label, source, response in (
            ("Azure Content Safety", "live-captured", _rebuild("content-safety")),
            ("Amazon Bedrock Guardrails", "live-captured, reduced headers", BEDROCK_REJECT),
            ("Google Model Armor", "live-captured 2026-10-19", _sibling("model-armor")),
            (
                "CrowdStrike AIDR",
                "policy-source-derived, NOT live-captured",
                _sibling("crowdstrike-aidr"),
            ),
        ):
            error = classify(response)
            assert isinstance(error, ContentSafetyBlocked)
            assert error.policy == "content-safety" and error.provider and error.categories
            print()
            say.field(label, f"HTTP {response.status_code}: {source}", raw=True)
            say.field("  .provider", error.provider, raw=True)
            say.field("  .categories", error.categories, raw=True)
            say.field("  .policy", error.policy, raw=True)
            cfg = DonkeyConfig(
                llm_proxy_url="https://example.invalid/",
                llm_proxy_client_id="demo-client-not-a-real-credential",
                llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
                max_retries=0,
            )
            async with Donkey(cfg) as donkey:

                def reject(
                    request: httpx.Request, response: httpx.Response = response
                ) -> httpx.Response:
                    return httpx.Response(
                        response.status_code,
                        headers=response.headers,
                        content=response.content,
                    )

                for client in http_clients(donkey):
                    swap_transport(client, httpx.MockTransport(reject))
                try:
                    async with donkey.run(id="demo15-safety"):
                        await donkey.llm.client().chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": "offline probe"}],
                        )
                except ContentSafetyBlocked as raised:
                    assert raised.provider == error.provider
                else:
                    raise AssertionError("The governed transport must refuse.")
            span = next(
                span
                for span in reversed(exporter.get_finished_spans())
                if "donkey.policy.provider" in (span.attributes or {})
            )
            attributes = dict(span.attributes or {})
            assert attributes["donkey.policy.provider"] == error.provider
            assert tuple(attributes["donkey.policy.categories"]) == tuple(error.categories)
            say.field(
                "  donkey.policy.provider", attributes["donkey.policy.provider"], raw=True
            )
            say.field(
                "  donkey.policy.categories",
                attributes["donkey.policy.categories"],
                raw=True,
            )

    # Force memory-only telemetry; never consult ambient OTLP headers/endpoints.
    with (
        patch("donkey_kit.core.telemetry._build_tracer_provider", return_value=None),
        patch(
            "donkey_kit.core.telemetry._tracer", return_value=provider.get_tracer("demo15")
        ),
    ):
        asyncio.run(demonstrate())
    provider.shutdown()
    outage = classify(
        httpx.Response(
            503,
            headers={
                "x-llm-proxy-model-armor-action": "reject",
                "x-llm-proxy-model-armor-reason": "timeout",
            },
            json={"error": "service unavailable", "categories": ["timeout"]},
        )
    )
    assert isinstance(outage, UpstreamModelError) and not isinstance(
        outage, ContentSafetyBlocked
    )
    say.field("fail-closed 503 (policy-source-derived)", type(outage).__name__, raw=True)
    say.note(
        "403 judges content; a fail-closed 503 judges nothing: moderation was unavailable."
    )
    say.note(
        "Model Armor and CrowdStrike are sibling classifier fixtures, not simulator vendor selectors."
    )


def act_3_two_error_envelopes() -> None:
    say.step(3, "Two provider error envelopes, one exception")
    for label, response in (
        ('OpenAI  {"error": {...}}', _rebuild("model-not-found")),
        ('Gemini  [{"error": {...}}]', GEMINI_400),
    ):
        error = classify(response)
        print()
        say.field(label, f"HTTP {response.status_code}", raw=True)
        say.field("  classified as", type(error).__name__)
        say.field("  .code", repr(getattr(error, "code", None)), raw=True)
        say.field("  .error_type", getattr(error, "error_type", None), raw=True)
        say.field("  .param", getattr(error, "param", None), raw=True)
        assert isinstance(error, UpstreamRequestError), "expected UpstreamRequestError"
        assert not isinstance(error, PolicyViolation), "an upstream 400 is not a refusal"
    print()
    say.ok(
        "both are UpstreamRequestError — your request was wrong, the gateway did not refuse"
    )
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
            "Format=OpenAI": "POST /<base>/responses or /chat/completions — donkey.openai(), the OpenAI-compatible adapters",
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
                telemetry=False,
            )
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            client = donkey.anthropic.client()
        say.field(
            "donkey.anthropic.client()",
            f"{type(client).__module__}.{type(client).__name__}",
        )
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
    act_2_safety_vendors()
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
        "demo is replayed offline. Model Armor is live-captured; CrowdStrike AIDR "
        "and the fail-closed 503 are policy-source-derived, not live verification."
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
        extras=("openai", "opentelemetry.sdk"),
    )
