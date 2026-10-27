#!/usr/bin/env python3
"""Run the new straight-line, credential-free examples in fresh processes."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = (
    "openai/17 - refusal-handlers.py",
    "openai/18 - dynamic-provider-key.py",
    "langgraph/10 - tool-approvals.py",
    "openai-agents/04 - approvals.py",
    "openai-agents/05 - governed-observations.py",
    "conformance/verify.py",
    "a2a/verify.py",
)
FRAMEWORKS = (
    "strands/05 - approvals.py",
    "adk/03 - approvals.py",
    "adk/04 - bridged-observations.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frameworks", action="store_true", help="run only ADK/Strands")
    args = parser.parse_args()
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("DONKEY_", "ANYPOINT_", "OTEL_"))
        and key.lower() not in {"http_proxy", "https_proxy", "all_proxy"}
    }
    env.update(PYTHONPATH=str(ROOT), NO_PROXY="*", PYTHONUNBUFFERED="1")
    for script in FRAMEWORKS if args.frameworks else BASE:
        print(f"\nVerifying {script}", flush=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / "demos/human-made" / script)],
            cwd=ROOT,
            env=env,
            timeout=90,
            check=False,
        )
        if result.returncode:
            return result.returncode
    print("All SDK coverage examples passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
