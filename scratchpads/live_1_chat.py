"""Live-coding scratchpad — a governed chat completion, in as few lines as it goes.

Type this out on camera. Every `.` gives full IntelliSense:

    donkey.        -> llm, langgraph, adk, strands, anthropic, crewai, …
    donkey.llm.    -> client(), resolve(), list_models()
    client.        -> the whole AsyncOpenAI surface (chat, responses, embeddings…)

Drop the `_paths` line if you have already exported the three
DONKEY_LLM_PROXY_* variables in your shell.
"""

# ruff: noqa: I001, E402  (the _paths shim must import before donkey_kit — do not reorder)
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root (holds _paths.py)
import _paths  # noqa: F401  (loads .env.local into the environment)

from donkey_kit import Donkey


async def main() -> None:
    async with Donkey.from_env() as donkey:
        client = donkey.llm.client()
        reply = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Say hi in three words."}],
        )
        print(reply.choices[0].message.content)


asyncio.run(main())
