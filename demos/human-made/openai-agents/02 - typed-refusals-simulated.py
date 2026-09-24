import asyncio

import openai
from agents import Agent, OpenAIResponsesModel, Runner, set_tracing_disabled
from donkey_kit import (
    ContentSafetyBlocked,
    Donkey,
    PIIDetected,
    PromptInjectionBlocked,
    TokenBudgetExceeded,
)
from donkey_kit.core.errors import classify

# Needs donkey-kit[openai-agents] and DONKEY_LLM_PROXY_* (no network — simulate()
# replays the captured fixture in-process). Runner re-raises the openai error as is.
#
# python "demos/human-made/openai-agents/02 - typed-refusals-simulated.py"

set_tracing_disabled(True)
REFUSALS = (PIIDetected, PromptInjectionBlocked, ContentSafetyBlocked, TokenBudgetExceeded)


async def main() -> None:
    async with Donkey.from_env() as donkey:
        agent = Agent(
            name="greeter",
            instructions="Answer in one short sentence.",
            model=OpenAIResponsesModel(model="gpt-4o", **donkey.openai_agents.connection_kwargs()),
        )
        for refusal in REFUSALS:
            async with donkey.run(id=f"agents-simulated-{refusal.__name__}"):
                with donkey.simulate(refusal):
                    try:
                        await Runner.run(agent, "hello")
                        print(refusal.__name__, "no refusal raised")
                    except openai.APIStatusError as err:
                        error = classify(err.response)
                        print(type(error).__name__, error.policy, error.correlation_id)


asyncio.run(main())
