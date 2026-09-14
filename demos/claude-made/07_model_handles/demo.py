"""Demo 07 — model handles, and an SDK that refuses to invent an endpoint.

The governed proxy has no catalog endpoint. `GET /models` returns 404 — that is
verified against a real gateway, not assumed — because model-based routing only
routes requests that already carry `model` in the body.

An SDK could paper over that by guessing a path, or by shipping a hardcoded list
that goes stale. This one does neither. `list_models(live=True)` raises a
ConfigError that explains the absence, and `resolve()` gives you a local,
clearly-heuristic capability handle instead.

That is a small demo with a large point: a fabricated endpoint that 404s in a
customer's sandbox costs more trust than the missing feature ever would.

    python demos/claude-made/07_model_handles/demo.py
"""

from __future__ import annotations

import asyncio

from donkey_kit import ConfigError, Donkey, DonkeyConfig

from _harness import narrate as say
from _harness import preflight

MODELS = ("gpt-4o", "gpt-4o-mini", "o3", "claude-3-5-sonnet", "something-unknown-9")


async def act_1_resolve(donkey: Donkey) -> None:
    say.step(1, "resolve() — a local capability handle for a known model id")
    say.code(
        """
        handle = donkey.llm.resolve("gpt-4o")
        handle.capabilities
        """
    )
    for model_id in MODELS:
        handle = donkey.llm.resolve(model_id)
        say.field(model_id, handle.capabilities, raw=True)
    print()
    say.note(
        "These are heuristics derived from the model id, and the SDK says so "
        "rather than implying it asked the gateway. They are useful for routing "
        "decisions in your own code; they are not a governed catalog."
    )


async def act_2_the_missing_catalog(donkey: Donkey) -> None:
    say.step(2, "list_models(live=True) — the honest failure")
    say.code(
        """
        await donkey.llm.list_models(live=True)
        """
    )
    try:
        await donkey.llm.list_models(live=True)
        say.fail("expected a ConfigError")
    except ConfigError as exc:
        say.field("raised", "ConfigError")
        print()
        say.note(str(exc))

    print()
    say.ok(
        "It names the verified absence and points at the alternative, instead of "
        "guessing a /models path that would 404 in your sandbox."
    )


def act_3_config_errors() -> None:
    say.step(3, "The same discipline applied to configuration")
    say.note(
        "The most common reason someone abandons an SDK in the first five minutes "
        "is the one-missing-variable-per-run loop: fix a variable, re-run, "
        "discover the next one. So validation reports everything at once."
    )
    say.code(
        """
        DonkeyConfig(llm_proxy_url="https://…").validated(need="llm")
        """
    )
    try:
        DonkeyConfig(llm_proxy_url="https://example.invalid/instance/").validated(need="llm")
        say.fail("expected a ConfigError")
    except ConfigError as exc:
        print()
        for line in str(exc).splitlines():
            print(f"    {line}")

    print()
    say.note(
        "Two missing fields, one error, each naming the environment variable that "
        "sets it. And note the LLM proxy credential is validated separately from "
        "the Anypoint control-plane one — a developer may legitimately have proxy "
        "access and no Exchange access."
    )


async def _main() -> None:
    async with Donkey.from_env() as donkey:
        await act_1_resolve(donkey)
        say.pause()
        await act_2_the_missing_catalog(donkey)
        say.pause()
        act_3_config_errors()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 07 — model handles and honest gaps",
        subtitle="What the SDK does when the platform has no endpoint for what you asked.",
        target="offline",
    )
