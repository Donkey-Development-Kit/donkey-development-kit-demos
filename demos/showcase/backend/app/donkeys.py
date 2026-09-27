"""Donkey instance factory + shared helpers.

One ``Donkey`` per process is plenty for the demo (the budget object is
per-instance, and we *want* the budget window to be shared across the demo's
calls so the pacing card is meaningful). Callers bind per-run cost tags with
``donkey.run(...)``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from donkey_kit import Donkey

DEFAULT_MODEL = "gpt-5.1"


@lru_cache(maxsize=1)
def get_donkey() -> Donkey:
    """The shared, process-wide Donkey, configured from the env vars
    ``simulator.start()`` set. Cached so budget state accumulates across calls."""
    return Donkey.from_env(team="support", project="triage-v2", env="demo")


def message_text(message: Any) -> str:
    """Flatten a LangChain message's ``.content`` to plain text.

    With the Responses API, ``content`` is a list of typed blocks
    (``[{"type": "text", "text": ...}]``); with Chat Completions it's a string.
    """
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text") or block.get("content") or "")
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def budget_snapshot(donkey: Donkey) -> dict[str, Any]:
    b = donkey.budget
    return {
        "limit": b.limit,
        "remaining": b.remaining,
        "fraction_used": round(b.fraction_used, 4) if b.fraction_used is not None else None,
        "reset_at": b.reset_at.isoformat() if b.reset_at else None,
        "observed_at": b.observed_at.isoformat() if b.observed_at else None,
    }


def last_call_snapshot(donkey: Donkey) -> dict[str, Any]:
    """Must be read *inside* the ``donkey.run(...)`` block — last_call is
    contextvar-scoped, so it reverts to UNOBSERVED once the block exits."""
    lc = donkey.last_call
    return {
        "state": getattr(lc, "state", str(lc)),
        "served_model": getattr(lc, "served_model", None),
        "served_provider": getattr(lc, "served_provider", None),
        "routing_type": getattr(lc, "routing_type", None),
        "fallback": getattr(lc, "fallback", None),
        "substituted": getattr(lc, "substituted", None),
        "request_id": getattr(lc, "request_id", None),
        "input_tokens": getattr(lc, "input_tokens", None),
        "output_tokens": getattr(lc, "output_tokens", None),
        "total_tokens": getattr(lc, "total_tokens", None),
    }
