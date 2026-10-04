"""The agent factory the conformance suite grades.

This is the contract from DDK's testing docs::

    pytest --donkey-conformance --donkey-agent=tests.agent_app:build

``build(donkey)`` receives a fresh Donkey per scenario (its transport swapped to
replay one captured refusal) and returns an object with a callable ``run(input)``
the harness drives. It builds the *same* LangGraph graph the chat uses, so the
thing we grade is the thing we ship.

To pass the scenarios the suite asks about, ``run`` must:
  * not retry a refusal (the graph calls the model exactly once);
  * not swallow a typed refusal (``typed_refusals()`` converts it and we let it
    propagate out of ``run``);
  * propagate the run's correlation id into its own logs;
  * still work when budget headers are absent.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent import build_graph, user_state
from donkey_kit.core.telemetry import current_correlation_id

log = logging.getLogger("demo.agent")
log.setLevel(logging.INFO)  # ensure INFO records are created for the capture handler


class GraphAgent:
    def __init__(self, donkey: Any) -> None:
        self.donkey = donkey
        self.graph = build_graph(donkey.langgraph.chat_model("gpt-5.1"))

    async def run(self, text: str) -> Any:
        # The caller (here, the conformance harness) binds the run's correlation
        # id; we read the ambient one and carry it into our own logs so a failure
        # joins the run. Binding a fresh id here would shadow the caller's.
        cid = current_correlation_id()
        log.info("handling agent run", extra={"correlation_id": cid})
        return await self.graph.ainvoke(user_state(text))


def build(donkey: Any) -> GraphAgent:
    return GraphAgent(donkey)


# No exemptions claimed — this agent is expected to satisfy every scenario.
KNOWN_LIMITATIONS: dict[str, str] = {}
