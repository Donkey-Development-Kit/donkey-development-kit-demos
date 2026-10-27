"""Local-only telemetry: incoming IDs, explicit hops, tenant scopes and flush.

Run this script in a fresh process. No config files or credentials are read.
The OTLP receiver binds a real loopback port; model and HTTP-hop responses use
MockTransport. This verifies SDK behavior, not a deployed gateway contract.
"""

from __future__ import annotations

import asyncio
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
from donkey_kit import Donkey, PIIDetected
from donkey_kit._testing import http_clients, swap_transport
from donkey_kit.core import _verify, _wire
from donkey_kit.core.config import DonkeyConfig
from donkey_kit.core.correlation import current_business_group, current_correlation_id
from donkey_kit.core.cost import CostTags
from donkey_kit.core.telemetry import (
    GEN_AI_COMPLETION,
    GEN_AI_PROMPT,
    GEN_AI_SEMCONV_VERSION,
)
from donkey_kit.core.transport import CALL_ID_HEADER, CORRELATION_HEADER

from _harness import narrate as say
from _harness import preflight, redact


async def _main() -> None:
    from opentelemetry import trace
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceRequest,
    )
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    # Do not inherit collector credentials, endpoints, resources or content settings.
    for name in tuple(os.environ):
        if name.startswith("OTEL_"):
            del os.environ[name]
    initial_provider = trace.get_tracer_provider()
    async with Donkey(DonkeyConfig()) as inert:
        assert await asyncio.to_thread(inert.flush_telemetry, timeout_s=2.0) is True
        assert trace.get_tracer_provider() is initial_provider
    received = []

    class Collector(BaseHTTPRequestHandler):
        def do_POST(self):
            assert self.path == "/v1/traces"
            payload = ExportTraceServiceRequest()
            payload.ParseFromString(self.rfile.read(int(self.headers["Content-Length"])))
            received.extend(
                span
                for resource in payload.resource_spans
                for scope in resource.scope_spans
                for span in scope.spans
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/x-protobuf")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *_args):
            pass

    collector = ThreadingHTTPServer(("127.0.0.1", 0), Collector)
    thread = threading.Thread(target=collector.serve_forever, daemon=True)
    thread.start()
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = f"http://127.0.0.1:{collector.server_port}"
    os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"
    os.environ["OTEL_EXPORTER_OTLP_TIMEOUT"] = "1"
    os.environ["OTEL_BSP_SCHEDULE_DELAY"] = "60000"
    os.environ["OTEL_RESOURCE_ATTRIBUTES"] = "service.name=local-demo-06"
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    say.note(
        "Model and HTTP-hop responses are mocked. Only the OTLP receiver uses a real loopback port; no external collector is contacted."
    )
    say.ok("Without an OTLP endpoint, bootstrap stayed inert and flush was a no-op")

    cfg = DonkeyConfig(
        llm_proxy_url="https://model.example.invalid/",
        llm_proxy_client_id="demo-client-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
        business_group="configured",
        cost=CostTags(team="platform", env="dev"),
    )
    seen = []
    hops = []

    async def model(request):
        await asyncio.sleep(0)
        seen.append(request)
        return httpx.Response(
            200,
            headers={
                _wire.LLM_PROVIDER_HEADER: "openai",
                _wire.LLM_MODEL_HEADER: "served-model",
                _wire.ROUTING_TYPE_HEADER: "Model",
                _wire.ROUTING_FALLBACK_HEADER: "true",
            },
            json={
                "model": "served-model",
                "choices": [],
                "usage": {
                    "input_tokens": 1420,
                    "output_tokens": 310,
                    "input_tokens_details": {
                        "cached_tokens": 512,
                        "cache_write_tokens": 128,
                    },
                    "output_tokens_details": {"reasoning_tokens": 96},
                },
            },
        )

    def hop(request):
        hops.append(request)
        return httpx.Response(200, json={"ok": True})

    host = None
    try:
        async with Donkey(cfg) as donkey:
            for http in http_clients(donkey):
                swap_transport(http, httpx.MockTransport(model))
            client = donkey.http_client()
            say.step(1, "One governed call produces both GenAI and Donkey span attributes")
            say.code("""
                await donkey.http_client().post(url, json={"model": "local-model", ...})
                # The shared transport records model, routing and usage, not content.
            """)
            await client.post(
                f"{cfg.llm_proxy_url}chat/completions",
                json={"model": "local-model", "messages": []},
            )
            assert await asyncio.to_thread(donkey.flush_telemetry, timeout_s=2.0)
            assert len(received) == 1
            assert received[0].name == "donkey.llm.chat"

            def attributes(span):
                return {
                    a.key: getattr(a.value, a.value.WhichOneof("value"))
                    for a in span.attributes
                }

            first = attributes(received[0])
            assert first["gen_ai.request.model"] == "local-model"
            assert first["gen_ai.response.model"] == "served-model"
            assert first["donkey.routing.type"] == "Model"
            assert first["donkey.routing.fallback"] is True
            assert first["gen_ai.usage.input_tokens"] == 1420
            assert first["gen_ai.usage.output_tokens"] == 310
            assert first["donkey.usage.cached_tokens"] == 512
            assert first["donkey.usage.cache_write_tokens"] == 128
            assert first["donkey.usage.reasoning_tokens"] == 96
            assert GEN_AI_PROMPT not in first and GEN_AI_COMPLETION not in first
            for namespace in ("gen_ai.", "donkey.routing.", "donkey.usage."):
                say.table(
                    {
                        k: redact.text(v)
                        for k, v in first.items()
                        if k.startswith(namespace)
                    },
                    title_=namespace,
                )
            say.field("semconv version", GEN_AI_SEMCONV_VERSION)
            say.ok(
                "One call, one span; routing fallback and cached/reasoning usage are observed"
            )
            say.note(
                "gen_ai.* uses the SDK's pinned semantic convention; donkey.* is its stable namespace. Request and served models differ here because the synthetic response reports a fallback. Content capture remains opt-in."
            )
            say.pause()
            say.step(2, "Three model calls share one business run and its cost overrides")
            async with donkey.run(id="ticket-4417", team="support", project="triage"):
                for _ in range(3):
                    await client.post(
                        f"{cfg.llm_proxy_url}chat/completions",
                        json={"model": "local-model", "messages": []},
                    )
            assert await asyncio.to_thread(donkey.flush_telemetry, timeout_s=2.0)
            run_attrs = [attributes(s) for s in received[1:]]
            assert len(run_attrs) == 3
            assert {a["donkey.correlation_id"] for a in run_attrs} == {"ticket-4417"}
            assert {a["donkey.cost.team"] for a in run_attrs} == {"support"}
            assert {a["donkey.cost.project"] for a in run_attrs} == {"triage"}
            assert {a["donkey.cost.env"] for a in run_attrs} == {"dev"}
            assert all(
                GEN_AI_PROMPT not in a and GEN_AI_COMPLETION not in a for a in run_attrs
            )
            assert len({r.headers[CALL_ID_HEADER] for r in seen[1:]}) == 3
            say.field("run header", CORRELATION_HEADER)
            say.field("call header", CALL_ID_HEADER)
            say.ok(
                "Three calls share one run ID and team/project overrides; env inherits dev"
            )
            say.note(
                "Run ID joins a business operation; each call ID distinguishes one model request. Cost tags are span attribution, not proof of gateway cost-header ingestion."
            )
            received.clear()
            seen.clear()
            say.pause()
            say.step(3, "Adopt incoming correlation, or mint a safe replacement")
            say.code("""
                async with donkey.run_from_headers(incoming):
                    await outbound.post(hop_url, headers=donkey.correlation_headers())
            """)
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(hop), trust_env=False
            ) as outbound:
                expected = []
                for incoming, source in (
                    (
                        {
                            "x-correlation-id": "caller-run-42",
                            "X-Anypoint-Cost-Team": "untrusted-caller-claim",
                        },
                        "adopted",
                    ),
                    ({"X-Correlation-Id": "invalid id; not forwarded"}, "minted"),
                ):
                    async with donkey.run_from_headers(incoming) as run_id:
                        if source == "adopted":
                            assert run_id == "caller-run-42"
                        else:
                            assert re.fullmatch(r"[0-9a-f]{32}", run_id)
                        await client.post(
                            f"{cfg.llm_proxy_url}chat/completions",
                            json={"model": "local-model", "messages": []},
                        )
                        # A plain HTTP hop, NOT a claimed Exchange/MCP binding.
                        await outbound.post(
                            "https://hop.example.invalid/",
                            headers=donkey.correlation_headers(),
                        )
                        expected.append((run_id, source))
                        assert seen[-1].headers[CORRELATION_HEADER] == run_id
                        assert hops[-1].headers[CORRELATION_HEADER] == run_id
                        assert "client_id" not in hops[-1].headers
                        assert "client_secret" not in hops[-1].headers
                assert current_correlation_id() is None
                assert donkey.correlation_headers() == {}
                say.ok("Incoming ID adopted; malformed ID minted; explicit HTTP hop joined")
                say.note(
                    "This hop is plain HTTP on a separate client, not a claimed Exchange/MCP binding. Only correlation headers cross it, never consumer credentials or inbound cost claims."
                )

            say.pause()
            say.step(4, "Concurrent tenants keep their own business-group scopes")
            group_header = _verify.ATTRIBUTION_BUSINESS_GROUP_HEADER.placeholder
            async with donkey.attribution(business_group="outer"):

                async def tenant(name):
                    async with donkey.run(id=name, business_group=name):
                        await asyncio.sleep(0)
                        await client.post(
                            f"{cfg.llm_proxy_url}chat/completions",
                            json={"model": "local-model", "messages": []},
                        )
                        assert current_business_group() == name

                await asyncio.gather(tenant("tenant-a"), tenant("tenant-b"))
                assert current_business_group() == "outer"
                await client.post(
                    f"{cfg.llm_proxy_url}chat/completions",
                    json={"model": "local-model", "messages": []},
                )
            assert current_business_group() is None
            await client.post(
                f"{cfg.llm_proxy_url}chat/completions",
                json={"model": "local-model", "messages": []},
            )
            assert {
                (r.headers[CORRELATION_HEADER], r.headers[group_header]) for r in seen[2:4]
            } == {("tenant-a", "tenant-a"), ("tenant-b", "tenant-b")}
            assert [r.headers[group_header] for r in seen[4:]] == ["outer", "configured"]
            say.ok(
                "Concurrent tenant groups isolated; outer then configured group restored"
            )
            say.warn("Business-group wire name is UNVERIFIED; no gateway ingestion claim")

            say.pause()
            say.step(
                5, "A refusal is an ERROR span; flush before a short-lived process exits"
            )
            async with donkey.run(id="refused-run"):
                with donkey.simulate(PIIDetected):
                    response = await client.post(
                        f"{cfg.llm_proxy_url}chat/completions",
                        json={"model": "local-model", "messages": []},
                    )
                    assert response.status_code == 403
                    from donkey_kit.core.errors import classify

                    refusal = classify(response)
                    assert isinstance(refusal, PIIDetected)
                    assert refusal.correlation_id == "refused-run"
                    assert refusal.call_id == response.request.headers[CALL_ID_HEADER]
                    say.field("refusal type", type(refusal).__name__)
                    say.field("correlation_id", refusal.correlation_id)
                    say.field("call_id", refusal.call_id)
            say.code("await asyncio.to_thread(donkey.flush_telemetry, timeout_s=2.0)")
            start = time.monotonic()
            flushed = await asyncio.to_thread(donkey.flush_telemetry, timeout_s=2.0)
            elapsed = time.monotonic() - start
            assert flushed is True
            assert elapsed < 3.0, "local flush exceeded timeout plus scheduling allowance"
            assert len(received) == 7, len(received)
            attrs = [{a.key: a.value.string_value for a in s.attributes} for s in received]
            for run_id, source in expected:
                match = [a for a in attrs if a.get("donkey.correlation_id") == run_id]
                assert len(match) == 1
                assert match[0]["donkey.correlation_id.source"] == source
            assert received[-1].status.code == 2  # OTLP STATUS_CODE_ERROR
            assert attrs[-1]["donkey.policy.type"] == "pii_detected"
            assert attrs[-1]["donkey.policy.decision"] == "refuse"
            assert all(GEN_AI_PROMPT not in a and GEN_AI_COMPLETION not in a for a in attrs)
            assert all(a["donkey.cost.team"] == "platform" for a in attrs)
            assert all(
                not k.startswith("donkey.cost.")
                or k in {"donkey.cost.team", "donkey.cost.env"}
                for a in attrs
                for k in a
            )
            say.field("flush result", flushed)
            say.field("OTLP spans received", len(received))
            say.ok(
                "DDK-owned flush delivered seven queued spans; adopted/minted sources and refusal ERROR checked"
            )
            say.ok("Prompt/completion absent; incoming cost claim was not adopted")
            say.pause()
            say.step(6, "A host-owned provider wins, and owns its own flush")

            exporter = InMemorySpanExporter()

            class HostProvider(TracerProvider):
                flush_calls = 0

                def force_flush(self, timeout_millis=30000):
                    self.flush_calls += 1
                    return super().force_flush(timeout_millis)

            host = HostProvider()
            host.add_span_processor(
                BatchSpanProcessor(exporter, schedule_delay_millis=60000)
            )
            trace.set_tracer_provider(host)
            await client.post(
                f"{cfg.llm_proxy_url}chat/completions",
                json={"model": "local-model", "messages": []},
            )
            assert not exporter.get_finished_spans()
            assert await asyncio.to_thread(donkey.flush_telemetry, timeout_s=2.0) is True
            assert host.flush_calls == 0
            assert not exporter.get_finished_spans()
            assert await asyncio.to_thread(host.force_flush, timeout_millis=2000)
            assert len(exporter.get_finished_spans()) == 1
            assert len(received) == 7
            say.ok(
                "Host provider wins; DDK flush leaves host queue alone; host flush exports it"
            )
            say.note(
                "Standard OTEL_EXPORTER_OTLP_ENDPOINT enables DDK-scoped batched export; without an endpoint it is inert. DDK does not take the global provider unless telemetry_install_global opts in. Its provider is process-wide, not per Donkey. Flush blocks: offload in async code. True can be a no-op; False means timeout/failure."
            )
    finally:
        if host is not None:
            host.shutdown()
        await asyncio.to_thread(collector.shutdown)
        collector.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()
    say.ok(
        "Local collector shutdown; no credentials, caller cost claims or content printed"
    )


def main() -> None:
    """Run the assertions in an isolated process, with local-only dependencies."""
    asyncio.run(_main())


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 06 - GenAI telemetry and cross-hop attribution",
        subtitle="Standard spans, isolated runs and explicit flush ownership.",
        target="offline",
        extras=(
            "opentelemetry.sdk",
            "opentelemetry.exporter.otlp.proto.http.trace_exporter",
        ),
    )
