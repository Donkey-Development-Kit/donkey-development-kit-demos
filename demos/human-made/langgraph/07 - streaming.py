import asyncio

from donkey_kit import Donkey

# Needs donkey-kit[langgraph] and DONKEY_LLM_PROXY_*.
# Live only — mock streaming is truncated SSE and ChatOpenAI rejects it.
#
# python "demos/human-made/langgraph/07 - streaming.py"


async def main() -> None:
    async with Donkey.from_env() as donkey:
        model = donkey.langgraph("gpt-4o")

        final = None
        async for chunk in model.astream("Say hello in exactly three words."):
            final = chunk if final is None else final + chunk

        print(final.text)
        print("usage", final.usage_metadata)   # lands on the terminal event


asyncio.run(main())
