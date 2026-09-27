"""GET /api/features — the catalog rendered in the right-hand pane."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from ..features import public_features


async def features(request: Request) -> JSONResponse:
    return JSONResponse({"features": public_features()})
