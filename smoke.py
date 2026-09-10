"""Smallest live smoke test — one governed chat completion, blocking.

The bare minimum that proves a checkout can reach the governed proxy:
``Donkey.from_env()`` -> a real ``openai.OpenAI`` -> one ``chat.completions``
call. For the narrated walkthrough see ``deliverables/`` and ``recordings/``.

Run (needs the three DONKEY_LLM_PROXY_* vars, or a .env.local):
    python smoke.py

With no credentials it prints setup guidance and exits cleanly.
"""

# ruff: noqa: I001  (the _paths shim must import before donkey_kit — do not reorder)
import os

import _paths  # noqa: F401  (dev path shim + .env.local loader; sibling of this file)

from donkey_kit import Donkey

_REQUIRED = (
    "DONKEY_LLM_PROXY_URL",
    "DONKEY_LLM_PROXY_CLIENT_ID",
    "DONKEY_LLM_PROXY_CLIENT_SECRET",
)


def main() -> None:
    if not all(os.environ.get(v) for v in _REQUIRED):
        print(__doc__)
        print(">> Set the three DONKEY_LLM_PROXY_* env vars to run this live smoke test.")
        return

    with Donkey.from_env() as donkey:
        client = donkey.llm.client(sync=True)
        response = client.chat.completions.create(
            model=os.environ.get("DEMO_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": "What is the capital of Switzerland?"}],
        )
        print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
