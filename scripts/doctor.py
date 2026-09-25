#!/usr/bin/env python3
"""What is installed here, and therefore what will run.

Run this before a talk. It answers the three questions that actually go wrong on
stage: is the SDK importable, is the simulator installed, and are the live
credentials loaded — without printing any of their values.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _harness import env, redact  # noqa: E402
from _harness import narrate as say

CHECKS = [
    ("donkey_kit", "the SDK itself", "donkey"),
    ("openai", "the raw client and every offline demo", "llm"),
    ("starlette", "the local simulator", "local"),
    ("uvicorn", "the local simulator", "local"),
    ("pytest", "the conformance demo", "test"),
    ("opentelemetry.sdk", "the telemetry demo", "otel"),
    ("langchain_openai", "the LangGraph demos", "langgraph"),
    ("langgraph", "the LangGraph agent demo", "langgraph"),
]

# Required, but not shipped in any donkey-kit extra: (module, why, pip spec).
PACKAGES = [
    ("langchain", "the LangGraph agent demo", "langchain>=1.0"),
]

OPTIONAL = [
    ("anthropic", "anthropic"),
    ("crewai", "crewai"),
    ("llama_index", "llamaindex"),
    ("strands", "strands"),
    ("google.adk", "adk"),
    ("agents", "openai-agents"),
    ("agent_framework", "agent-framework"),
]


def _installed(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def main() -> int:
    say.title("Demo environment check")

    say.section("Required")
    missing_required = []
    for module, why, extra in CHECKS:
        present = _installed(module)
        (say.ok if present else say.fail)(f"{module:<20} {why}")
        if not present:
            missing_required.append(extra)
    missing_packages = []
    for module, why, spec in PACKAGES:
        present = _installed(module)
        (say.ok if present else say.fail)(f"{module:<20} {why}")
        if not present:
            missing_packages.append(spec)

    say.section("Optional frameworks (demo 08 reports these as 'not installed')")
    for module, extra in OPTIONAL:
        state = "installed" if _installed(module) else f'pip install "donkey-kit[{extra}]"'
        print(f"  {module:<20} {state}")

    say.section("CLI")
    cli = shutil.which("donkey")
    (say.ok if cli else say.fail)(
        "donkey on PATH" if cli else 'donkey missing — pip install "donkey-kit[cli]"'
    )

    say.section("Configuration")
    loaded = env.load()
    say.field("dotenv files read", ", ".join(str(p.name) for p in loaded) or "none")
    import os

    for var in env.PROXY_VARS:
        short = var.replace("DONKEY_LLM_PROXY_", "proxy ").lower()
        say.field(short, "set" if os.environ.get(var) else "not set")
    say.field("mock URL", env.mock_url())
    say.field("output masking", "on" if redact.enabled() else "OFF")

    say.section("What you can run")
    if not missing_required:
        say.ok("every offline demo (make offline)")
    else:
        say.warn(f'missing extras: pip install "donkey-kit[{",".join(sorted(set(missing_required)))}]"')
    if missing_packages:
        specs = " ".join(f'"{s}"' for s in missing_packages)
        say.warn(f"missing packages: pip install {specs}")
    if env.proxy_configured() and not missing_packages:
        say.ok("the live demos (make demo N=09)")
    elif env.proxy_configured():
        say.warn("credentials set, but the live demos need the missing packages above")
    else:
        print("  live demos need the three DONKEY_LLM_PROXY_* variables")

    warning = redact.why_visible()
    if warning:
        print()
        say.warn(warning)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
