"""Which Donkey a chat/compare call runs on, plus the refusal extras the UI shows.

Most cards share the process-wide Donkey (``donkeys.get_donkey``) so the budget
window accumulates across calls. Two kinds of call get a throwaway Donkey
instead, closed when the call ends:

* The ``donkey-sim/agent-killed`` and ``donkey-sim/request-rate-limit``
  sentinels. The simulator replays the captured fixture verbatim, so the
  request window (3 per window, about 48s to reset) and the ``AgentKilled``
  latch are the capture's, not this demo's. Fed into the shared Budget they
  would stop the pacing card for the next minute, or for good after a kill.
  That matches the SDK's own rule: only a Donkey built after the agent is
  restored starts fresh. The other sentinels leave nothing behind, so they keep
  the shared Donkey as before.
* The refusal-reactions card, which registers a ``donkey.on(...)`` reaction.
  Reactions are per Donkey, so registering one on the shared Donkey would
  change how the prompt-injection card behaves.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import AsyncIterator
from typing import Any

from donkey_kit import (
    AgentKilled,
    Donkey,
    DonkeyError,
    GatewayApprovalPending,
    PromptInjectionBlocked,
    RefusalContext,
    RequestRateLimitExceeded,
)

from .donkeys import get_donkey

SIM_PREFIX = "donkey-sim/"
ISOLATED_SHAPES = frozenset({"agent-killed", "request-rate-limit"})
REACTION_FEATURE = "refusal-reactions"
REACTION_MAX_TIMES = 1

# Matches the simulator's `injection:on-pattern=ignore previous` scenario
# (simulator.SCENARIOS) and the sentence that carries it.
_INJECTION = re.compile(r"(?i)\bignore previous\b[^.?!]*[.?!]?\s*")


def _new_donkey() -> Donkey:
    return Donkey.from_env(team="support", project="triage-v2", env="demo")


class Reaction:
    """The bounded ``donkey.on(PromptInjectionBlocked).call(...)`` reaction and
    what it did, for the chat's reaction trail."""

    def __init__(self) -> None:
        self.steps: list[dict[str, Any]] = []

    def strip_injection(self, ctx: RefusalContext) -> None:
        """Drop the injected sentence and re-send. The re-send is a NEW governed
        request that the gateway judges from scratch; returning without
        ``resend`` lets the refusal propagate."""
        body = ctx.body
        if body is None:
            return
        removed: list[str] = []
        sanitised = _strip(body, removed)
        self.steps.append(
            {
                "refusal": type(ctx.violation).__name__,
                "policy": getattr(ctx.violation, "policy", None),
                "removed": removed,
                "resent_prompt": sanitised,
            }
        )
        if removed:
            ctx.resend(json=body)

    def event(self, outcome: str) -> dict[str, Any] | None:
        if not self.steps:
            return None
        first = self.steps[0]
        return {
            "on": "PromptInjectionBlocked",
            "reaction": f"call(strip_injection, max_times={REACTION_MAX_TIMES})",
            "refusal": first["refusal"],
            "policy": first["policy"],
            "removed": first["removed"],
            "resent_prompt": first["resent_prompt"],
            "resends": sum(1 for s in self.steps if s["removed"]),
            "max_times": REACTION_MAX_TIMES,
            "outcome": outcome,
        }


def _strip(body: dict[str, Any], removed: list[str]) -> str | None:
    """Remove the injected sentence from the last user message, in place."""

    def clean(text: str) -> str:
        removed.extend(m.group(0).strip() for m in _INJECTION.finditer(text))
        return _INJECTION.sub("", text).strip()

    messages = body.get("messages")
    if isinstance(messages, list) and messages:
        last = messages[-1]
        if isinstance(last, dict) and isinstance(last.get("content"), str):
            last["content"] = clean(last["content"])
            return last["content"]
    if isinstance(body.get("input"), str):
        body["input"] = clean(body["input"])
        return body["input"]
    return None


@contextlib.asynccontextmanager
async def governed_donkey(
    model_id: str, feature: str | None
) -> AsyncIterator[tuple[Donkey, Reaction | None, bool]]:
    """Yield ``(donkey, reaction, scratch)`` for one chat or compare call."""
    if feature == REACTION_FEATURE:
        donkey = _new_donkey()
        reaction = Reaction()
        donkey.on(PromptInjectionBlocked).call(
            reaction.strip_injection, max_times=REACTION_MAX_TIMES
        )
        try:
            yield donkey, reaction, True
        finally:
            await donkey.aclose()
    elif model_id.startswith(SIM_PREFIX) and model_id[len(SIM_PREFIX) :] in ISOLATED_SHAPES:
        donkey = _new_donkey()
        try:
            yield donkey, None, True
        finally:
            await donkey.aclose()
    else:
        yield get_donkey(), None, False


async def refusal_extras(exc: DonkeyError, donkey: Donkey) -> dict[str, Any]:
    """What the SDK did with the refusal beyond the exception itself."""
    extras: dict[str, Any] = {}
    if isinstance(exc, AgentKilled):
        # The kill latches the Budget: pace() and wait_for_reset() now raise it.
        try:
            async with donkey.budget.pace():
                extras["latched"] = False
        except AgentKilled:
            extras["latched"] = True
    if isinstance(exc, RequestRateLimitExceeded):
        r = donkey.budget.requests
        extras["requests_window"] = {
            "limit": r.limit,
            "remaining": r.remaining,
            "fraction_used": r.fraction_used,
        }
    return extras


def disposition(exc: DonkeyError) -> str:
    from donkey_kit import UpstreamModelError

    if isinstance(exc, UpstreamModelError):
        return "retryable"
    if isinstance(exc, GatewayApprovalPending):
        return "pending"
    return "terminal"
