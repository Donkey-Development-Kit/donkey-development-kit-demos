"""POST /api/conformance — grade the demo's own agent against every refusal shape.

Runs DDK's conformance suite in-process via ``run_conformance`` (the same suite
the ``pytest --donkey-conformance`` plugin drives) against the factory in
``tests.agent_app`` — the same graph the chat uses. Returns the
scenario → pass / fail / exempt table the UI renders.
"""

from __future__ import annotations

from typing import Any

from donkey_kit.conformance.harness import run_conformance
from starlette.requests import Request
from starlette.responses import JSONResponse

# Import the agent factory the same way pytest would (module:attr).
from tests.agent_app import KNOWN_LIMITATIONS, build


async def conformance(request: Request) -> JSONResponse:
    results = await run_conformance(build, known_limitations=KNOWN_LIMITATIONS)
    rows: list[dict[str, Any]] = [
        {"name": r.scenario, "title": r.title, "status": r.status, "detail": r.detail}
        for r in results
    ]
    summary = {
        "pass": sum(1 for r in rows if r["status"] == "pass"),
        "fail": sum(1 for r in rows if r["status"] == "fail"),
        "exempt": sum(1 for r in rows if r["status"] == "exempt"),
        "total": len(rows),
    }
    return JSONResponse({"rows": rows, "summary": summary})
