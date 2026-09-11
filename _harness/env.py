"""Environment loading for the demos.

This is demo-harness plumbing, not part of the SDK. The SDK deliberately never
reads a `.env` file implicitly (`core.config` resolves kwargs → env var →
`.donkey-kit.toml` → default); this module is how the demos opt in on the
developer's behalf, so nobody has to paste four `export` lines before a talk.

Precedence is deliberate and matches the SDK's own rule that the most explicit
source wins:

    shell export  >  .env.local  >  .env  >  unset

Values are written with `setdefault`, so anything already exported survives. The
files are searched in the repo root first, then the current directory.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["REPO_ROOT", "load", "mock_url", "proxy_configured", "target_is_mock"]

REPO_ROOT = Path(__file__).resolve().parents[1]

_FILENAMES = (".env.local", ".env")

PROXY_VARS = (
    "DONKEY_LLM_PROXY_URL",
    "DONKEY_LLM_PROXY_CLIENT_ID",
    "DONKEY_LLM_PROXY_CLIENT_SECRET",
)

# Any non-empty pair works: the simulator replays fixtures and enforces no auth.
# Naming them this way makes it obvious in `env | grep` that they are not real.
MOCK_CLIENT_ID = "demo-mock-client-id-not-a-real-credential"
MOCK_CLIENT_SECRET = "demo-mock-client-secret-not-a-real-credential"


def _parse(path: Path) -> dict[str, str]:
    """Read a dotenv file. Supports `KEY=value`, `export KEY=value`, `#` comments
    and single/double quoted values. Anything else on a line is ignored rather
    than raising — a malformed line should not stop a demo."""
    out: dict[str, str] = {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            out[key] = value
    return out


def load() -> list[Path]:
    """Load the dotenv files into `os.environ` and return which ones were used."""
    used: list[Path] = []
    seen: set[Path] = set()
    for directory in (REPO_ROOT, Path.cwd()):
        for name in _FILENAMES:
            path = (directory / name).resolve()
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            for key, value in _parse(path).items():
                os.environ.setdefault(key, value)
            used.append(path)
    return used


def mock_url() -> str:
    """Base URL of the local simulator."""
    return os.environ.get("DEMO_MOCK_URL", "http://127.0.0.1:8080").rstrip("/") + "/"


def proxy_configured() -> bool:
    """Whether all three governed-proxy variables hold a non-empty value."""
    return all(os.environ.get(v) for v in PROXY_VARS)


def target_is_mock() -> bool:
    """Whether the configured proxy URL points at a loopback address, i.e. the
    simulator rather than a real gateway."""
    url = os.environ.get("DONKEY_LLM_PROXY_URL", "")
    return any(h in url for h in ("127.0.0.1", "localhost", "0.0.0.0", "[::1]"))


# Loading on import is intentional: a demo's first line is `from _harness import
# demo`, and everything after it expects the environment to be populated.
load()
