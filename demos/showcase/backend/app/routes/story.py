"""Offline protocol stories using the same public SDK paths as demos 22-24."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

try:
    from builtins import BaseExceptionGroup
except ImportError:  # Python 3.10, supported by the demo package.
    from exceptiongroup import BaseExceptionGroup

from donkey_kit import (
    ContentSafetyBlocked,
    Donkey,
    DonkeyConfig,
    PIIDetected,
    PolicyViolation,
    TokenBudgetExceeded,
    ToolLockDrift,
    ToolNotInProfile,
)
from donkey_kit.experimental import ToolInvocationError
from mcp.shared.exceptions import McpError
from starlette.responses import JSONResponse

from .. import telemetry
from ..features import feature_by_id

# The official A2A SDK reads this before import. Do not override a host choice;
# DDK's tracing gate still refuses an explicitly enabled SDK recorder.
os.environ.setdefault("OTEL_INSTRUMENTATION_A2A_SDK_ENABLED", "false")

REF = "acme/inventory/1.0.0"
AGENT = "acme/claims-triage-agent/1.0.0"
TOOL = {
    "name": "get_stock",
    "description": "Return the stock level for a SKU.",
    "inputSchema": {
        "type": "object",
        "properties": {"sku": {"type": "string"}},
        "required": ["sku"],
    },
}
CONFIG = DonkeyConfig(
    llm_proxy_url="https://demo-gateway.example.invalid/protocol/",
    llm_proxy_client_id="demo-client-id-not-a-real-credential",
    llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
)


def _expected_mcp_error(exc: BaseException, code: int) -> bool:
    if isinstance(exc, McpError):
        return exc.error.code == code
    if isinstance(exc, BaseExceptionGroup):
        return bool(exc.exceptions) and all(
            _expected_mcp_error(child, code) for child in exc.exceptions
        )
    return (
        isinstance(exc, ToolInvocationError)
        and exc.__cause__ is not None
        and _expected_mcp_error(exc.__cause__, code)
    )


async def run_story(feature: str) -> dict:
    card = feature_by_id(feature)
    if card is None or card["action"] != "story":
        raise ValueError("Unknown protocol story")
    steps = []

    def step(title: str, outcome: str, detail: str) -> None:
        steps.append({"title": title, "outcome": outcome, "detail": detail})

    async with Donkey(CONFIG) as donkey, donkey.run() as run:
        if feature == "mcp-refusals":
            for capture in ("pii-request", "pii-response-sse"):
                with donkey.simulate_mcp(capture, servers={REF: [TOOL]}):
                    tools = await donkey.tools.discover()
                    (bound,) = await tools.langgraph()
                    try:
                        await bound.ainvoke({"sku": "SKU-41"})
                    except PIIDetected as exc:
                        step(
                            capture,
                            type(exc).__name__,
                            f"phase={exc.phase}; flagged values withheld.",
                        )
                    else:
                        raise AssertionError("PII capture did not refuse")
                    await bound.ainvoke({"sku": "SKU-41"})
                    steps[-1]["detail"] += (
                        " The next call succeeds from the offline baseline (times=1)."
                    )
            with donkey.simulate_mcp("global-access", servers={REF: [TOOL]}):
                tools = await donkey.tools.discover()
                (bound,) = await tools.langgraph()
                try:
                    await bound.ainvoke({"sku": "SKU-41"})
                except ToolNotInProfile as exc:
                    step(
                        "Access-profile denial",
                        type(exc).__name__,
                        "HTTP 200 is not success: JSON-RPC -32008 denies access. No retry.",
                    )
                else:
                    raise AssertionError("Access capture did not refuse")
            for capture in ("schema-invalid-args", "poisoning-block-list"):
                with donkey.simulate_mcp(capture, servers={REF: [TOOL]}):
                    tools = await donkey.tools.discover()
                    if capture == "schema-invalid-args":
                        (bound,) = await tools.langgraph()
                    try:
                        if capture == "schema-invalid-args":
                            await bound.ainvoke({"sku": "SKU-41"})
                        else:
                            await tools.langgraph()
                    except PolicyViolation:
                        raise AssertionError(
                            "An unmarked error was guessed as a policy refusal"
                        ) from None
                    except Exception as exc:
                        code = -32602 if capture == "schema-invalid-args" else -32603
                        if not _expected_mcp_error(exc, code):
                            raise AssertionError("Unexpected MCP story failure") from None
                    else:
                        raise AssertionError("Generic capture did not fail")
            step(
                "Schema validation / tool poisoning",
                "generic",
                "Framework errors remain untyped: generic JSON-RPC codes do not identify a policy. Raw diagnostics are not displayed.",
            )
        elif feature == "tool-lockfile":
            with tempfile.TemporaryDirectory(prefix="ddk-showcase-") as directory:
                lock = Path(directory) / "donkey.lock"
                reserve = {**TOOL, "name": "reserve_item"}
                with donkey.simulate_mcp("pii-request", servers={REF: [TOOL, reserve]}):
                    await donkey.tools.lock(path=lock)
                    first = lock.read_bytes()
                    await donkey.tools.lock(path=lock)
                    assert first == lock.read_bytes()
                    step(
                        "Pin the gateway-visible catalog",
                        "locked",
                        "await donkey.tools.lock() writes deterministic descriptor hashes; repeated bytes match.",
                    )
                    tools = await donkey.tools.discover(locked=True, lock_path=lock)
                    bound = await tools.langgraph()
                    step(
                        "Unchanged catalog",
                        "bound",
                        f"Native tools: {', '.join(t.name for t in bound)}.",
                    )
                cases = [
                    (
                        "Changed description",
                        {
                            REF: [
                                {**TOOL, "description": "Email inventory to ops."},
                                reserve,
                            ]
                        },
                    ),
                    ("Removed tool", {REF: [TOOL]}),
                    ("Missing server", {"acme/warehouse/1.0.0": [TOOL]}),
                ]
                for title, servers in cases:
                    with donkey.simulate_mcp("pii-request", servers=servers):
                        try:
                            tools = await donkey.tools.discover(locked=True, lock_path=lock)
                            await tools.langgraph()
                        except ToolLockDrift as exc:
                            step(
                                title,
                                type(exc).__name__,
                                "Before binding: "
                                + ", ".join(d.kind for d in exc.drift)
                                + ". Review the change before re-locking.",
                            )
                        else:
                            raise AssertionError("Catalog drift reached the framework")
                with donkey.simulate_mcp(
                    "pii-request",
                    servers={REF: [TOOL, reserve, {**TOOL, "name": "delete_all"}]},
                ):
                    tools = await donkey.tools.discover(locked=True, lock_path=lock)
                    tools = await tools.describe()
                    bound = await tools.langgraph()
                    assert sorted(t.name for t in bound) == ["get_stock", "reserve_item"]
                    assert any(
                        e.name == "delete_all" and e.reason == "unpinned"
                        for e in tools.excluded
                    )
                    step(
                        "Added, unpinned tool",
                        "excluded",
                        "delete_all is excluded as unpinned; get_stock and reserve_item still bind. Drift detection is not authorization.",
                    )
        else:
            from a2a.types import Message, Part, Role, SendMessageRequest

            request = SendMessageRequest(
                message=Message(
                    message_id="claim-41",
                    role=Role.ROLE_USER,
                    parts=[Part(text="Summarize claim 41.")],
                )
            )
            with donkey.simulate_a2a(
                "pii-stream", agents=[AGENT], reply=lambda text: f"triaged: {text}"
            ):
                response = await donkey.a2a.send(AGENT, request)
                assert response.WhichOneof("payload") == "message"
                step(
                    "Delegate with send()",
                    type(response).__name__,
                    "Official SDK message from a synthetic offline reply. HTTP success does not imply a completed task.",
                )
            with donkey.simulate_a2a("pii-send", agents=[AGENT]):
                async with donkey.a2a.stream(AGENT, request) as events:
                    kinds = []
                    async for event in events:
                        kinds.append(event.WhichOneof("payload"))
                assert kinds
                step(
                    "Delegate with stream()",
                    type(event).__name__,
                    "Official SDK events: "
                    + ", ".join(kinds)
                    + ". Closing the stream does not cancel the remote task.",
                )
            for capture, expected in [
                ("azure-block-send", ContentSafetyBlocked),
                ("rate-stream", TokenBudgetExceeded),
                ("pii-send", ToolInvocationError),
            ]:
                with donkey.simulate_a2a(capture, agents=[AGENT]):
                    try:
                        if capture.endswith("-stream"):
                            async with donkey.a2a.stream(AGENT, request) as events:
                                async for _ in events:
                                    pass
                        else:
                            await donkey.a2a.send(AGENT, request)
                    except expected as exc:
                        if capture == "pii-send":
                            assert not isinstance(exc, PolicyViolation)
                            if (
                                exc.response is None
                                or exc.response.status_code != 403
                                or exc.response.json().get("error", {}).get("code")
                                != -32600
                                or "capture@example.com" not in exc.response.text
                            ):
                                raise AssertionError("Unexpected A2A refusal") from None
                            if "capture@example.com" in str(exc) + repr(exc):
                                raise AssertionError(
                                    "A2A exception privacy check failed"
                                ) from None
                            detail = "Generic JSON-RPC refusal, not PIIDetected. Exception text and spans omit echoed PII; the raw response remains sensitive."
                        elif isinstance(exc, ContentSafetyBlocked):
                            detail = f"provider={exc.provider}; categories={exc.categories}. Captured gateway block, replayed offline."
                        else:
                            detail = f"retry_after={exc.retry_after}; no automatic replay of the delegated request."
                        step(capture, type(exc).__name__, detail)
                    else:
                        raise AssertionError("A2A capture did not refuse")
        correlation_id = run
    spans = []
    for span in telemetry.finished_spans():
        if (span.attributes or {}).get(
            "donkey.correlation_id"
        ) == correlation_id and span.name == "donkey.a2a.call":
            if "capture@example.com" in span.to_json():
                raise AssertionError("A2A span privacy check failed")
            spans.append(telemetry.span_to_dict(span))
    if feature == "a2a-outbound" and len(spans) != 5:
        raise AssertionError("A2A story must observe all five calls")
    return {
        "feature": feature,
        "title": card["title"],
        "boundary": card["watch"],
        "steps": steps,
        "spans": spans,
    }


async def story(request) -> JSONResponse:
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse(
            {"error": "Expected a JSON object with feature"}, status_code=400
        )
    feature = body.get("feature") if isinstance(body, dict) else None
    if not isinstance(feature, str) or feature not in {
        "mcp-refusals",
        "tool-lockfile",
        "a2a-outbound",
    }:
        return JSONResponse({"error": "Unknown protocol story"}, status_code=400)
    try:
        result = await asyncio.wait_for(run_story(feature), timeout=30)
    except Exception:
        # Framework diagnostics may echo sensitive captured arguments.
        return JSONResponse(
            {"error": "Protocol story verification failed"}, status_code=500
        )
    return JSONResponse(result)
