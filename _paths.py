"""Dev-time convenience for the demos: an optional .env loader.

Demo-only sugar (the SDK itself never reads env files implicitly — see
``core/config.py`` in the SDK). Loads ``.env.local`` then ``.env`` from this
directory and the current working directory into ``os.environ`` so
``export``-ing the ``AGENT_FABRIC_LLM_PROXY_*`` vars by hand is optional. Values
already present in the environment win — an explicit shell ``export`` is never
overridden.

The demos need ``agent_fabric`` importable; install the SDK first (see the
README): ``pip install "agent-fabric[llm] @ git+https://github.com/Agent-Fabric-SDK/agent-fabric-sdk.git#subdirectory=python"``.

Importing this module runs the loader.
"""

from __future__ import annotations

import os
from pathlib import Path


# --- minimal, dependency-free .env loader ----------------------------------
def _parse_env(text: str) -> dict[str, str]:
    """Parse KEY=VALUE lines. Ignores blanks, ``#`` comments, and a leading
    ``export``; strips matching single/double quotes. No interpolation."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        line = line.removeprefix("export ")
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            out[key] = value
    return out


_HERE = Path(__file__).resolve().parent


def _load_env_files() -> None:
    # Search this directory (repo root, next to _paths.py) then the cwd, so a
    # .env.local sitting beside the demos is picked up. Precedence via
    # setdefault (first writer wins): explicit os.environ export > .env.local >
    # .env, and earlier directories win over later ones.
    seen: set[Path] = set()
    for base in (_HERE, Path.cwd()):
        if base in seen:
            continue
        seen.add(base)
        for name in (".env.local", ".env"):
            path = base / name
            if not path.is_file():
                continue
            for key, value in _parse_env(path.read_text()).items():
                os.environ.setdefault(key, value)


_load_env_files()
