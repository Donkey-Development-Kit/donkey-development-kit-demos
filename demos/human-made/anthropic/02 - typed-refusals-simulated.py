import asyncio

import anthropic
from donkey_kit import (
    ContentSafetyBlocked,
    Donkey,
    PIIDetected,
    PromptInjectionBlocked,
    TokenBudgetExceeded,
)
from donkey_kit.core.errors import classify

# Needs donkey-kit[anthropic] and DONKEY_LLM_PROXY_* (no network — simulate()
# replays the captured fixture in-process). The Anthropic client shares the
# governed transport, so the same refusals come back typed.
#
# python "demos/human-made/anthropic/02 - typed-refusals-simulated.py"

REFUSALS = (PIIDetected, PromptInjectionBlocked, ContentSafetyBlocked, TokenBudgetExceeded)


async def main() -> None:
    async with Donkey.from_env() as donkey:
        client = donkey.anthropic.client()
        for refusal in REFUSALS:
            async with donkey.run(id=f"anthropic-simulated-{refusal.__name__}"):
                with donkey.simulate(refusal):
                    try:
                        await client.messages.create(
                            model="claude-haiku-4-5-20251001",
                            max_tokens=32,
                            messages=[{"role": "user", "content": "hello"}],
                        )
                        print(refusal.__name__, "no refusal raised")
                    except anthropic.APIStatusError as err:
                        error = classify(err.response)
                        print(type(err).__name__, "->", type(error).__name__, error.policy, error.correlation_id)


asyncio.run(main())
