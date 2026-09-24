import asyncio

from donkey_kit import Donkey
from donkey_kit.core.telemetry import current_correlation_id
from langchain.agents import create_agent
from langchain_core.tools import tool

# Needs donkey-kit[langgraph] and DONKEY_LLM_PROXY_*. Live — the simulator never calls tools.
# LangGraph copies the context into every node, so the run id reaches the tool untouched.
#
# python "demos/human-made/langgraph/05 - agent-and-tool.py"


@tool
def lookup_sku(sku: str) -> str:
    """Return stock for a product SKU."""
    print("tool sees run id", current_correlation_id())
    return "42"


async def main() -> None:
    async with Donkey.from_env() as donkey:
        agent = create_agent(
            donkey.langgraph("gpt-4o"),
            tools=[lookup_sku],
            system_prompt="Answer in one short sentence. Use the tool for stock.",
        )
        async with donkey.run(id="lg-ticket-4417", team="support", project="triage"):
            print("run id          ", current_correlation_id())
            out = await agent.ainvoke({"messages": [{"role": "user", "content": "How many AF-1001 are in stock?"}]})

        print(out["messages"][-1].text)
        print("messages        ", len(out["messages"]))


asyncio.run(main())
