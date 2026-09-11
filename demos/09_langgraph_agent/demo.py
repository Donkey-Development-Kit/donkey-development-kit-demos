"""Demo 09 — a real LangGraph agent, governed, doing real tool calls.

Everything before this demo could be accused of being a client library talking
to itself. This one runs an actual multi-step agent: the model decides to call
two tools, the tools return, the model composes an answer. Every model call in
that loop goes through the governed proxy, and the object driving it is
LangChain's own `ChatOpenAI` — not a wrapper the SDK invented.

This is the deep, conformance-gated adapter. The other seven frameworks are
supported at `connection_kwargs()` (demo 08).

**Live only.** The local simulator serves the Responses API; LangChain's
`ChatOpenAI` talks to `/chat/completions`, which the simulator deliberately does
not implement rather than fabricate. Its refusal path *can* be exercised offline
though — see act 6 of demo 04, which drives this same `ChatOpenAI` through
`donkey.simulate()`.

    python demos/09_langgraph_agent/demo.py        # needs real credentials
"""

from __future__ import annotations

import asyncio
import os

from donkey_kit import Donkey
from langchain.agents import create_agent
from langchain_core.tools import tool

from _harness import narrate as say
from _harness import preflight, redact

MODEL = os.environ.get("DEMO_MODEL", "gpt-4o-mini")
QUESTION = "Can I ship SKU AF-1001 today, and what does it cost?"

INVENTORY = {"AF-1001": "42 units in Amsterdam", "AF-2002": "0 units"}
PRICES = {"AF-1001": "EUR 129.00", "AF-2002": "EUR 89.50"}


@tool
def check_inventory(sku: str) -> str:
    """Return the units in stock and warehouse for a product SKU."""
    return INVENTORY.get(sku, "unknown SKU")


@tool
def get_price(sku: str) -> str:
    """Return the list price for a product SKU."""
    return PRICES.get(sku, "unknown SKU")


async def _main() -> None:
    async with Donkey.from_env() as donkey:
        say.step(1, "One call gets LangChain's own model object")
        say.code(
            """
            model = donkey.langgraph.chat_model("gpt-4o-mini", temperature=0)
            agent = create_agent(model, tools=[check_inventory, get_price])
            """
        )

        model = donkey.langgraph.chat_model(MODEL, temperature=0)
        say.field("type", f"{type(model).__module__}.{type(model).__name__}")
        say.field(
            "governed via",
            ", ".join(sorted(donkey.langgraph.connection_kwargs())),
        )
        say.note(
            "A real ChatOpenAI. bind_tools, stream, astream, structured output — "
            "everything LangChain can do with a chat model still works, because "
            "nothing was wrapped."
        )

        say.pause()
        say.step(2, "Run the agent loop")
        agent = create_agent(model, tools=[check_inventory, get_price])
        say.field("question", QUESTION)
        print()

        calls = 0
        async for chunk in agent.astream(
            {"messages": [("user", QUESTION)]}, stream_mode="updates"
        ):
            for node, update in chunk.items():
                for message in update.get("messages", []):
                    if getattr(message, "tool_calls", None):
                        for call in message.tool_calls:
                            calls += 1
                            print(f"    tool call    {call['name']}({call['args']})")
                    elif node == "tools":
                        print(f"    tool result  {redact.text(message.content)}")
                    elif message.content:
                        print()
                        say.field("answer", redact.text(message.content))

        say.pause()
        say.step(3, "What the governance layer saw")
        say.field("tool calls made", calls, raw=True)
        budget = donkey.budget
        say.field("budget.remaining", budget.remaining, raw=True)
        say.field(
            "budget.fraction_used",
            f"{budget.fraction_used:.1%}" if budget.fraction_used is not None else "unobserved",
            raw=True,
        )
        say.note(
            "Several model calls in one agent run, all through one transport — so "
            "the budget is the run's real consumption, and a single correlation id "
            "ties the whole loop together in the gateway's observability view."
        )

        print()
        say.section("The point")
        say.note(
            "The agent code is ordinary LangGraph. The only DDK line is "
            "the one that built the model. That is the whole proposition: "
            "governance at the boundary, not in your agent's control flow."
        )


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 09 — a governed LangGraph agent",
        subtitle="A real tool-calling loop through the deep adapter. Needs live credentials.",
        target="live",
        extras=("langchain_openai", "langgraph"),
    )
