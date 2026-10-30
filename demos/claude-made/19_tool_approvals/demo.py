"""Local approval decisions and native LangGraph checkpointed pause/resume."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from donkey_kit import (
    Approval,
    ApprovalRejected,
    ApprovalRequired,
    ApprovalTimedOut,
    Donkey,
    DonkeyConfig,
    PIIDetected,
)
from donkey_kit.core.telemetry import current_correlation_id

from _harness import narrate as say
from _harness import preflight

if TYPE_CHECKING:
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def request(call: Callable[[], object]) -> Approval:
    """Capture the SDK's pending decision, never run the tool early."""
    try:
        call()
    except ApprovalRequired as exc:
        return exc.approval
    raise AssertionError("a gated call must request approval")


async def story(exporter: InMemorySpanExporter) -> None:
    from donkey_kit.integrations.langgraph import APPROVAL_INTERRUPT
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command

    config = DonkeyConfig(
        llm_proxy_url="https://demo.example.invalid/",
        llm_proxy_client_id="demo-client-id-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
        max_retries=0,
        telemetry=False,  # No environment-driven OTLP; approval events use the host provider.
    )
    effects: list[tuple[str, str | None]] = []
    decisions: list[tuple[str, str, str]] = []
    async with Donkey(config) as donkey:

        @donkey.tool(approval="required", risk="financial")
        def refund(ticket: str) -> str:
            """Record a synthetic refund in the local ledger."""
            effects.append((ticket, current_correlation_id()))
            return "refund recorded locally"

        say.step(1, "Pending is not permission to perform a side effect")
        with donkey.run(id="approval-local"):
            approved = request(lambda: refund("PRIVATE-APPROVED-TICKET"))
        assert approved in donkey.approvals.pending()
        assert approved.risk == "financial"
        assert effects == []
        result = donkey.approvals.resolve(approved.id, approved_by="demo.reviewer")
        assert result == "refund recorded locally"
        assert effects == [("PRIVATE-APPROVED-TICKET", "approval-local")]
        decisions.append((approved.id, "approved", "approval-local"))
        assert approved not in donkey.approvals.pending()
        try:
            donkey.approvals.resolve(approved.id, approved_by="demo.reviewer")
        except KeyError:
            pass
        else:
            raise AssertionError("a decision must not run a tool twice")
        say.ok("Pending had zero effects; approval ran once under the original correlation")

        say.step(2, "Rejecting drops the pending call without executing it")
        with donkey.run(id="approval-rejected"):
            rejected = request(lambda: refund("PRIVATE-REJECTED-TICKET"))
        assert rejected in donkey.approvals.pending()
        assert donkey.approvals.reject(rejected.id, rejected_by="demo.reviewer") == rejected
        assert len(effects) == 1
        assert rejected not in donkey.approvals.pending()
        decisions.append((rejected.id, "rejected", "approval-rejected"))
        say.ok("Rejection recorded the reviewer; the local ledger did not change")

        say.step(3, "A short local expiry cannot execute the call")

        @donkey.tool(approval="required", risk="financial", approval_timeout="10ms")
        def expiring_refund(ticket: str) -> None:
            """A synthetic refund whose local approval expires quickly."""
            effects.append((ticket, current_correlation_id()))

        with donkey.run(id="approval-timeout"):
            expired = request(lambda: expiring_refund("PRIVATE-TIMED-OUT-TICKET"))

        async def until_expired() -> None:
            while not expired.expired:
                await asyncio.sleep(0)

        await asyncio.wait_for(until_expired(), timeout=1)
        try:
            donkey.approvals.resolve(expired.id, approved_by="demo.reviewer")
        except ApprovalTimedOut as exc:
            assert exc.approval == expired
        else:
            raise AssertionError("an expired approval must not execute")
        assert expired not in donkey.approvals.pending()
        assert len(effects) == 1
        decisions.append((expired.id, "timed_out", "approval-timeout"))
        say.ok("10ms expiry raised ApprovalTimedOut; no side effect and no long sleep")

        say.step(4, "A native LangGraph interrupt lives in the checkpoint")
        builder = StateGraph(dict)
        builder.add_node("refund", lambda state: {"result": refund(state["ticket"])})
        builder.add_edge(START, "refund")
        builder.add_edge("refund", END)
        saver = MemorySaver()
        graph = builder.compile(checkpointer=saver)
        thread = {"configurable": {"thread_id": "demo-approved-thread"}}
        local_pending = donkey.approvals.pending()
        with donkey.run(id="approval-graph"):
            paused = graph.invoke({"ticket": "PRIVATE-GRAPH-TICKET"}, thread)
        (interrupt,) = paused["__interrupt__"]
        assert interrupt.value["type"] == APPROVAL_INTERRUPT
        assert interrupt.value["risk"] == "financial"
        assert graph.get_state(thread).tasks[0].interrupts
        assert donkey.approvals.pending() == local_pending
        assert len(effects) == 1
        # Recompile with the same saver, not the original compiled graph.
        graph = builder.compile(checkpointer=saver)
        with donkey.run(id="approval-graph"):
            done = graph.invoke(
                Command(resume={"approved": True, "by": "demo.reviewer"}), thread
            )
        assert done["result"] == "refund recorded locally"
        assert effects[-1] == ("PRIVATE-GRAPH-TICKET", "approval-graph")
        assert len(effects) == 2
        decisions.append((interrupt.value["approval_id"], "approved", "approval-graph"))
        say.ok("Checkpoint held the pause; Command(resume=...) ran the tool once")

        rejected_thread = {"configurable": {"thread_id": "demo-rejected-thread"}}
        with donkey.run(id="approval-graph-rejected"):
            paused = graph.invoke({"ticket": "PRIVATE-GRAPH-REJECTED"}, rejected_thread)
            try:
                graph.invoke(
                    Command(resume={"approved": False, "by": "demo.reviewer"}),
                    rejected_thread,
                )
            except ApprovalRejected as exc:
                assert exc.approval.id == paused["__interrupt__"][0].value["approval_id"]
            else:
                raise AssertionError("a native rejection must raise ApprovalRejected")
        assert len(effects) == 2
        decisions.append(
            (
                paused["__interrupt__"][0].value["approval_id"],
                "rejected",
                "approval-graph-rejected",
            )
        )
        say.ok("Native rejection raised ApprovalRejected; no additional side effect")

        say.step(5, "Approval never lifts a downstream gateway refusal")

        @donkey.tool(approval="required", risk="pii")
        def summarise(ticket: str) -> str:
            """Request a governed summary before recording any local effect."""
            donkey.openai(sync=True).responses.create(model="gpt-4o", input=ticket)
            effects.append((ticket, current_correlation_id()))
            return "must not succeed"

        refused_builder = StateGraph(dict)
        refused_builder.add_node(
            "summary", lambda state: {"result": summarise(state["ticket"])}
        )
        refused_builder.add_edge(START, "summary")
        refused_builder.add_edge("summary", END)
        refused_graph = refused_builder.compile(checkpointer=MemorySaver())
        refused_thread = {"configurable": {"thread_id": "demo-refused-thread"}}
        with donkey.run(id="approval-downstream"):
            paused = refused_graph.invoke(
                {"ticket": "PRIVATE-REFUSED-TICKET"}, refused_thread
            )
        try:
            with donkey.simulate(PIIDetected), donkey.run(id="approval-downstream"):
                refused_graph.invoke(
                    Command(resume={"approved": True, "by": "demo.reviewer"}),
                    refused_thread,
                )
        except PIIDetected as exc:
            assert exc.correlation_id == "approval-downstream"
            assert exc.call_id
        else:
            raise AssertionError("approval must not override the simulated gateway")
        assert len(effects) == 2
        decisions.append(
            (
                paused["__interrupt__"][0].value["approval_id"],
                "approved",
                "approval-downstream",
            )
        )
        say.ok("Reviewer approved, gateway refused, and the post-request effect never ran")

    say.step(6, "Audit identity and correlation, never tool arguments")
    spans = exporter.get_finished_spans()
    events = [
        (event.name, dict(event.attributes or {}))
        for span in spans
        for event in span.events
    ]
    for approval_id, verdict, correlation in decisions:
        pending = [
            attrs
            for name, attrs in events
            if name == "donkey.approval.pending"
            and attrs["donkey.approval.id"] == approval_id
        ]
        decided = [
            attrs
            for name, attrs in events
            if name == f"donkey.approval.{verdict}"
            and attrs["donkey.approval.id"] == approval_id
        ]
        assert len(pending) == len(decided) == 1
        assert (
            pending[0]["donkey.correlation_id"]
            == decided[0]["donkey.correlation_id"]
            == correlation
        )
        if verdict in ("approved", "rejected"):
            assert decided[0][f"donkey.approval.{verdict}_by"] == "demo.reviewer"
        if correlation.startswith("approval-graph") or correlation == "approval-downstream":
            assert "donkey.approval.expires_at" not in pending[0]
    serialized = " ".join(span.to_json() for span in spans)
    assert "PRIVATE-" not in serialized
    assert "arguments" not in serialized
    assert len(spans) == 2 * len(decisions)
    say.ok(
        f"{len(spans)} in-memory approval spans: IDs, reviewer, correlation; no arguments"
    )
    say.note(
        "Local approvals are process-global memory, shared across Donkeys, and expire lazily. "
        "LangGraph holds native pauses in its checkpointer with no DDK expiry. MemorySaver "
        "is still memory: a durable saver is required to survive process restart. "
        "Checkpoint/interrupt payloads contain arguments and require access controls even "
        "though the spans omit them. No approval UI, queue, live model, or platform change."
    )


def main() -> None:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    if not isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
        raise RuntimeError(
            "Demo 19 requires a fresh uninstrumented process: an OpenTelemetry "
            "provider is already installed. No approval operations were run; "
            "refusing to send audit spans to the host exporter."
        )
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    try:
        if trace.get_tracer_provider() is not provider:
            raise RuntimeError(
                "Demo 19 could not install its isolated in-memory OTel provider"
            )
        asyncio.run(asyncio.wait_for(story(exporter), timeout=15))
    finally:
        provider.shutdown()


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 19 - tool approvals",
        subtitle="Local decisions, native graph pause/resume, and argument-free approval audit spans.",
        target="offline",
        extras=("openai", "langgraph", "opentelemetry.sdk"),
    )
