"""Offline native LangGraph approval: no LLM, no credentials, no SDK private APIs."""

from donkey_kit import ApprovalRejected, Donkey, DonkeyConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


def main() -> None:
    effects = []
    with Donkey(DonkeyConfig(telemetry=False)) as donkey:

        @donkey.tool(approval="required", risk="financial", approval_timeout="10ms")
        def refund(ticket: str) -> str:
            """Record a synthetic refund in memory, only after approval."""
            effects.append(ticket)
            return "refunded locally"

        builder = StateGraph(dict)
        builder.add_node("refund", lambda state: {"result": refund(state["ticket"])})
        builder.add_edge(START, "refund")
        builder.add_edge("refund", END)
        saver = MemorySaver()
        graph = builder.compile(checkpointer=saver)
        thread = {"configurable": {"thread_id": "refund-approved"}}
        with donkey.run(id="copyable-approval"):
            paused = graph.invoke({"ticket": "synthetic-ticket"}, thread)
        assert paused["__interrupt__"][0].value["type"] == "donkey.approval"
        assert effects == []
        assert donkey.approvals.pending() == ()  # The graph checkpoint owns this pause.
        assert graph.get_state(thread).tasks[0].interrupts
        print("PENDING: native interrupt checkpointed; no side effects")

        # Native pauses have no DDK expiry, even with approval_timeout='10ms'.
        # Recompile against the same saver to resume its stored checkpoint.
        graph = builder.compile(checkpointer=saver)
        with donkey.run(id="copyable-approval"):
            done = graph.invoke(
                Command(resume={"approved": True, "by": "demo.reviewer"}), thread
            )
        assert done["result"] == "refunded locally"
        assert effects == ["synthetic-ticket"]
        print("APPROVED: Command(resume=...) ran the tool once")

        thread = {"configurable": {"thread_id": "refund-rejected"}}
        graph.invoke({"ticket": "rejected-ticket"}, thread)
        try:
            graph.invoke(Command(resume={"approved": False, "by": "demo.reviewer"}), thread)
        except ApprovalRejected:
            pass
        else:
            raise AssertionError("a rejected resume must not run the tool")
        assert effects == ["synthetic-ticket"]
        print("REJECTED: ApprovalRejected, with no additional effects")
        print(
            "MemorySaver is not durable; use a durable checkpointer for process restarts."
        )
        print("The node replays on resume: keep side effects after the gated call.")


if __name__ == "__main__":
    main()
