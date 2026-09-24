import asyncio

from agent_framework import Agent
from agent_framework.exceptions import ChatClientException
from donkey_kit import Donkey, DonkeyConfig
from donkey_kit.conformance.gateway import start_gateway
from donkey_kit.core.errors import classify

# No live gateway. Needs donkey-kit[agent_framework,local]. Every 2nd call is the captured PII 403.
#
# python "demos/human-made/agent-framework/03 - start-gateway.py"

gw = start_gateway()
gw.set_scenarios("pii_block:every=2")
donkey = Donkey(
    DonkeyConfig(
        llm_proxy_url=gw.url,
        llm_proxy_client_id="demo-client-id-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
    )
)

for ticket in ("The app crashes when I tap Export.", "My email is jane@example.com, please update it."):
    agent = Agent(client=donkey.agent_framework.chat_client("gpt-4o"), instructions="Reply in one sentence.")
    try:
        print("ok     ", asyncio.run(agent.run(ticket)).text[:60])
    except ChatClientException as err:
        error = classify(err.__cause__.response)
        print("refused", type(error).__name__, error.entities)

print("requests", gw.requests_received)
donkey.close()
gw.close()
