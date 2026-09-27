"""POST /api/doctor — run `donkey doctor` live against the simulator.

`donkey doctor` tells a wrong URL from wrong credentials from a model that is not
on the proxy's allow-list — one diagnosis instead of one opaque failure.
"""

from __future__ import annotations

import asyncio
import os

from starlette.requests import Request
from starlette.responses import JSONResponse


async def doctor(request: Request) -> JSONResponse:
    env = dict(os.environ)
    proc = await asyncio.create_subprocess_exec(
        "donkey",
        "doctor",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
    except asyncio.TimeoutError:
        proc.kill()
        return JSONResponse({"ok": False, "output": "donkey doctor timed out."})
    return JSONResponse({"ok": proc.returncode == 0, "output": out.decode(errors="replace")})
