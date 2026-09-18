"""The blocking twin of live_chat.py — same governance, no asyncio.

Worth showing right after the async one: the only difference is `sync=True`.
"""

from donkey_kit import Donkey

import _harness  # noqa: F401  — loads .env.local

with Donkey.from_env() as donkey:
    client = donkey.openai(sync=True)
    print(client.responses.create(model="gpt-4o", input="Say hi in three words.").output_text)
