import asyncio

import openai
from donkey_kit import Donkey
from donkey_kit.core.errors import DonkeyError, classify
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner

# Needs donkey-kit[adk] and DONKEY_LLM_PROXY_* with llm-pii-detection-policy (Email, Reject).
# LiteLLM re-raises the 403 as its own APIError, but the openai error with the full
# response is on its cause chain. ADK's Runner drops that chain, so classify() runs in
# on_model_error_callback, where the model call failed.
#
# python "demos/human-made/adk/02 - refusal-live.py"

PII_PROMPT = "Summarise this contact record in one line: John Doe, john.doe@example.com, +1 415 555 0132."


def typed_refusal(callback_context, llm_request, error):
    current = error
    while current is not None:
        if isinstance(current, openai.APIStatusError):
            raise classify(current.response) from error
        current = current.__cause__ or current.__context__


donkey = Donkey.from_env()
agent = Agent(
    name="support",
    model=donkey.adk.model("gpt-4o"),
    instruction="Answer in one short sentence.",
    on_model_error_callback=typed_refusal,
)

try:
    asyncio.run(InMemoryRunner(agent=agent).run_debug(PII_PROMPT, quiet=True))
    print("NO REFUSAL")
except DonkeyError as err:
    print(type(err).__name__, getattr(err, "entities", None))

donkey.close()
