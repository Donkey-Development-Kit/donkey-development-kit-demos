import asyncio

import openai
from donkey_kit import ContentSafetyBlocked, Donkey, PIIDetected, PromptInjectionBlocked
from donkey_kit.core.errors import classify
from strands import Agent
from strands.models.openai import OpenAIModel

# Needs strands-agents[openai] and DONKEY_LLM_PROXY_* (no network — simulate()
# replays the captured fixture in-process).
# No TokenBudgetExceeded: Strands retries a 429 itself (ModelThrottledException),
# so the one simulated 429 is absorbed and the retry succeeds.
#
# python "demos/human-made/strands/03 - typed-refusals-simulated.py"

REFUSALS = (PIIDetected, PromptInjectionBlocked, ContentSafetyBlocked)


async def main() -> None:
    async with Donkey.from_env() as donkey:
        model = OpenAIModel(client=donkey.openai(), model_id="gpt-4o")
        for refusal in REFUSALS:
            async with donkey.run(id=f"strands-simulated-{refusal.__name__}"):
                with donkey.simulate(refusal):
                    try:
                        await Agent(model=model, callback_handler=None).invoke_async("hello")
                        print(refusal.__name__, "no refusal raised")
                    except openai.APIStatusError as err:
                        error = classify(err.response)
                        print(type(error).__name__, error.policy, error.correlation_id)


asyncio.run(main())
