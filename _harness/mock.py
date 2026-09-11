"""Lifecycle for the SDK's local gateway simulator (`donkey mock`).

The simulator is a separate process serving the *same captured fixtures* that
`donkey_kit.core.errors.classify()` is tested against. That is what makes the
offline demos honest: they are not mocking the SDK, they are replaying real
recorded gateway responses through the real SDK.

Two things worth knowing before writing a demo against it:

* It answers `POST <base>/responses` and `GET <base>/models`. It does **not**
  implement `/chat/completions` — an unknown route returns the captured 404. So
  demos use the Responses API, which is the live-verified route anyway.
* Rejections are selected by a sentinel model id, `donkey-sim/<shape>`. That is
  a simulator control surface and never real gateway behaviour.

Every response it sends carries `x-donkey-simulator: true`.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from urllib.parse import urlparse

from . import env

__all__ = ["REJECTION_SHAPES", "SIMULATOR_HEADER", "is_up", "running", "sentinel"]

SIMULATOR_HEADER = "x-donkey-simulator"

# The shapes `donkey-sim/<shape>` can select, mirroring
# `donkey_kit.simulator.app._REJECTION_SHAPES`. Kept as a plain tuple so a
# demo can iterate them without importing a private SDK name.
REJECTION_SHAPES = (
    "token-rate-limit",
    "pii-detected",
    "injection-protection",
    "content-moderation",
    "model-not-found",
    "upstream-5xx",
    "client-id-missing",
)


def sentinel(shape: str) -> str:
    """The model id that makes the simulator serve `shape`."""
    if shape not in REJECTION_SHAPES:
        raise ValueError(f"unknown simulator shape {shape!r}; expected one of {REJECTION_SHAPES}")
    return f"donkey-sim/{shape}"


def is_up(url: str | None = None, *, timeout: float = 0.75) -> bool:
    """Whether a simulator is already answering at `url`.

    Identified by the honesty header, not merely by something accepting the
    port — pointing a demo at an unrelated service listening on 8080 would be a
    confusing failure.
    """
    import httpx

    target = url or env.mock_url()
    try:
        response = httpx.get(target, timeout=timeout)
    except (httpx.HTTPError, OSError):
        return False
    return SIMULATOR_HEADER in {k.lower() for k in response.headers}


def _wait_until_up(url: str, *, deadline_s: float = 15.0) -> bool:
    end = time.monotonic() + deadline_s
    while time.monotonic() < end:
        if is_up(url, timeout=0.5):
            return True
        time.sleep(0.25)
    return False


@contextlib.contextmanager
def running(*, url: str | None = None, autostart: bool = True) -> Iterator[str]:
    """Yield the base URL of a live simulator.

    Reuses one that is already listening — so a presenter can start
    `donkey mock` in a visible second pane and every demo will attach to
    it — and otherwise starts one in the background and stops it on exit.
    """
    target = url or env.mock_url()

    if is_up(target):
        yield target
        return

    if not autostart:
        raise RuntimeError(
            f"No simulator at {target} and autostart is off. Start one with:\n"
            f"    donkey mock --port {urlparse(target).port or 8080}"
        )

    if shutil.which("donkey") is None:
        raise RuntimeError(
            "The `donkey` CLI is not on PATH. Install the SDK with the "
            'local extra:\n    pip install "donkey-kit[llm,local]"'
        )

    parsed = urlparse(target)
    proc = subprocess.Popen(
        [
            "donkey",
            "mock",
            "--host",
            parsed.hostname or "127.0.0.1",
            "--port",
            str(parsed.port or 8080),
        ],
        stdout=subprocess.DEVNULL if os.environ.get("DEMO_QUIET_MOCK", "1") == "1" else None,
        stderr=subprocess.STDOUT,
    )
    try:
        if not _wait_until_up(target):
            proc.terminate()
            raise RuntimeError(
                f"Started `donkey mock` but nothing answered at {target} "
                f"within 15s. Is the port in use? Try DEMO_MOCK_URL=http://127.0.0.1:8099"
            )
        print(f"  (started a local simulator at {target}; it stops when this demo exits)")
        yield target
    finally:
        proc.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)
        if proc.poll() is None:  # pragma: no cover - only if terminate is ignored
            proc.kill()
        print("  (simulator stopped)", file=sys.stderr if not sys.stdout.isatty() else sys.stdout)
