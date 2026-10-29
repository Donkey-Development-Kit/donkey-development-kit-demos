"""POST /api/chat — run one prompt through the governed LangGraph agent (SSE).

We invoke the graph to completion inside ``donkey.run(...)`` so a gateway refusal
surfaces cleanly as a typed exception, then stream the resulting text to the
client as ``token`` events for a live chat feel (the simulator returns a captured
completion, so real token streaming would add fragility for no fidelity). On a
refusal we emit a structured ``governance`` event; either way we finish with the
live ``budget``, ``last_call`` and OTel ``span`` for the call. When the
refusal-reactions card's ``donkey.on(...)`` reaction ran, a ``reaction`` event
says what it re-sent and how the new governed request ended.

``governed.governed_donkey`` picks the Donkey: the shared one, or a throwaway
one for ``donkey-sim/<shape>`` sentinels and the reactions card (see there why).
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from donkey_kit import (
    AuthError,
    BudgetReserveReached,
    Donkey,
    ContentSafetyBlocked,
    DonkeyError,
    GatewayApprovalPending,
    GatewayUnavailable,
    PIIDetected,
    PromptInjectionBlocked,
    RequestRateLimitExceeded,
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
    last_call_snapshot,
    message_text,
)
from ..governed import Reaction, disposition, governed_donkey, refusal_extras


def _sse(event: str, data: Any) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def governance_payload(exc: DonkeyError) -> dict[str, Any]:
    """Everything the UI needs to render a typed refusal as a first-class event."""
    payload: dict[str, Any] = {
        "type": type(exc).__name__,
        "message": str(exc),
        "remediation": getattr(exc, "remediation", None),
        "retryable": isinstance(exc, UpstreamModelError),
        "disposition": disposition(exc),
        "policy": getattr(exc, "policy", None),
        "correlation_id": getattr(exc, "correlation_id", None),
        "call_id": getattr(exc, "call_id", None),
        "request_id": getattr(exc, "request_id", None),
    }
    if isinstance(exc, PIIDetected):
        payload["entities"] = getattr(exc, "entities", None)
    if isinstance(exc, (TokenBudgetExceeded, RequestRateLimitExceeded, GatewayApprovalPending)):
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
    feature: str | None = body.get("feature")

    async def stream() -> AsyncIterator[bytes]:
        yield _sse("start", {"run_id": run_id, "model": model_id, "team": team, "project": project})
        async with governed_donkey(model_id, feature) as (donkey, reaction, scratch):
            async for frame in _run(donkey, reaction, scratch, prompt, model_id, run_id, team, project):
                yield frame

    return StreamingResponse(stream(), media_type="text/event-stream")


async def _run(
    donkey: Donkey,
    reaction: Reaction | None,
    scratch: bool,
    prompt: str,
    model_id: str,
    run_id: str,
    team: str,
    project: str,
) -> AsyncIterator[bytes]:
    """One governed call on ``donkey``, as SSE frames after ``start``."""
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
        governance.update(await refusal_extras(exc, donkey))

    recent = telemetry.recent_spans(limit=10_000)
    new_spans = recent[: max(0, len(recent) - before)]  # newest first
    if reaction is not None:
        trail = reaction.event("refused again" if governance is not None else "answered")
        if trail is not None:
            # One span per governed request, oldest first: the refusal, then the re-send.
            trail["decisions"] = [
                s["attributes"].get("donkey.policy.decision") for s in reversed(new_spans)
            ]
            yield _sse("reaction", trail)
    if governance is not None:
        yield _sse("governance", governance)
    else:
        # Stream the answer out word-by-word for a live chat feel.
        words = text.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == 0 else " " + word
            yield _sse("token", {"text": chunk})
            await asyncio.sleep(0.012)

    budget = budget_snapshot(donkey)
    # A throwaway Donkey that saw no token window has nothing to report;
    # sending its empty Budget would blank the header's shared budget bar.
    if not scratch or budget["limit"] is not None:
        yield _sse("budget", budget)
    if last_call is not None:
        yield _sse("last_call", last_call)
    if new_spans:
        yield _sse("span", new_spans[0])
    yield _sse("done", {"ok": governance is None})
