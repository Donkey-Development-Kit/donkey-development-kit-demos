"""POST /api/chat — run one prompt through the governed LangGraph agent (SSE).

We invoke the graph to completion inside ``donkey.run(...)`` so a gateway refusal
surfaces cleanly as a typed exception, then stream the resulting text to the
client as ``token`` events for a live chat feel (the simulator returns a captured
completion, so real token streaming would add fragility for no fidelity). On a
refusal we emit a structured ``governance`` event; either way we finish with the
live ``budget``, ``last_call`` and OTel ``span`` for the call.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from donkey_kit import (
    AuthError,
    BudgetReserveReached,
    ContentSafetyBlocked,
    DonkeyError,
    GatewayUnavailable,
    PIIDetected,
    PromptInjectionBlocked,
    TokenBudgetExceeded,
    UpstreamModelError,
)
from donkey_kit.core.errors import UpstreamRequestError
from starlette.requests import Request
from starlette.responses import StreamingResponse

from .. import telemetry
from ..agent import build_graph, user_state
from ..donkeys import (
    DEFAULT_MODEL,
    budget_snapshot,
    get_donkey,
    last_call_snapshot,
    message_text,
)


def _sse(event: str, data: Any) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def governance_payload(exc: DonkeyError) -> dict[str, Any]:
    """Everything the UI needs to render a typed refusal as a first-class event."""
    payload: dict[str, Any] = {
        "type": type(exc).__name__,
        "message": str(exc),
        "remediation": getattr(exc, "remediation", None),
        "retryable": isinstance(exc, UpstreamModelError),
        "correlation_id": getattr(exc, "correlation_id", None),
        "call_id": getattr(exc, "call_id", None),
        "request_id": getattr(exc, "request_id", None),
    }
    if isinstance(exc, PIIDetected):
        payload["entities"] = getattr(exc, "entities", None)
    if isinstance(exc, TokenBudgetExceeded):
        payload["retry_after"] = getattr(exc, "retry_after", None)
    if isinstance(exc, ContentSafetyBlocked):
        payload["categories"] = getattr(exc, "categories", None)
    if isinstance(exc, UpstreamRequestError):
        payload["code"] = getattr(exc, "code", None)
        payload["error_type"] = getattr(exc, "error_type", None)
    if isinstance(exc, GatewayUnavailable):
        payload["base_url"] = getattr(exc, "base_url", None)
    return payload


async def chat(request: Request) -> StreamingResponse:
    body = await request.json()
    prompt: str = (body.get("prompt") or "").strip()
    model_id: str = body.get("model") or DEFAULT_MODEL
    team = body.get("team") or "support"
    project = body.get("project") or "triage-v2"
    run_id = body.get("run_id") or f"run-{uuid.uuid4().hex[:12]}"

    donkey = get_donkey()

    async def stream() -> Any:
        yield _sse("start", {"run_id": run_id, "model": model_id, "team": team, "project": project})
        before = len(telemetry.recent_spans(limit=10_000))
        last_call: dict[str, Any] | None = None
        governance: dict[str, Any] | None = None
        text = ""

        try:
            model = donkey.langgraph.chat_model(model_id)
            graph = build_graph(model)
            async with donkey.run(id=run_id, team=team, project=project):
                result = await graph.ainvoke(user_state(prompt))
                # last_call is contextvar-scoped: read it INSIDE the run block.
                last_call = last_call_snapshot(donkey)
            text = message_text(result["messages"][-1])
        except (
            PIIDetected,
            TokenBudgetExceeded,
            PromptInjectionBlocked,
            ContentSafetyBlocked,
            AuthError,
            UpstreamRequestError,
            UpstreamModelError,
            GatewayUnavailable,
            BudgetReserveReached,
            DonkeyError,
        ) as exc:
            governance = governance_payload(exc)

        if governance is not None:
            yield _sse("governance", governance)
        else:
            # Stream the answer out word-by-word for a live chat feel.
            words = text.split(" ")
            for i, word in enumerate(words):
                chunk = word if i == 0 else " " + word
                yield _sse("token", {"text": chunk})
                await asyncio.sleep(0.012)

        yield _sse("budget", budget_snapshot(donkey))
        if last_call is not None:
            yield _sse("last_call", last_call)
        recent = telemetry.recent_spans(limit=10_000)
        new_spans = recent[: max(0, len(recent) - before)]
        if new_spans:
            yield _sse("span", new_spans[0])
        yield _sse("done", {"ok": governance is None})

    return StreamingResponse(stream(), media_type="text/event-stream")
