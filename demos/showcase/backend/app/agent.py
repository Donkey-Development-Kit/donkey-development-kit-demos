"""The demo agent — a minimal LangGraph graph over a DDK-governed model.

This is the one deep, conformance-tested surface: ``donkey.langgraph.chat_model``
returns a native ``langchain_openai.ChatOpenAI`` pointed at the governed proxy.
The ``call_model`` node runs inside the LangGraph adapter's ``typed_refusals()``
so a gateway refusal raised inside the node propagates out of ``graph.ainvoke``
as the SDK's typed exception (``PIIDetected``, ``TokenBudgetExceeded``, …) rather
than a framework-wrapped generic error.

``build_graph`` takes a model, not a Donkey, so it is donkey-agnostic: the same
graph is driven by the chat route (with the process-wide Donkey) and by the
conformance factory in ``tests/agent_app.py`` (with the harness's per-scenario
Donkey whose transport has been swapped). The thing we grade is the thing we
ship.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from donkey_kit.integrations.langgraph import typed_refusals
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_graph(model: Any):
    """Compile a one-node graph around a governed chat model.

    ``typed_refusals()`` is the module-level, stateless bridge, so this graph
    carries no Donkey of its own — whichever Donkey built ``model`` owns the
    transport and the run scope.
    """

    async def call_model(state: AgentState) -> dict[str, list[AnyMessage]]:
        with typed_refusals():
            reply = await model.ainvoke(state["messages"])
        return {"messages": [reply]}

    graph = StateGraph(AgentState)
    graph.add_node("call_model", call_model)
    graph.add_edge(START, "call_model")
    graph.add_edge("call_model", END)
    return graph.compile()


def user_state(prompt: str) -> AgentState:
    return {"messages": [HumanMessage(prompt)]}
