import asyncio

from donkey_kit import Donkey
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner

# Needs donkey-kit[adk] and DONKEY_LLM_PROXY_*. LiteLLM calls /chat/completions,
# which is not live-verified on DDK proxies (/responses is).
# LiteLLM owns the transport: headers go on the wire, but no run id and no last_call.
#
# python "demos/human-made/adk/01 - basic-gw.py"

donkey = Donkey.from_env()
agent = Agent(name="greeter", model=donkey.adk.model("gpt-4o"), instruction="Answer in one short sentence.")

events = asyncio.run(InMemoryRunner(agent=agent).run_debug("Say hello in exactly three words.", quiet=True))

print(events[-1].content.parts[0].text)
print("total tokens", events[-1].usage_metadata.total_token_count)
print("last_call   ", donkey.last_call.status.value, donkey.last_call.surface)

donkey.close()
