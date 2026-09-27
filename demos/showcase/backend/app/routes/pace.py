"""POST /api/pace — run a small batch under donkey.budget.pace(reserve=).

Demonstrates the Budget object: fraction_used climbs call by call, and the
pace(reserve=) guard would raise BudgetReserveReached *before* crossing the
reserve (recovered with wait_for_reset()). Streams a budget snapshot after each
call so the UI's budget bar animates.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from donkey_kit import BudgetReserveReached
from starlette.requests import Request
from starlette.responses import StreamingResponse

from ..agent import build_graph, user_state
from ..donkeys import DEFAULT_MODEL, budget_snapshot, get_donkey


def _sse(event: str, data: Any) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


async def pace(request: Request) -> StreamingResponse:
    body = await request.json()
    calls = int(body.get("calls", 6))
    reserve = float(body.get("reserve", 0.05))
    donkey = get_donkey()
    model = donkey.langgraph.chat_model(DEFAULT_MODEL)
    graph = build_graph(model)

    async def stream() -> Any:
        yield _sse("start", {"calls": calls, "reserve": reserve})
        yield _sse("budget", budget_snapshot(donkey))
        for i in range(1, calls + 1):
            try:
                async with donkey.budget.pace(reserve=reserve):
                    async with donkey.run(id=f"batch-{i}", team="support", project="nightly-enrich"):
                        await graph.ainvoke(user_state(f"Enrich product record #{i}."))
                yield _sse("call", {"n": i, "status": "ok"})
                yield _sse("budget", budget_snapshot(donkey))
            except BudgetReserveReached as exc:
                yield _sse(
                    "reserve_reached",
                    {
                        "n": i,
                        "fraction_used": getattr(exc, "fraction_used", None),
                        "reserve": getattr(exc, "reserve", reserve),
                        "reset_at": exc.reset_at.isoformat() if getattr(exc, "reset_at", None) else None,
                        "remediation": getattr(exc, "remediation", None),
                    },
                )
                # In production you'd `await donkey.budget.wait_for_reset()` and
                # continue. We don't block the demo on a full window here.
                break
            await asyncio.sleep(0.15)
        yield _sse("done", {})

    return StreamingResponse(stream(), media_type="text/event-stream")
