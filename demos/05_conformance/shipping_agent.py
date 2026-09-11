"""Two agents for the conformance suite to grade: one written the way people
actually write them, and one that has been through the findings.

The conformance harness never reads this file. It calls a factory, gets an
object, and drives `agent.run(<probe input>)` while watching the transport and
the logs — so what it grades is behaviour, not structure. That is the whole
point: it can grade an agent written in any framework, including one it has
never heard of.
"""

from __future__ import annotations

import logging

import openai
from donkey_kit import Donkey
from donkey_kit.core.errors import classify
from donkey_kit.core.telemetry import current_correlation_id

log = logging.getLogger("shipping.agent")

PROMPT = "Summarise the order status."


class NaiveAgent:
    """Three habits that each look reasonable in isolation.

    Retrying on failure is a good default — except a budget refusal is terminal,
    so the retry just burns the same exhausted window. Catching broadly and
    raising something friendly keeps stack traces out of the caller's face —
    except it destroys the typed refusal the caller needed to branch on. And
    logging the prompt but not the correlation id is fine until someone asks the
    platform team what happened to one specific run.
    """

    def __init__(self, donkey: Donkey) -> None:
        self._client = donkey.openai()

    async def run(self, user_input: str) -> str:
        log.info("handling request: %s", user_input[:40])
        for attempt in range(3):
            try:
                response = await self._client.responses.create(
                    model="gpt-4o", input=user_input
                )
                return getattr(response, "output_text", "")
            except openai.APIStatusError as exc:
                if attempt == 2:
                    raise RuntimeError(f"model call failed: {exc.status_code}") from exc
        return ""


class GovernedAgent:
    """The same agent after the findings.

    A refusal is classified and allowed to escape as its own type; a budget
    refusal is never retried; the correlation id goes into the logs so a run can
    be traced from here to the gateway's own observability view.
    """

    def __init__(self, donkey: Donkey) -> None:
        self._donkey = donkey
        self._client = donkey.openai()

    async def run(self, user_input: str) -> str:
        log.info(
            "handling request",
            extra={"correlation_id": current_correlation_id(), "input": user_input[:40]},
        )
        try:
            response = await self._client.responses.create(model="gpt-4o", input=user_input)
        except openai.APIStatusError as exc:
            error = classify(exc.response)
            log.warning(
                "governed refusal",
                extra={
                    "correlation_id": current_correlation_id(),
                    "refusal": type(error).__name__,
                },
            )
            raise error from exc
        return getattr(response, "output_text", "")


def build_naive(donkey: Donkey) -> NaiveAgent:
    return NaiveAgent(donkey)


def build_governed(donkey: Donkey) -> GovernedAgent:
    return GovernedAgent(donkey)


# Note there is deliberately no KNOWN_LIMITATIONS here. The plugin auto-discovers
# one next to the factory if it exists, and an exemption declared before the
# findings are in would quietly hide a scenario these agents should be graded on.
# See exemptions.py for the asserted-exemption half of the demo.
