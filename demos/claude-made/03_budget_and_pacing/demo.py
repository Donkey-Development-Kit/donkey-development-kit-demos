"""Demo 03 — the token budget, and refusing to cross it before the gateway does.

The gateway reports budget only in-band, on `x-token-*` response headers. There
is no endpoint to ask "how much is left", so a brand-new process knows nothing
until its first call returns. `donkey.budget` is that window as an object: the
developer never parses a header, and `observed_at` is there so nobody mistakes
stale data for live data.

Pacing is the useful half. `pace(reserve=…)` refuses locally *before* issuing a
request that would cross your reserve, which turns a 429 you have to recover
from into an exception you chose to raise.

    python demos/claude-made/03_budget_and_pacing/demo.py
"""

from __future__ import annotations

import asyncio
import os

import httpx
from donkey_kit import BudgetReserveReached, Donkey, TokenBudgetExceeded
from donkey_kit.core.budget import LIMIT_HEADER, REMAINING_HEADER, RESET_HEADER
from donkey_kit.core.errors import classify

from _harness import mock, preflight
from _harness import narrate as say

MODEL = os.environ.get("DEMO_MODEL", "gpt-4o")


def _show(budget: object, label: str) -> None:
    fraction = getattr(budget, "fraction_used", None)
    say.field(
        label,
        f"remaining={getattr(budget, 'remaining', None)}  "
        f"limit={getattr(budget, 'limit', None)}  "
        f"used={f'{fraction:.1%}' if fraction is not None else 'unobserved'}",
        raw=True,
    )


async def act_1_cold_start(donkey: Donkey) -> None:
    say.step(1, "A new process knows nothing until its first call returns")
    _show(donkey.budget, "before any call")
    say.note(
        "Every field is None rather than zero. An unobserved budget reports "
        "'I don't know', because reporting 0 remaining would be a lie that stops "
        "an agent that could have run."
    )


async def act_2_in_band(donkey: Donkey) -> None:
    say.step(2, "Each response updates the window, with no code from you")
    say.code(
        """
        await client.responses.create(model=..., input=...)
        donkey.budget.remaining      # already up to date
        """
    )

    client = donkey.openai()
    for i in range(1, 4):
        await client.responses.create(model=MODEL, input=f"ping {i}")
        _show(donkey.budget, f"after call {i}")

    say.field("observed_at", donkey.budget.observed_at, raw=True)
    say.field("reset_at", donkey.budget.reset_at, raw=True)
    print()
    say.warn(
        "Honesty note: the simulator synthesises this decreasing window. Budget "
        "headers on a 200 are NOT yet confirmed against a real proxy — they are "
        "verified on the 429 refusal. Treat the shape as real and the happy-path "
        "numbers as illustrative."
    )


async def act_3_pacing(donkey: Donkey) -> None:
    say.step(3, "pace(reserve=…) refuses before the request goes out")
    say.note(
        "Rather than issue the 200 calls it would take to drain the simulator's "
        "window, we let the budget observe a response that says we are already at "
        "96% — the same code path a real near-exhausted window takes."
    )
    say.code(
        """
        async with donkey.budget.pace(reserve=0.05):
            await enrich(batch)            # never runs if the reserve is crossed
        """
    )

    near_exhausted = httpx.Response(
        200,
        headers={LIMIT_HEADER: "100000", REMAINING_HEADER: "4000", RESET_HEADER: "3000"},
    )
    donkey.budget.observe(near_exhausted)
    _show(donkey.budget, "observed")

    print()
    try:
        async with donkey.budget.pace(reserve=0.05):
            say.fail("the guarded block ran — it should not have")
    except BudgetReserveReached as exc:
        say.ok("BudgetReserveReached — the request was never issued")
        say.field("fraction_used", f"{exc.fraction_used:.1%}", raw=True)
        say.field("reserve", f"{exc.reserve:.1%}", raw=True)
        say.field("reset_at", exc.reset_at, raw=True)

    print()
    say.note(
        "BudgetReserveReached is deliberately NOT a PolicyViolation. A refusal is "
        "the gateway saying no and is terminal; this is your own client-side "
        "signal, raised locally, that you are expected to recover from."
    )

    say.code(
        """
        try:
            async with donkey.budget.pace(reserve=0.05):
                await enrich(batch)
        except BudgetReserveReached:
            await donkey.budget.wait_for_reset()   # one sleep, never a spin loop
        """
    )
    say.note("wait_for_reset() would sleep ~3s here; skipping the sleep for the demo.")


async def act_4_the_refusal_itself(donkey: Donkey) -> None:
    say.step(4, "And if you do cross it, the 429 is terminal")
    client = donkey.openai()
    try:
        await client.responses.create(model=mock.sentinel("token-rate-limit"), input="x")
        say.warn("expected a 429")
        return
    except Exception as exc:  # noqa: BLE001 — the openai error type varies by status
        response = getattr(exc, "response", None)
        if response is None:
            raise
        error = classify(response)

    say.field("classified as", type(error).__name__)
    say.field("retry_after", getattr(error, "retry_after", None), raw=True)
    if isinstance(error, TokenBudgetExceeded):
        say.ok("The transport never retried it — retrying only burns the same window.")
    print()
    say.note(
        "This is the scenario the conformance suite checks other people's agents "
        "for, because retrying a budget refusal is the single most common way an "
        "agent turns one refusal into a rate-limit spiral. See demo 05."
    )


async def _main() -> None:
    async with Donkey.from_env() as donkey:
        await act_1_cold_start(donkey)
        say.pause()
        await act_2_in_band(donkey)
        say.pause()
        await act_3_pacing(donkey)
        say.pause()
        await act_4_the_refusal_itself(donkey)


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 03 — budget and pacing",
        subtitle="The token window as an object, and refusing to cross it before the gateway does.",
        target="mock",
        extras=("openai",),
    )
