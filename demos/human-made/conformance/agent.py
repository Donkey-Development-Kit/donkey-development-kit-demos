"""Small customer-style agent for the public conformance plugin."""

import logging

import openai
from donkey_kit import Donkey, classify
from donkey_kit.core.telemetry import current_correlation_id

log = logging.getLogger(__name__)


class Agent:
    """Surface typed refusals and log the run correlation, without retrying them."""

    def __init__(self, donkey: Donkey) -> None:
        self.client = donkey.openai()

    async def run(self, prompt: str) -> str:
        """Make one governed model call using the harness-provided Donkey."""
        log.info("agent run", extra={"correlation_id": current_correlation_id()})
        try:
            result = await self.client.responses.create(model="gpt-4o", input=prompt)
        except openai.APIStatusError as exc:
            raise classify(exc.response) from exc
        return result.output_text


def build(donkey: Donkey) -> Agent:
    """Dependency injection keeps the same agent usable in either test mode."""
    return Agent(donkey)
