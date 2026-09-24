import asyncio

import openai
from agents import Agent, OpenAIResponsesModel, Runner, set_tracing_disabled
from donkey_kit import Donkey, DonkeyConfig
from donkey_kit.conformance.gateway import start_gateway
from donkey_kit.core.errors import classify

# No live gateway. Needs donkey-kit[openai-agents,local]. Every 2nd call is the captured PII 403.
#
# python "demos/human-made/openai-agents/03 - start-gateway.py"

set_tracing_disabled(True)
gw = start_gateway()
gw.set_scenarios("pii_block:every=2")
cfg = DonkeyConfig(
    llm_proxy_url=gw.url,
    llm_proxy_client_id="demo-client-id-not-a-real-credential",
    llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
)
TICKETS = ("The app crashes when I tap Export.", "My email is jane@example.com, please update it.")


async def main() -> None:
    async with Donkey(cfg) as donkey:
        agent = Agent(
            name="triage",
            instructions="Reply in one sentence.",
            model=OpenAIResponsesModel(model="gpt-4o", **donkey.openai_agents.connection_kwargs()),
        )
        for ticket in TICKETS:
            try:
                result = await Runner.run(agent, ticket)
                print("ok     ", result.final_output[:60])
            except openai.APIStatusError as err:
                error = classify(err.response)
                print("refused", type(error).__name__, error.entities)


asyncio.run(main())
print("requests", gw.requests_received)
gw.close()
