import asyncio

import litellm
from donkey_kit import Donkey
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner

# Needs donkey-kit[adk] and DONKEY_LLM_PROXY_* with llm-pii-detection-policy (Email, Reject).
# LiteLLM keeps the status and message but drops the response headers, so
# classify() has nothing to read — no typed refusal on this path.
#
# python "demos/human-made/adk/02 - refusal-live.py"

PII_PROMPT = "Summarise this contact record in one line: John Doe, john.doe@example.com, +1 415 555 0132."

donkey = Donkey.from_env()
agent = Agent(name="support", model=donkey.adk.model("gpt-4o"), instruction="Answer in one short sentence.")

try:
    asyncio.run(InMemoryRunner(agent=agent).run_debug(PII_PROMPT, quiet=True))
    print("NO REFUSAL")
except litellm.exceptions.APIError as err:
    print(type(err).__name__, err.status_code)
    print(str(err).splitlines()[0])

donkey.close()
