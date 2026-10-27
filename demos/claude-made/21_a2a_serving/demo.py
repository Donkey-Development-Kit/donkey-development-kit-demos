"""Official a2a-sdk serving, exercised locally through ASGI with lifespan.

No socket listener is started. This is the app behind Donkey.serve(), not
gateway exposure. Model calls are MockTransport responses, never live calls.
"""

from __future__ import annotations

import asyncio
import json
import os
import re

import httpx
from donkey_kit import A2ATask, Donkey, typed_refusals
from donkey_kit._testing import http_clients, swap_transport
from donkey_kit.a2a import build_app
from donkey_kit.core.config import DonkeyConfig
from donkey_kit.core.telemetry import GEN_AI_COMPLETION, GEN_AI_PROMPT
from donkey_kit.core.transport import CALL_ID_HEADER, CORRELATION_HEADER

from _harness import narrate as say
from _harness import preflight


async def _main() -> None:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.trace import SpanKind, StatusCode

    if not isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
        raise RuntimeError(
            "Demo 21 requires a fresh process: a concrete host OTel provider is already installed. No agent operations were run; refusing to send spans to a host exporter."
        )
    for name in tuple(os.environ):
        if name.startswith("OTEL_"):
            del os.environ[name]
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    if trace.get_tracer_provider() is not provider:
        provider.shutdown()
        raise RuntimeError("Demo 21 could not install its isolated in-memory OTel provider")
    seen = []
    entered = []
    baseline = asyncio.all_tasks()
    cfg = DonkeyConfig(
        llm_proxy_url="https://model.example.invalid/",
        llm_proxy_client_id="demo-client-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
        max_retries=0,
    )
    hidden = "synthetic-internal-detail-never-returned"

    def model(request):
        seen.append(request)
        body = json.loads(request.content)
        if body["model"] == "refuse":
            return httpx.Response(
                403, json={"error": {"type": "pii_detected", "message": hidden}}
            )
        return httpx.Response(
            200,
            json={
                "id": "local-completion",
                "object": "chat.completion",
                "created": 0,
                "model": "local-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "local result"},
                    }
                ],
            },
        )

    say.note(
        "The official a2a-sdk app runs through ASGI lifespan in process, with no listening port. Model calls use MockTransport; no gateway is contacted."
    )
    say.step(1, "An agent marker generates a discoverable A2A card")
    say.code("""
        @donkey.agent(name="local-helper", skills=["governed-call"])
        async def helper(task: A2ATask) -> str: ...
        app = build_app(helper, refusals=typed_refusals())
        # Donkey.serve runs this app with uvicorn; here we exercise ASGI lifespan.
    """)
    try:
        async with Donkey(cfg) as donkey:
            for http in http_clients(donkey):
                swap_transport(http, httpx.MockTransport(model))
            client = donkey.llm.client()

            @donkey.agent(name="local-helper", skills=["governed-call"])
            async def helper(task: A2ATask) -> str:
                """Makes one locally simulated governed model call."""
                entered.append(task.correlation_id)
                await client.chat.completions.create(
                    model="refuse" if task.input == "refuse" else "local-model",
                    messages=[{"role": "user", "content": "synthetic-input"}],
                )
                return "completed locally"

            # Same official SDK app as Donkey.serve(), mounted in-process instead
            # of uvicorn. Pass the same typed-refusal bridge the serve facade uses.
            app = build_app(helper, url="http://agent.local/", refusals=typed_refusals())
            async with (
                app.router.lifespan_context(app),
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://agent.local",
                    trust_env=False,
                ) as caller,
            ):
                card_response = await caller.get("/.well-known/agent-card.json")
                assert card_response.status_code == 200
                card = card_response.json()
                assert card["name"] == "local-helper"
                assert [s["id"] for s in card["skills"]] == ["governed-call"]
                assert card["description"] == helper.__doc__
                assert card["supportedInterfaces"][0]["protocolVersion"] == "1.0"
                say.field("agent name", card["name"])
                say.field("skill", card["skills"][0]["id"])
                say.field("protocol", card["supportedInterfaces"][0]["protocolVersion"])
                say.ok("Generated card matches the decorator, including its description")
                say.pause()
                say.step(
                    2, "Success, a structured refusal, then success on the same server"
                )
                say.code("""
                    # A2A 1.0: A2A-Version: 1.0, JSON-RPC method SendMessage
                    # message: {messageId: ..., role: ROLE_USER, parts: [{text: ...}]}
                """)

                tasks = []
                for i, (text, headers) in enumerate(
                    (
                        ("success", {CORRELATION_HEADER: "caller-run-55"}),
                        ("refuse", {CORRELATION_HEADER: "caller-refusal-55"}),
                        ("success", {}),
                    )
                ):
                    # A2A 1.0 JSON-RPC SendMessage, matching SDK wire-contract tests.
                    response = await caller.post(
                        "/",
                        headers={"A2A-Version": "1.0", **headers},
                        json={
                            "jsonrpc": "2.0",
                            "id": i + 1,
                            "method": "SendMessage",
                            "params": {
                                "message": {
                                    "messageId": f"local-{i}",
                                    "role": "ROLE_USER",
                                    "parts": [{"text": text}],
                                }
                            },
                        },
                    )
                    assert response.status_code == 200
                    payload = response.json()
                    assert "error" not in payload
                    tasks.append(payload["result"]["task"])
                first, refused, recovered = tasks
                assert first["status"]["state"] == "TASK_STATE_COMPLETED"
                assert first["artifacts"][0]["parts"] == [{"text": "completed locally"}]
                assert refused["status"]["state"] == "TASK_STATE_FAILED"
                details = refused["status"]["message"]["parts"][1]["data"]["error"]
                assert details == {
                    "type": "PIIDetected",
                    "refusal": True,
                    "correlation_id": "caller-refusal-55",
                    "call_id": seen[1].headers[CALL_ID_HEADER],
                }
                assert hidden not in json.dumps(refused)
                assert "Traceback" not in json.dumps(refused)
                assert recovered["status"]["state"] == "TASK_STATE_COMPLETED"
                assert len({t["id"] for t in tasks}) == 3
                assert entered[:2] == ["caller-run-55", "caller-refusal-55"]
                assert re.fullmatch(r"[0-9a-f]{32}", entered[2])
                assert [r.headers[CORRELATION_HEADER] for r in seen] == entered
                for label, task in zip(
                    ("first task", "refused task", "recovery task"), tasks, strict=True
                ):
                    say.field(label, task["status"]["state"])
                say.field("refusal type", details["type"])
                say.field("refusal flag", details["refusal"])
                say.ok("Success -> structured PIIDetected failure -> continued success")
                say.ok(
                    "Valid incoming IDs adopted; absent ID minted; downstream headers match"
                )
                say.note(
                    "A failed task carries type and correlation/call IDs, not the internal exception message or traceback. One refused task does not terminate the server."
                )
                say.pause()
                say.step(3, "Each inbound task parents its governed downstream span")

            # Lifespan exit calls the official request handler's aclose(), draining
            # its worker tasks. Check before asyncio.run can hide leaks by cancelling.
            await asyncio.sleep(0)
            assert not (asyncio.all_tasks() - baseline), (
                "A2A worker leaked after lifespan shutdown"
            )
            all_spans = exporter.get_finished_spans()
            assert all(hidden not in s.to_json() for s in all_spans)
            spans = all_spans
            spans = [s for s in spans if s.name in {"donkey.a2a.task", "donkey.llm.chat"}]
            assert len(spans) == 6, [s.name for s in exporter.get_finished_spans()]
            for i, task in enumerate(tasks):
                (parent,) = [
                    s
                    for s in spans
                    if s.name == "donkey.a2a.task"
                    and s.attributes["donkey.a2a.task_id"] == task["id"]
                ]
                (child,) = [
                    s
                    for s in spans
                    if s.name == "donkey.llm.chat"
                    and s.attributes["donkey.correlation_id"] == entered[i]
                ]
                assert parent.kind == SpanKind.SERVER
                assert parent.attributes["donkey.correlation_id"] == entered[i]
                assert parent.attributes["donkey.correlation_id.source"] == (
                    "minted" if i == 2 else "adopted"
                )
                assert child.parent.span_id == parent.context.span_id
                assert child.context.trace_id == parent.context.trace_id
                assert (parent.status.status_code == StatusCode.ERROR) == (i == 1)
                assert (child.status.status_code == StatusCode.ERROR) == (i == 1)
            assert all(hidden not in s.to_json() for s in spans)
            assert all(
                GEN_AI_PROMPT not in s.attributes and GEN_AI_COMPLETION not in s.attributes
                for s in spans
            )
            say.field("DDK spans", len(spans))
            say.ok("Three SERVER task spans parent three model spans in matching traces")
            say.ok("Refusal ERROR; no message, prompt or completion leak")
            say.pause()
            say.step(4, "Shutdown drains workers before the event loop can hide a leak")
            say.ok("ASGI lifespan shutdown drained all A2A workers")
        assert donkey.http_client().is_closed
        say.ok("Donkey transport closed")
        say.note(
            "Gateway exposure, donkey expose and donkey dev remain outside implemented scope. ASGI checks do not verify the blocking uvicorn launcher, network reachability or a deployed gateway."
        )
    finally:
        assert provider.force_flush(timeout_millis=2000)
        provider.shutdown()
    say.ok("Host provider flushed and shut down")


def main() -> None:
    """Run the A2A serving assertions in a fresh process."""
    asyncio.run(asyncio.wait_for(_main(), timeout=20))


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 21 - local A2A serving",
        subtitle="An official-SDK agent card, governed tasks and a refusal that does not stop service.",
        target="offline",
        extras=("openai", "a2a", "starlette", "opentelemetry.sdk"),
    )
