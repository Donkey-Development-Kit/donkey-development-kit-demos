"""Read-only telemetry endpoints: recent OTel spans, budget, simulator info."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from .. import simulator, telemetry
from ..donkeys import budget_snapshot, get_donkey


async def spans(request: Request) -> JSONResponse:
    return JSONResponse({"spans": telemetry.recent_spans(limit=25)})


async def budget(request: Request) -> JSONResponse:
    return JSONResponse(budget_snapshot(get_donkey()))


async def simulator_info(request: Request) -> JSONResponse:
    return JSONResponse(simulator.info())
