import asyncio

from agent_framework import Agent
from donkey_kit import Donkey

# Needs donkey-kit[agent_framework] and DONKEY_LLM_PROXY_*.
# OpenAIChatClient (verified against 1.19.0) calls /responses.
# Only default_headers are handed over: no run id and no last_call.
#
# python "demos/human-made/agent-framework/01 - basic-gw.py"

donkey = Donkey.from_env()
agent = Agent(
    client=donkey.agent_framework.chat_client("gpt-4o"),
    name="greeter",
    instructions="Answer in one short sentence.",
)

result = asyncio.run(agent.run("Say hello in exactly three words."))

print(result.text)
print("total tokens", result.usage_details["total_token_count"])
print("last_call   ", donkey.last_call.status.value, donkey.last_call.surface)

donkey.close()
