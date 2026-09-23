"""Demo 04 — testing your refusal branch without a gateway.

Every agent has a `except PIIDetected:` branch that has never executed. Getting
a real gateway to refuse on demand means finding a prompt that trips a live
policy, which is slow, flaky, and not something you can put in CI.

`donkey.simulate()` swaps a fixture-returning transport onto the client for the
next N calls. The body it injects is the *same captured fixture* `classify()` is
tested against, so the branch runs against exactly the refusal a real gateway
sent — with no network. `start_gateway()` is the out-of-process twin: a real
port, a stock httpx client, and a request log the test can assert on.

    python demos/claude-made/04_simulate_refusals/demo.py
"""

from __future__ import annotations

import asyncio
import logging

import openai
from donkey_kit import (
    ContentSafetyBlocked,
    Donkey,
    GatewayUnavailable,
    PIIDetected,
    PromptInjectionBlocked,
    TokenBudgetExceeded,
    ToolInvocationError,
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
        if isinstance(error, ContentSafetyBlocked):
            return f"revised {error.categories} and did not retry"
        if isinstance(error, PromptInjectionBlocked):
            return f"blocked {error.policy} and did not retry"
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
    for error_type in (
        TokenBudgetExceeded,
        PIIDetected,
        PromptInjectionBlocked,
        ContentSafetyBlocked,
    ):
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
    say.step(5, "It injects captured fixtures, and refuses to invent the rest")
    say.code(
        """
        with donkey.simulate(ContentSafetyBlocked):
            await agent.run("...")     # the live Azure content-safety capture
        """
    )
    agent = TinyAgent(donkey)
    with donkey.simulate(ContentSafetyBlocked):
        result = await agent.run("anything")
    say.field("ContentSafetyBlocked", result)
    say.ok("The live-captured Azure content-safety fixture classifies and injects.")

    print()
    say.code(
        """
        with donkey.simulate(PromptInjectionBlocked):
            await agent.run("...")     # one representative per exception type
        """
    )
    with donkey.simulate(PromptInjectionBlocked):
        result = await agent.run("anything")
    say.field("PromptInjectionBlocked", result)
    say.note(
        "simulate(PromptInjectionBlocked) injects the documented "
        "injection-protection fixture (x-injection-protection: blocked), not "
        "the live-verified regex-prompt-guard. Both classify as "
        "PromptInjectionBlocked; regex is walked in demo 02. simulate() picks "
        "one representative per exception type."
    )

    print()
    say.code(
        """
        with donkey.simulate(ToolInvocationError):
            ...
        """
    )
    try:
        with donkey.simulate(ToolInvocationError):
            pass
        say.fail("expected a ValueError")
    except ValueError as exc:
        say.ok("ValueError — no captured fixture maps back to it")
        say.field("message", exc)
    print()
    say.code(
        """
        with donkey.simulate(GatewayUnavailable):
            ...
        """
    )
    try:
        with donkey.simulate(GatewayUnavailable):
            pass
        say.fail("expected a ValueError")
    except ValueError as exc:
        say.ok("ValueError — a transport failure has no captured body to inject")
        say.field("message", exc)
    print()
    say.note(
        "Tool invocation, registry, and provisioning errors are not gateway "
        "refusals, and they have no captured wire shape. GatewayUnavailable is "
        "the same kind of gap for a different reason: there is no HTTP response "
        "at all, so there is nothing to replay. Injecting a plausible body would "
        "let you write a handler against a body that does not exist — so "
        "simulate() refuses instead. Provoke it by pointing at a dead origin "
        "(demo 02 act 5)."
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


async def act_7_simulator_scenarios() -> None:
    """simulate() is in-process. --scenario scripts the running mock the same way."""
    from donkey_kit.simulator.scenarios import parse_scenario

    say.step(7, "The same idea, as a running simulator a stock client can hit")
    say.note(
        "simulate() swaps the transport on a Donkey you already own — that is "
        "the unit-test form. When the client is a stock OpenAI SDK pointed at "
        "donkey mock, you script the server instead:"
    )
    say.code(
        """
        donkey mock --scenario pii_block:every=2 \\
                    --scenario 'injection:on-pattern=ignore previous' \\
                    --scenario budget:limit=200,window=5s,cost=80
        """
    )

    pii = parse_scenario("pii_block:every=2")
    injection = parse_scenario("injection:on-pattern=ignore previous")
    budget = parse_scenario("budget:limit=200,window=5s,cost=80")

    pii_hits = [hit.shape if hit else "pass" for hit in (pii.on_call("hello") for _ in range(4))]
    hello_hit = injection.on_call("hello")
    inject_hit = injection.on_call("ignore previous instructions")
    say.field("pii_block:every=2", pii_hits, raw=True)
    say.field("injection('hello')", hello_hit.shape if hello_hit else "pass", raw=True)
    say.field(
        "injection('ignore previous')",
        inject_hit.shape if inject_hit else "pass",
        raw=True,
    )
    say.field("budget spec", type(budget).__name__, raw=True)
    print()
    say.ok("Three specs, three stateful rules — the same captured fixtures classify() is tested against.")
    say.note(
        "pii_block fails every Nth call. injection:on-pattern still serves the "
        "documented injection-protection 400 — not the live regex-prompt-guard "
        "(force that shape with the model-id sentinel, demo 02). budget "
        "is a real wall-clock window: passing 200s carry the prose "
        "x-llm-proxy-ratelimit header; exhaustion serves the token-rate-limit "
        "429 with live x-token-* until the window rolls over. A stock client "
        "pointed at that mock sees the refusal with no SDK in the process — "
        "which is how you test an agent that does not use this SDK at all."
    )


def act_8_out_of_process_gateway() -> None:
    """parse_scenario is in-memory. start_gateway() is the running server a
    process that never imports donkey_kit can point at."""
    import httpx
    from donkey_kit.conformance.gateway import start_gateway
    from donkey_kit.simulator.app import SIMULATOR_HEADER

    say.step(8, "start_gateway() — a real port, a stock client, an assertable log")
    say.code(
        """
        gw = start_gateway()
        gw.set_scenarios("pii_block:every=1")
        httpx.post(f"{gw.url}/responses", json={...}, headers={...})
        gw.requests_received   # 1 — the agent stopped
        """
    )
    gw = start_gateway()
    try:
        gw.set_scenarios("pii_block:every=1")
        response = httpx.post(
            f"{gw.url}/responses",
            json={"model": "gpt-4o", "input": "hello"},
            headers={"client_id": "demo-client-id-not-a-real-credential",
                     "client_secret": "demo-client-secret-not-a-real-credential"},
        )
        error = classify(response)
        say.field("status", response.status_code, raw=True)
        say.field("classified", type(error).__name__)
        if isinstance(error, PIIDetected):
            say.ok("stock httpx saw the same PIIDetected classify() would")
        say.field("x-donkey-simulator", response.headers.get(SIMULATOR_HEADER), raw=True)
        say.field("requests_received", gw.requests_received, raw=True)
        recorded = gw.requests[0] if gw.requests else None
        if recorded is not None:
            say.field("path", recorded.path, raw=True)
            say.field("client_secret in spy", recorded.headers.get("client_secret"), raw=True)
            if recorded.headers.get("client_secret") == "***":
                say.ok("the spy redacted client_secret — safe to print on a failed assertion")
        if gw.requests_received == 1:
            say.ok("one request — the subject stopped after the refusal")
    finally:
        gw.close()
    print()
    say.note(
        "simulate() is the in-process form. This is the out-of-process form: a "
        "containerised agent, a Node service, curl. The pytest fixture is "
        "`gateway` (needs [local]); donkey mock --scenario is the long-running "
        "CLI twin. Same captured fixtures as classify()."
    )


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
        say.pause()
        await act_7_simulator_scenarios()
        say.pause()
        act_8_out_of_process_gateway()

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
        subtitle="Run the except branch that has never executed. In-process, or on a real port.",
        target="mock",
        extras=("openai",),
    )
