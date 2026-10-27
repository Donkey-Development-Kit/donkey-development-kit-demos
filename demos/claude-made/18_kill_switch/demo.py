"""A platform kill wakes a budget waiter and ends a paced batch without recovery."""

from __future__ import annotations

import asyncio

import httpx
from donkey_kit import (
    AgentKilled,
    BudgetReserveReached,
    Donkey,
    DonkeyConfig,
    PolicyViolation,
)

from _harness import narrate as say
from _harness import preflight


async def story() -> None:
    config = DonkeyConfig(
        llm_proxy_url="https://demo.example.invalid/",
        llm_proxy_client_id="demo-client-id-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
        max_retries=0,
        telemetry=False,
    )
    async with Donkey(config) as donkey:
        say.step(1, "A spent window parks the next batch")
        donkey.budget.observe(
            httpx.Response(
                429,
                headers={
                    "x-token-limit": "100",
                    "x-token-remaining": "0",
                    "x-token-reset": "3600000",
                },
            )
        )
        entered_wait = asyncio.Event()
        completed: list[str] = []

        async def batch() -> None:
            try:
                async with donkey.budget.pace():
                    completed.append("must not run")
            except BudgetReserveReached as exc:
                assert exc.reset_at is not None
                entered_wait.set()
                await donkey.budget.wait_for_reset(window=exc.window)
                raise AssertionError(
                    "the hour-long reset must not complete normally"
                ) from None

        waiter = asyncio.create_task(batch())
        try:
            await asyncio.wait_for(entered_wait.wait(), timeout=1)
            # Event.set() does not yield. The batch reaches wait_for_reset's first
            # suspension before this task resumes, without reading SDK internals.
            assert not waiter.done()
            assert completed == []
            say.ok("Batch reached wait_for_reset with a one-hour synthetic window")

            say.step(2, "Inject the platform's terminal refusal on the same Donkey")
            handled: list[PolicyViolation] = []
            donkey.on(PolicyViolation).call(lambda ctx: handled.append(ctx.violation))
            try:
                donkey.on(AgentKilled)
            except TypeError as exc:
                assert "terminal" in str(exc)
            else:
                raise AssertionError("AgentKilled cannot have a recovery handler")
            try:
                with donkey.simulate(AgentKilled), donkey.run(id="killed-batch"):
                    await donkey.openai().responses.create(model="gpt-4o", input="hello")
            except AgentKilled as exc:
                assert exc.correlation_id == "killed-batch"
                assert exc.call_id
            else:
                raise AssertionError("the injected kill must propagate")
            assert handled == []
            try:
                await asyncio.wait_for(waiter, timeout=1)
            except AgentKilled:
                pass
            else:
                raise AssertionError("the sleeping batch must wake with AgentKilled")
            assert completed == []
            say.ok("Sleeping batch woke with AgentKilled; generic handler never ran")

            say.step(3, "The kill stays latched after simulate() exits")
            for operation in ("pace", "wait_for_reset"):
                try:
                    if operation == "pace":
                        async with donkey.budget.pace():
                            completed.append("must not run")
                    else:
                        await asyncio.wait_for(donkey.budget.wait_for_reset(), timeout=1)
                except AgentKilled:
                    say.ok(f"Subsequent {operation}() raised AgentKilled")
                else:
                    raise AssertionError(f"{operation} must preserve the kill latch")
            assert completed == []
        finally:
            if not waiter.done():
                waiter.cancel()
            await asyncio.gather(waiter, return_exceptions=True)
        say.note(
            "This consumes the platform kill decision; it does not administer a kill switch. "
            "The budget latch stops paced work, not every arbitrary HTTP request. "
            "The refusal fixture stays in-process; no live gateway was contacted."
        )


def main() -> None:
    asyncio.run(asyncio.wait_for(story(), timeout=5))


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 18 - terminal kill handling",
        subtitle="A waiting batch wakes immediately instead of sleeping until its budget resets.",
        target="offline",
        extras=("openai",),
    )
