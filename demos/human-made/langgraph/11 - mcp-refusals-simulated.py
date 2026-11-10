# Typed MCP tool refusals, offline: donkey.simulate_mcp() replays a captured
# Omni Gateway refusal into a LangGraph tool from donkey.tools.discover().
# Needs: pip install "donkey-kit[langgraph,mcp]" langchain-mcp-adapters  (SDK >= 0.2.1)
# No gateway, no Exchange, no credentials.
import asyncio

from donkey_kit import Donkey, DonkeyConfig, PIIDetected, ToolNotInProfile

config = DonkeyConfig(
    llm_proxy_url="https://demo-gateway.example.invalid/mcp-demo/",
    llm_proxy_client_id="not-a-real-id",
    llm_proxy_client_secret="not-a-real-secret",
)
servers = {"acme/crm-tools/1.0.0": [{"name": "lookup_customer"}]}


async def main():
    async with Donkey(config) as donkey:
        with donkey.simulate_mcp("pii-request", servers=servers):
            (lookup,) = await (await donkey.tools.discover()).langgraph()
            try:
                await lookup.ainvoke({})
            except PIIDetected as exc:
                print("blocked:", type(exc).__name__, exc.phase, "-", exc)
            print("next call:", await lookup.ainvoke({}))

        with donkey.simulate_mcp("abac-denied", servers=servers):
            (lookup,) = await (await donkey.tools.discover()).langgraph()
            try:
                await lookup.ainvoke({})
            except ToolNotInProfile as exc:
                print("denied:", type(exc).__name__, exc.tool_name)


asyncio.run(main())
