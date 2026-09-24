import os

os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")   # otherwise CrewAI prompts to view traces

from crewai import Agent  # noqa: E402
from donkey_kit import Donkey  # noqa: E402

# Needs donkey-kit[crewai] and DONKEY_LLM_PROXY_*. Calls /chat/completions,
# which is not live-verified on DDK proxies (/responses is).
# CrewAI owns the transport: headers go on the wire, but no run id and no last_call.
#
# python "demos/human-made/crewai/01 - basic-gw.py"

donkey = Donkey.from_env()
llm = donkey.crewai.llm("gpt-4o")

print(llm.call("Say hello in exactly three words."))

agent = Agent(role="Greeter", goal="Greet people", backstory="Friendly and brief.", llm=llm)
out = agent.kickoff("Say goodbye in exactly three words.")

print(out.raw)
print("usage    ", out.usage_metrics)
print("last_call", donkey.last_call.status.value, donkey.last_call.surface)

donkey.close()
