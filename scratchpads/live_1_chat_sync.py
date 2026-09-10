"""Live-coding scratchpad — the same governed call as live_1_chat.py, blocking.

`sync=True` returns a real `openai.OpenAI` instead of `AsyncOpenAI`, governed on
identical terms. No event loop, no `await`, and nothing to forget awaiting.

Every `.` gives full IntelliSense — the two forms are typed overloads, so the
call site narrows to one concrete class rather than a union:

    donkey.llm.client()            -> openai.AsyncOpenAI
    donkey.llm.client(sync=True)   -> openai.OpenAI
    client.                        -> the whole OpenAI surface

Drop the `_paths` line if you have already exported the three
DONKEY_LLM_PROXY_* variables in your shell.
"""

# ruff: noqa: I001, E402  (the _paths shim must import before donkey_kit — do not reorder)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root (holds _paths.py)
import _paths  # noqa: F401  (loads .env.local into the environment)

from donkey_kit import Donkey

with Donkey.from_env() as donkey:
    client = donkey.llm.client(sync=True)
    reply = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Say hi in three words."}],
    )
    print(reply.choices[0].message.content)
