"""Demo 09 — a real LangGraph agent, governed, doing real tool calls.

Everything before this demo could be accused of being a client library talking
to itself. This one runs an actual multi-step agent: the model decides to call
two tools, the tools return, the model composes an answer. Every model call in
that loop goes through the governed proxy, and the object driving it is
LangChain's own `ChatOpenAI` — not a wrapper the SDK invented.

This is the deep, conformance-gated adapter. The other seven frameworks are
supported at `connection_kwargs()` (demo 08).

**Live only.** This is a real multi-step tool-calling loop, so it needs a model
that can actually decide to call tools. The local simulator replays a captured
`/responses` completion and will not drive that loop. The adapter itself *does*
target `/responses` (`use_responses_api=True`) — the same live-verified route
as `donkey.openai()`. The refusal path can be exercised offline: see act 6 of
demo 04, which drives this same `ChatOpenAI` through `donkey.simulate()`.

**What step 3 can and cannot show.** `donkey.budget` is the proxy's shared
token window for this client id, populated only on proxies that send the
header. `donkey.last_call` stays `unobserved` after the loop: it is per asyncio
task, and LangGraph makes each model call on its own task (DDK #613 tracks a
run-level record).

    python demos/claude-made/09_langgraph_agent/demo.py        # needs real credentials
    DEMO_LANGGRAPH_API=chat python demos/.../demo.py           # proxy without /responses
"""

from __future__ import annotations

import asyncio
import os

from donkey_kit import Donkey, registered_tools
from langchain_core.tools import tool

from _harness import narrate as say
from _harness import preflight, redact

MODEL = os.environ.get("DEMO_MODEL", "gpt-4o-mini")
# `chat` for a proxy whose upstream has no `/responses` route (e.g. ddk-token-rate-limit).
API = os.environ.get("DEMO_LANGGRAPH_API", "responses")
QUESTION = "Can I ship SKU AF-1001 today, and what does it cost?"

INVENTORY = {"AF-1001": "42 units in Amsterdam", "AF-2002": "0 units"}
PRICES = {"AF-1001": "EUR 129.00", "AF-2002": "EUR 89.50"}


@tool
@Donkey.tool
def check_inventory(sku: str) -> str:
    """Return the units in stock and warehouse for a product SKU."""
    return INVENTORY.get(sku, "unknown SKU")


@tool
@Donkey.tool
def get_price(sku: str) -> str:
    """Return the list price for a product SKU."""
    return PRICES.get(sku, "unknown SKU")


def _text(message: object) -> str:
    """The visible text of a message; `/responses` content is a list of typed blocks."""
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    return "".join(
        b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
    )


async def _main() -> None:
    # Deferred so a missing `langchain` reaches preflight's install hint, not a traceback.
    from langchain.agents import create_agent

    async with Donkey.from_env() as donkey:
        say.step(1, "One call gets LangChain's own model object")
        say.code(
            """
            model = donkey.langgraph.chat_model("gpt-4o-mini")
            agent = create_agent(model, tools=[check_inventory, get_price])
            """
        )

        # No `temperature`: reasoning models (gpt-5, o-series) reject it with a 400.
        if API == "chat":
            from langchain_openai import ChatOpenAI

            # chat_model() cannot take `use_responses_api=False`: it collides with the
            # adapter's own kwarg (TypeError), so build from connection_kwargs().
            kwargs = {**donkey.langgraph.connection_kwargs(), "use_responses_api": False}
            model = ChatOpenAI(model=MODEL, **kwargs)
        else:
            model = donkey.langgraph.chat_model(MODEL)
        say.field("type", f"{type(model).__module__}.{type(model).__name__}")
        say.field("route", "/chat/completions" if API == "chat" else "/responses")
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
        say.code(
            """
            async with donkey.run(id="sku-lookup"):
                with donkey.langgraph.typed_refusals():
                    async for chunk in agent.astream(...):
                        ...
            """
        )

        calls = 0
        async with donkey.run(id="sku-lookup"):
            with donkey.langgraph.typed_refusals():
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
                            elif _text(message):
                                print()
                                say.field("answer", redact.text(_text(message)))

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
        last = donkey.last_call
        say.field("last_call.status", last.status.value, raw=True)
        say.field("last_call.served_model", last.served_model, raw=True)
        say.field("last_call.total_tokens", last.total_tokens, raw=True)
        say.field("last_call.substituted", last.substituted, raw=True)
        marked = {s.name: s for s in registered_tools()}
        for name in ("check_inventory", "get_price"):
            spec = marked.get(name)
            if spec is not None:
                say.field(f"@donkey.tool {name}", spec.docstring)
        if budget.fraction_used is not None:
            budget_note = (
                "budget is the proxy's token window for this client id, read in-band "
                "from every response in the loop. It is shared, not per run: it "
                "includes anything else this client spent in the window."
            )
        else:
            budget_note = (
                "budget is unobserved: this proxy sends no token-window header. Only "
                "proxies with a token rate-limit policy do (e.g. ddk-token-rate-limit)."
            )
        say.note(
            "Several model calls in one agent run, all through one transport, and "
            f"donkey.run(id=…) ties the whole loop together with one run id. {budget_note}"
        )
        if last.status.value == "unobserved":
            say.note(
                "last_call reads 'unobserved' here, and that is by design. LangGraph "
                "made each model call on its own asyncio task, and last_call is "
                "scoped per task so parallel siblings never overwrite each other's "
                "record — so it never reaches this outer scope. On a direct call it "
                "is populated (demo 10). A run-level record of every call is tracked "
                "in DDK #613."
            )
        say.note(
            "typed_refusals() is the node-level bridge: a proxy 403 surfaces out "
            "of astream as PIIDetected, not a framework-wrapped generic error. "
            "@donkey.tool marked the same functions the agent just called — it "
            "records them for a scanner, it does not wrap them."
        )

        print()
        say.section("The point")
        say.note(
            "The agent code is ordinary LangGraph. The DDK lines are the one "
            "that built the model, donkey.run(id=…) around the loop, "
            "typed_refusals() so a gateway 403 is PIIDetected rather than a "
            "framework-wrapped generic, and @donkey.tool on the two functions. "
            "Governance at the boundary, not in the agent's control flow."
        )


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 09 — a governed LangGraph agent",
        subtitle="A real tool-calling loop through the deep adapter. Needs live credentials.",
        target="live",
        extras=("langchain_openai", "langgraph", "langchain"),
    )
