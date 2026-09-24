import asyncio

from donkey_kit import Donkey, DonkeyConfig, PolicyViolation
from donkey_kit.conformance.gateway import start_gateway
from langchain.agents import create_agent

# No live gateway. Needs donkey-kit[langgraph,local]. Every 2nd call is the captured PII 403.
#
# python "demos/human-made/langgraph/09 - start-gateway.py"

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
        agent = create_agent(donkey.langgraph("gpt-4o"), tools=[], system_prompt="Reply in one sentence.")
        for ticket in TICKETS:
            try:
                with donkey.langgraph.typed_refusals():
                    out = await agent.ainvoke({"messages": [{"role": "user", "content": ticket}]})
                print("ok     ", out["messages"][-1].text[:60])
            except PolicyViolation as error:
                print("refused", type(error).__name__, error.entities)


asyncio.run(main())
print("requests", gw.requests_received)
gw.close()
