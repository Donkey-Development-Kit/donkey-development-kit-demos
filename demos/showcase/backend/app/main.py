"""DDK demo backend — a Starlette app that runs the governed LangGraph agent
against DDK's local gateway simulator and exposes it to the React frontend.

Boot order matters:
1. Install the in-memory OTel exporter (must precede the first governed call).
2. On startup, spawn ``donkey mock`` and point DDK's env vars at it.
3. Serve the API; optionally serve the built frontend from ``frontend/dist``.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import simulator, telemetry
from .routes.chat import chat
from .routes.cli import doctor
from .routes.compare import compare
from .routes.conformance import conformance
from .routes.features import features
from .routes.pace import pace
from .routes.telemetry import budget, simulator_info, spans

# Install telemetry before anything can trigger a governed call.
telemetry.install()


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    simulator.start()
    yield
    simulator.stop()


async def health(request) -> JSONResponse:
    return JSONResponse({"ok": True, "simulator": simulator.info()})


routes = [
    Route("/api/health", health),
    Route("/api/features", features),
    Route("/api/chat", chat, methods=["POST"]),
    Route("/api/compare", compare, methods=["POST"]),
    Route("/api/pace", pace, methods=["POST"]),
    Route("/api/conformance", conformance, methods=["POST"]),
    Route("/api/doctor", doctor, methods=["POST"]),
    Route("/api/spans", spans),
    Route("/api/budget", budget),
    Route("/api/simulator", simulator_info),
]

# Serve the built frontend in production if present (dev uses the Vite server).
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.is_dir():
    routes.append(Mount("/", app=StaticFiles(directory=str(_dist), html=True), name="frontend"))

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(routes=routes, middleware=middleware, lifespan=lifespan)
