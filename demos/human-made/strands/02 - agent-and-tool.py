import asyncio

from donkey_kit import Donkey
from donkey_kit.core.telemetry import current_correlation_id
from strands import Agent, tool
from strands.models.openai import OpenAIModel

# Needs strands-agents[openai] and DONKEY_LLM_PROXY_*. Live — the tool loop is two model calls.
# client=donkey.openai() keeps the transport open across both (see 01).
#
# python "demos/human-made/strands/02 - agent-and-tool.py"


@tool
def lookup_sku(sku: str) -> str:
    """Return stock for a product SKU."""
    print("tool sees run id", current_correlation_id())
    return "42"


async def main() -> None:
    async with Donkey.from_env() as donkey:
        agent = Agent(
            model=OpenAIModel(client=donkey.openai(), model_id="gpt-4o"),
            tools=[lookup_sku],
            callback_handler=None,
            system_prompt="Answer in one short sentence. Use the tool for stock.",
        )
        async with donkey.run(id="strands-ticket-4417", team="support", project="triage"):
            result = await agent.invoke_async("How many AF-1001 are in stock?")
            last = donkey.last_call

        print(str(result).strip())
        print("model calls ", result.metrics.cycle_count)
        print("last_call   ", last.status.value, last.served_model)


asyncio.run(main())
