"""Demo 04 — testing your refusal branch without a gateway.

Every agent has a `except PIIDetected:` branch that has never executed. Getting
a real gateway to refuse on demand means finding a prompt that trips a live
policy, which is slow, flaky, and not something you can put in CI.

`donkey.simulate()` swaps a fixture-returning transport onto the client for the
next N calls. The body it injects is the *same captured fixture* `classify()` is
tested against, so the branch runs against exactly the refusal a real gateway
sent — with no network, no server and no credentials.

    python demos/claude-made/04_simulate_refusals/demo.py
"""

from __future__ import annotations

import asyncio
import logging

import openai
from donkey_kit import (
    ContentSafetyBlocked,
    Donkey,
    PIIDetected,
    TokenBudgetExceeded,
)
from donkey_kit.core.errors import DonkeyError, classify

from _harness import narrate as say
from _harness import preflight

log = logging.getLogger("demo.agent")


class TinyAgent:
    """A stand-in for the thing you actually ship: one model call, wrapped in the
    refusal handling you hope is correct."""

    def __init__(self, donkey: Donkey) -> None:
        self._donkey = donkey
        self.handled: list[str] = []

    async def run(self, prompt: str) -> str:
        client = self._donkey.openai()
        try:
            response = await client.responses.create(model="gpt-4o", input=prompt)
        except openai.APIStatusError as exc:
            error = classify(exc.response)
            return self._on_refusal(error)
        return getattr(response, "output_text", "<ok>")

    def _on_refusal(self, error: DonkeyError) -> str:
        """The branch that never runs in development."""
        self.handled.append(type(error).__name__)
        if isinstance(error, PIIDetected):
            return f"redacted {error.entities} and asked the user to rephrase"
        if isinstance(error, TokenBudgetExceeded):
            return f"queued for retry after {error.retry_after:.0f}s — did NOT retry now"
        return f"escalated: {type(error).__name__}"


async def act_1_the_problem(agent: TinyAgent) -> None:
    say.step(1, "Normally, the happy path is all you ever exercise")
    result = await agent.run("hello")
    say.field("agent returned", result)
    say.field("refusal branch ran", bool(agent.handled), raw=True)


async def act_2_inject(donkey: Donkey, agent: TinyAgent) -> None:
    say.step(2, "One context manager, and the branch runs")
    say.code(
        """
        with donkey.simulate(PIIDetected):
            await agent.run("...")     # fails as a real PIIDetected
        """
    )

    with donkey.simulate(PIIDetected):
        result = await agent.run("my email is a@b.com")
    say.field("agent returned", result)
    say.field("handled", agent.handled, raw=True)
    say.ok("The branch executed against the real captured 403 body.")


async def act_3_each_refusal(donkey: Donkey, agent: TinyAgent) -> None:
    say.step(3, "Every refusal you need to handle, one line each")
    for error_type in (TokenBudgetExceeded, PIIDetected):
        with donkey.simulate(error_type):
            result = await agent.run("anything")
        say.field(error_type.__name__, result)


async def act_4_times_and_scope(donkey: Donkey, agent: TinyAgent) -> None:
    say.step(4, "`times` counts calls, and normal service resumes after")
    say.code(
        """
        with donkey.simulate(TokenBudgetExceeded, times=2):
            await agent.run("a")   # refused
            await agent.run("b")   # refused
            await agent.run("c")   # succeeds — the injection is spent
        """
    )
    with donkey.simulate(TokenBudgetExceeded, times=2):
        outcomes = [await agent.run(p) for p in ("a", "b", "c")]
    for index, outcome in enumerate(outcomes, start=1):
        say.field(f"call {index}", outcome)


async def act_5_what_it_refuses_to_fake(donkey: Donkey) -> None:
    say.step(5, "It will not invent a refusal it has never seen")
    say.code(
        """
        with donkey.simulate(ContentSafetyBlocked):
            ...
        """
    )
    try:
        with donkey.simulate(ContentSafetyBlocked):
            pass
        say.fail("expected a ValueError")
    except ValueError as exc:
        say.ok("ValueError, not a hand-rolled stand-in")
        say.field("message", exc)
    print()
    say.note(
        "The content-moderation shape has not been captured from a live gateway "
        "yet. Injecting a plausible-looking body would let you write a handler "
        "against a body that does not exist — so it refuses instead."
    )


async def act_6_through_a_framework(donkey: Donkey) -> None:
    """The injection sits on the transport, so it applies to whatever is using it."""
    import importlib.util

    if importlib.util.find_spec("langchain_openai") is None:
        return

    say.step(6, "It works through a framework too, because it is on the transport")
    say.code(
        """
        model = donkey.langgraph.chat_model("gpt-4o")   # a real ChatOpenAI
        with donkey.simulate(PIIDetected):
            await model.ainvoke("...")
        """
    )
    model = donkey.langgraph.chat_model("gpt-4o")
    try:
        with donkey.simulate(PIIDetected):
            await model.ainvoke("my email is a@b.com")
        say.warn("expected a refusal")
    except Exception as exc:  # noqa: BLE001 — LangChain wraps the openai error
        response = getattr(exc, "response", None)
        name = type(classify(response)).__name__ if response is not None else type(exc).__name__
        say.field("LangChain raised", type(exc).__name__)
        say.field("classifies as", name)
        say.ok("Same fixture, same taxonomy, through the framework's own object.")


async def _main() -> None:
    async with Donkey.from_env() as donkey:
        agent = TinyAgent(donkey)
        await act_1_the_problem(agent)
        say.pause()
        await act_2_inject(donkey, agent)
        say.pause()
        await act_3_each_refusal(donkey, agent)
        await act_4_times_and_scope(donkey, agent)
        say.pause()
        await act_5_what_it_refuses_to_fake(donkey)
        await act_6_through_a_framework(donkey)

        print()
        say.section("The point")
        say.note(
            "This needs no gateway, so it belongs in your unit tests. Demo 05 is "
            "the same idea turned into a suite someone else can run against your "
            "agent without reading your code."
        )


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 04 — simulating refusals in-process",
        subtitle="Run the except branch that has never executed. No network, no server, no credentials.",
        target="mock",
        extras=("openai",),
    )
