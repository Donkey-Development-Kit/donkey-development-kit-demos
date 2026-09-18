"""The single entry point every demo goes through.

One place decides whether a demo can run, against what, and what to say when it
cannot — instead of each script re-implementing its own credential check. It
owns four things:

* **Target selection.** `--target mock` (the default) points the SDK at the
  local simulator with obviously-fake credentials. `--target live` uses your
  real ones and refuses to run without all three.
* **Prerequisite checks.** A missing framework extra reports the exact
  `pip install`, and a demo that needs live credentials exits *cleanly* with
  guidance rather than raising — a stack trace on a projector teaches nothing.
* **The banner.** Every run states its target and whether output is masked, so
  a recording contains proof of which mode it was in.
* **Error containment.** Anything that escapes `main()` is scrubbed through
  `redact.text()` before printing, so an exception message carrying the gateway
  host does not undo the masking everywhere else.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from collections.abc import Callable, Sequence

from . import env, mock, narrate, redact

__all__ = ["Target", "run"]

# What a demo needs to run:
#   "offline"  nothing at all — no gateway, no simulator, no credentials
#   "mock"     the local simulator, started automatically
#   "live"     a real governed proxy; no simulator equivalent exists
#   "either"   works both ways; defaults to the simulator
Target = str

_EXTRA_FOR_MODULE = {
    "openai": "llm",
    "langchain_openai": "langgraph",
    "langgraph": "langgraph",
    "starlette": "local",
    "uvicorn": "local",
    "pytest": "test",
    "opentelemetry.sdk": "otel",
    "anthropic": "anthropic",
    "crewai": "crewai",
    "llama_index": "llamaindex",
    "strands": "strands",
    "google.adk": "adk",
    "agents": "openai-agents",
    "agent_framework": "agent-framework",
}


def _installed(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _missing_extras(modules: Sequence[str]) -> list[tuple[str, str]]:
    return [
        (m, _EXTRA_FOR_MODULE.get(m, m)) for m in modules if not _installed(m)
    ]


def _parse_args(default_target: Target, argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True, description="Donkey Development Kit (DDK) demo")
    parser.add_argument(
        "--target",
        choices=("mock", "live"),
        default=None,
        help="run against the local simulator (default) or your real governed proxy",
    )
    parser.add_argument(
        "--no-autostart",
        action="store_true",
        help="do not start a simulator; attach to one already running",
    )
    args = parser.parse_args(argv)
    if args.target is None:
        args.target = "mock" if default_target in ("mock", "either") else "live"
    return args


def _banner(target: str, base_url: str) -> None:
    narrate.section("Run context")
    narrate.field("target", target)
    narrate.field("proxy base_url", redact.url(base_url))
    narrate.field("output masking", "on" if redact.enabled() else "OFF")
    if target == "mock":
        narrate.field("credentials", "fake — the simulator enforces no auth")
    else:
        narrate.field(
            "credentials",
            redact.secret(os.environ.get("DONKEY_LLM_PROXY_CLIENT_ID")),
        )
    warning = redact.why_visible()
    if warning:
        print()
        narrate.warn(warning)


def _live_guidance() -> None:
    narrate.section("This demo needs a real governed proxy")
    narrate.note(
        "It is the live half of the walkthrough, so it needs credentials for an "
        "actual Omni Gateway LLM proxy instance. Nothing was run and nothing failed."
    )
    print()
    narrate.bullet("Set these three, or put them in a git-ignored .env.local:")
    for var in env.PROXY_VARS:
        state = "set" if os.environ.get(var) else "MISSING"
        print(f"      {var:<42} {state}")
    print()
    narrate.bullet("Or see the same capability offline, with no credentials at all:")
    print("      make offline")


def run(
    main: Callable[[], None],
    *,
    title: str,
    subtitle: str = "",
    target: Target = "mock",
    extras: Sequence[str] = (),
    argv: Sequence[str] | None = None,
) -> int:
    """Run a demo's `main()` with the environment prepared and guarded.

    `target` is what the demo *wants*: `"mock"` for an offline demo, `"live"` for
    one that only makes sense against a real gateway, `"either"` when it works
    both ways and should default to the simulator. `extras` names the importable
    modules it needs, reported as `pip install "donkey-kit[<extra>]"`.
    """
    args = _parse_args(target, argv)
    narrate.title(title, subtitle or None)

    missing = _missing_extras(extras)
    if missing:
        narrate.section("Missing prerequisites")
        for module, extra in missing:
            narrate.bullet(f'{module} — pip install "donkey-kit[{extra}]"')
        return 0

    if target == "offline":
        narrate.section("Run context")
        narrate.field("target", "offline — no gateway, no simulator, no credentials")
        narrate.field("output masking", "on" if redact.enabled() else "OFF")
        warning = redact.why_visible()
        if warning:
            print()
            narrate.warn(warning)
        return _invoke(main)

    if target == "live" and args.target == "mock":
        # The demo cannot be faked; say so rather than silently doing something else.
        narrate.note(
            "This demo has no simulator equivalent, so --target mock does not apply."
        )
        args.target = "live"

    if args.target == "live":
        if not env.proxy_configured():
            _live_guidance()
            return 0
        _banner("live", os.environ.get("DONKEY_LLM_PROXY_URL", ""))
        return _invoke(main)

    if not _installed("starlette") or not _installed("uvicorn"):
        narrate.section("Missing prerequisites")
        narrate.bullet('the local simulator needs: pip install "donkey-kit[local]"')
        return 0

    try:
        with mock.running(autostart=not args.no_autostart) as base_url:
            os.environ["DONKEY_LLM_PROXY_URL"] = base_url
            os.environ["DONKEY_LLM_PROXY_CLIENT_ID"] = env.MOCK_CLIENT_ID
            os.environ["DONKEY_LLM_PROXY_CLIENT_SECRET"] = env.MOCK_CLIENT_SECRET
            _banner("mock", base_url)
            return _invoke(main)
    except RuntimeError as exc:
        narrate.section("Could not start the local simulator")
        narrate.note(redact.text(exc))
        return 1


def _invoke(main: Callable[[], None]) -> int:
    try:
        main()
    except KeyboardInterrupt:
        print()
        narrate.note("interrupted")
        return 130
    except Exception as exc:  # noqa: BLE001 — a demo must not spray a raw trace
        print()
        narrate.section("The demo raised")
        narrate.field("type", type(exc).__name__)
        narrate.field("message", redact.text(exc))
        if os.environ.get("DEMO_TRACEBACK", "0") in ("1", "true", "yes"):
            import traceback

            print()
            print(redact.text(traceback.format_exc()))
        else:
            print()
            narrate.note("Set DEMO_TRACEBACK=1 for the full (still masked) traceback.")
        return 1
    print()
    narrate.rule()
    return 0


def cli(main: Callable[[], None], **kw: object) -> None:
    """`run()` plus `sys.exit`, for a demo's `__main__` block."""
    sys.exit(run(main, **kw))  # type: ignore[arg-type]
