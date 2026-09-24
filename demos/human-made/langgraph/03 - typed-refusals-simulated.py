import asyncio

from donkey_kit import (
    ContentSafetyBlocked,
    Donkey,
    PIIDetected,
    PolicyViolation,
    PromptInjectionBlocked,
    TokenBudgetExceeded,
)
from langchain.agents import create_agent

# Needs donkey-kit[langgraph] and DONKEY_LLM_PROXY_* (no network — simulate()
# replays the captured fixture in-process).
#
# python "demos/human-made/langgraph/03 - typed-refusals-simulated.py"

REFUSALS = (PIIDetected, PromptInjectionBlocked, ContentSafetyBlocked, TokenBudgetExceeded, PolicyViolation)


async def main() -> None:
    async with Donkey.from_env() as donkey:
        agent = create_agent(donkey.langgraph("gpt-4o"), tools=[])

        for refusal in REFUSALS:
            async with donkey.run(id=f"lg-simulated-{refusal.__name__}"):
                with donkey.simulate(refusal):
                    try:
                        # typed_refusals turns the node's openai error back into the SDK type.
                        with donkey.langgraph.typed_refusals():
                            await agent.ainvoke({"messages": [{"role": "user", "content": "hello"}]})
                        print(refusal.__name__, "no refusal raised")
                    except PolicyViolation as error:
                        print(type(error).__name__, error.policy, error.correlation_id)


asyncio.run(main())
