import asyncio

import openai
from donkey_kit import (
    ContentSafetyBlocked,
    Donkey,
    GatewayUnavailable,
    PIIDetected,
    PolicyViolation,
    PromptInjectionBlocked,
    TokenBudgetExceeded,
)
from donkey_kit.core.errors import classify

REFUSALS = (
    PIIDetected,
    PromptInjectionBlocked,
    ContentSafetyBlocked,
    TokenBudgetExceeded,
    PolicyViolation,
)


def report(error: PolicyViolation) -> None:
    print(f"{type(error).__name__}  (policy: {error.policy})")
    print(f"  {error}")
    print(f"  remediation    {error.remediation}")
    print(f"  correlation_id {error.correlation_id}")
    print(f"  call_id        {error.call_id}")
    print(f"  request_id     {error.request_id}")
    if isinstance(error, PIIDetected) and error.entities:
        print(f"  entities       {', '.join(error.entities)}")
    if isinstance(error, ContentSafetyBlocked) and error.categories:
        print(f"  categories     {', '.join(error.categories)}")
    if isinstance(error, TokenBudgetExceeded):
        print(f"  retry_after    {error.retry_after}")
    print()


async def main() -> None:
    async with Donkey.from_env() as donkey:
        client = donkey.openai()

        for refusal in REFUSALS:
            async with donkey.run(id=f"typed-refusals-{refusal.__name__}"):
                # simulate() replays the captured gateway fixture in-process, so
                # the refusal branch runs with no network and nothing to provoke.
                with donkey.simulate(refusal):
                    try:
                        await client.responses.create(
                            model="gpt-4o",
                            input="Say hello in exactly three words.",
                        )
                    except openai.APIStatusError as err:
                        report(classify(err.response))
                    else:
                        print(f"{refusal.__name__}: no refusal raised\n")

        # No captured body to replay — simulate() refuses rather than invent one.
        try:
            with donkey.simulate(GatewayUnavailable):
                pass
        except ValueError as err:
            print("simulate(GatewayUnavailable)")
            print(f"  {err}")


asyncio.run(main())
