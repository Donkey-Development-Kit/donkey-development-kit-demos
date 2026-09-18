"""Type this on camera. Every `.` opens a real completion list:

    donkey.        -> openai, llm, budget, simulate, run_context, langgraph, …
    donkey.llm.    -> client(), resolve(), list_models()
    client.        -> the whole AsyncOpenAI surface

Drop the `_harness` line if you have already exported the three
DONKEY_LLM_PROXY_* variables in your shell — it only loads .env.local.
"""

import asyncio

from donkey_kit import Donkey

import _harness  # noqa: F401  — loads .env.local


async def main() -> None:
    async with Donkey.from_env() as donkey:
        client = donkey.openai()
        reply = await client.responses.create(model="gpt-4o", input="Say hi in three words.")
        print(reply.output_text)
        print(donkey.budget.remaining, "tokens left in the window")


asyncio.run(main())
