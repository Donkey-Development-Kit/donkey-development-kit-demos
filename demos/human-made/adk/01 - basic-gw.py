import asyncio

from donkey_kit import Donkey
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner

# Needs donkey-kit[adk] and DONKEY_LLM_PROXY_*. LiteLLM calls the proxy's /chat/completions route.
# LiteLLM sends through the SDK's shared client, so the run id goes on the wire. ADK's Runner
# runs the agent in a task of its own: last_call is observed in after_model_callback only.
#
# python "demos/human-made/adk/01 - basic-gw.py"

seen = []


def after_model(callback_context, llm_response):
    seen.append(donkey.last_call)


donkey = Donkey.from_env()
agent = Agent(
    name="greeter",
    model=donkey.adk.model("gpt-4o"),
    instruction="Answer in one short sentence.",
    after_model_callback=after_model,
)

events = asyncio.run(InMemoryRunner(agent=agent).run_debug("Say hello in exactly three words.", quiet=True))

print(events[-1].content.parts[0].text)
print("total tokens", events[-1].usage_metadata.total_token_count)
print("last_call   ", seen[-1].status.value, seen[-1].served_model, "(in after_model_callback)")
print("after run   ", donkey.last_call.status.value, "(Runner's task)")

donkey.close()
