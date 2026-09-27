"""Boot and manage DDK's local gateway simulator (``donkey mock``).

The whole demo runs against ``donkey mock`` — DDK's pure-Python stand-in for the
governed Omni Gateway proxy. It replays the *same captured fixtures* DDK's error
classifier is tested against, so a real ``PIIDetected`` / ``TokenBudgetExceeded``
/ span comes back with no Anypoint account and no credentials.

We run it as a subprocess (exactly how a developer runs it) and point
``DONKEY_LLM_PROXY_URL`` at it.
"""

from __future__ import annotations

import os
import subprocess
import time
import urllib.request

HOST = "127.0.0.1"
PORT = int(os.environ.get("DDK_SIM_PORT", "8080"))
BASE_URL = f"http://{HOST}:{PORT}"

# A short, wall-clock budget window so the pacing card is exercisable live: the
# window resets every 60s and the counter is real, so `fraction_used` climbs and
# `TokenBudgetExceeded` fires on exhaustion.
SCENARIOS = [
    "budget:limit=20000,window=60s",
    "injection:on-pattern=ignore previous",
]

_proc: subprocess.Popen | None = None


def _healthy() -> bool:
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/responses",
            data=b'{"model":"gpt-5.1","input":"ping"}',
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def start() -> None:
    """Spawn ``donkey mock`` and wait until it answers. Sets the env vars DDK
    reads so every ``Donkey.from_env()`` in the process is pointed at it."""
    global _proc
    if _healthy():
        _configure_env()
        return
    cmd = ["donkey", "mock", "--port", str(PORT)]
    for s in SCENARIOS:
        cmd += ["--scenario", s]
    _proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 20
    while time.time() < deadline:
        if _healthy():
            _configure_env()
            return
        time.sleep(0.4)
    raise RuntimeError("donkey mock did not become healthy in time")


def _configure_env() -> None:
    os.environ["DONKEY_LLM_PROXY_URL"] = BASE_URL
    os.environ.setdefault("DONKEY_LLM_PROXY_CLIENT_ID", "local")
    os.environ.setdefault("DONKEY_LLM_PROXY_CLIENT_SECRET", "local")


def stop() -> None:
    global _proc
    if _proc is not None:
        _proc.terminate()
        try:
            _proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _proc.kill()
        _proc = None


def info() -> dict[str, object]:
    return {
        "base_url": BASE_URL,
        "scenarios": SCENARIOS,
        "healthy": _healthy(),
        "managed": _proc is not None,
    }
