"""The best scratchpad to type on camera: it needs no gateway and no credentials,
so it cannot fail because a sandbox is down.

Point it at the local simulator first:

    donkey mock &
    export DONKEY_LLM_PROXY_URL=http://127.0.0.1:8080
    export DONKEY_LLM_PROXY_CLIENT_ID=anything
    export DONKEY_LLM_PROXY_CLIENT_SECRET=anything
"""

import asyncio

import openai
from donkey_kit import Donkey, PIIDetected
from donkey_kit.core.errors import classify

import _harness  # noqa: F401  — loads .env.local


async def main() -> None:
    async with Donkey.from_env() as donkey:
        client = donkey.openai()
        with donkey.simulate(PIIDetected):
            try:
                await client.responses.create(model="gpt-4o", input="my email is a@b.com")
            except openai.APIStatusError as exc:
                error = classify(exc.response)
                print(type(error).__name__, error.entities)


asyncio.run(main())
