"""Demo 06 — OpenTelemetry GenAI spans and the run-scoped correlation id.

Two things a platform team asks for and an agent team rarely delivers: a trace
that follows one logical run across every model call it fans out into, and spans
that speak the standard GenAI vocabulary so they land in existing dashboards
rather than a bespoke one.

Both come from the same place the budget and the typed refusals come from — the
one client every request leaves through. The developer configures an exporter
and gets the rest.

Two attribute namespaces land on one span, deliberately:

* `gen_ai.*` follows the OpenTelemetry GenAI semantic conventions, pinned to a
  specific version in the SDK rather than tracking whatever the installed
  semconv package happens to emit this week.
* `donkey.*` is the stable Donkey namespace. Renaming one of those keys is
  a breaking change, independent of any semconv bump.

The run id is bound with `donkey.run(id=...)`, which works as both a sync and an
async context manager and propagates into tasks the framework spawns.

    pip install "donkey-kit[otel]"
    python demos/claude-made/06_telemetry/demo.py
"""

from __future__ import annotations

import asyncio
import os

import openai
from donkey_kit import Donkey
from donkey_kit.core.errors import classify
from donkey_kit.core.telemetry import (
    GEN_AI_SEMCONV_VERSION,
    SPAN_LLM_CHAT,
    current_correlation_id,
)
from donkey_kit.core.transport import CALL_ID_HEADER, CORRELATION_HEADER

from _harness import mock, preflight
from _harness import narrate as say

MODEL = os.environ.get("DEMO_MODEL", "gpt-4o")


def _install_exporter():
    """An in-memory exporter, so the demo can show the spans as a table instead
    of as a wall of console-exporter JSON."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


def _show_spans(exporter, *, expect: int | None = None) -> None:
    spans = exporter.get_finished_spans()
    if not spans:
        say.warn("no spans were exported")
        return
    for span in spans:
        print()
        say.field("span", span.name)
        say.field("status", span.status.status_code.name, raw=True)
        attributes = dict(span.attributes or {})
        gen_ai = {k: v for k, v in attributes.items() if k.startswith("gen_ai.")}
        donkey_ns = {k: v for k, v in attributes.items() if k.startswith("donkey.")}
        say.table({k: str(v) for k, v in gen_ai.items()}, title_="gen_ai.*")
        say.table({k: str(v) for k, v in donkey_ns.items()}, title_="donkey.*")
    if expect is not None and len(spans) != expect:
        say.warn(f"expected {expect} span(s), got {len(spans)}")
    exporter.clear()


async def act_1_a_span_per_call(donkey: Donkey, exporter) -> None:
    say.step(1, "One governed call, one GenAI span — with no instrumentation code")
    say.code(
        """
        # your usual OTel setup, then:
        await client.responses.create(model=..., input=...)
        """
    )
    client = donkey.openai()
    await client.responses.create(model=MODEL, input="hello")
    _show_spans(exporter, expect=1)
    print()
    say.note(
        f"The gen_ai.* keys are pinned to semantic-convention version "
        f"{GEN_AI_SEMCONV_VERSION}. They are transcribed in the SDK rather than "
        f"imported from the semconv package, whose default version drifts release "
        f"to release — so what lands on your span is decided by a reviewable edit, "
        f"not by a transitive upgrade."
    )


async def act_2_correlation(donkey: Donkey, exporter) -> None:
    say.step(2, "One correlation id for a whole run, however many calls it makes")
    say.code(
        """
        async with donkey.run(id=ticket.id):       # your own business id
            await client.responses.create(...)     # all three calls
            await client.responses.create(...)     # share one id, on the
            await client.responses.create(...)     # wire and on the spans
        """
    )
    client = donkey.openai()
    # A ticket number, not a uuid: the value of binding the id yourself is that
    # the gateway record is searchable by something the business already knows.
    ticket = "ticket-4417"
    async with donkey.run(id=ticket):
        say.field("run id", current_correlation_id(), raw=True)
        for _ in range(3):
            await client.responses.create(model=MODEL, input="fan out")

    spans = exporter.get_finished_spans()
    ids = {(s.attributes or {}).get("donkey.correlation_id") for s in spans}
    say.field("spans emitted", len(spans), raw=True)
    say.field("distinct correlation ids", len(ids), raw=True)
    if ids == {ticket}:
        say.ok(f"all {len(spans)} spans carry the one run id")
    exporter.clear()

    print()
    say.note(
        "Nothing was threaded through the agent. The id is bound to the async "
        "context, and tasks the framework spawns copy that context — so a "
        "LangGraph node running the model on a child task is inside the same run "
        "without knowing the run exists. Concurrent runs do not leak into each "
        "other, and nested run() blocks rebind then restore."
    )

    print()
    say.section("Two ids, two questions")
    say.field("run    header", CORRELATION_HEADER)
    say.field("call   header", CALL_ID_HEADER)
    say.note(
        "The run id answers 'show me everything this ticket did'. The per-call id "
        "answers 'which one of those calls was this'. Both go out on every "
        "request, which is what lets a line in your log join to the gateway's own "
        "record of the same call."
    )


async def act_3_refusal_spans(donkey: Donkey, exporter) -> None:
    say.step(3, "A refusal is a failed span, not a successful-looking one")
    say.note(
        "A span that ends OK on a request the gateway refused is worse than no "
        "span: it makes a dashboard say everything is fine. So a refusal sets the "
        "span status to ERROR and records what refused it."
    )
    client = donkey.openai()
    refusal = None
    async with donkey.run(id="ticket-4417"):
        try:
            await client.responses.create(
                model=mock.sentinel("pii-detected"), input="a@b.com"
            )
        except openai.APIStatusError as err:
            refusal = classify(err.response)
    _show_spans(exporter, expect=1)
    print()
    say.note(
        "donkey.policy.decision is 'refuse' and donkey.policy.type names the "
        "specific policy — so a dashboard can separate 'the model failed' from "
        "'governance said no', which are very different operational stories."
    )

    if refusal is not None:
        print()
        say.section("The same two ids, on the exception")
        say.field("type", type(refusal).__name__)
        say.field(".correlation_id", refusal.correlation_id, raw=True)
        say.field(".call_id", refusal.call_id, raw=True)
        say.note(
            "classify() read those back off the request the failed response came "
            "from, so the exception you catch already carries the ids without you "
            "passing them in. Put .correlation_id in the alert and the platform "
            "team can pull the gateway's record of the same refusal."
        )


async def _main() -> None:
    exporter = _install_exporter()
    async with Donkey.from_env() as donkey:
        await act_1_a_span_per_call(donkey, exporter)
        say.pause()
        await act_2_correlation(donkey, exporter)
        say.pause()
        await act_3_refusal_spans(donkey, exporter)

        print()
        say.section("The point")
        say.note(
            f"Span name is {SPAN_LLM_CHAT!r}. Nothing in the agent code above "
            f"mentions OpenTelemetry — the instrumentation hangs off the same "
            f"transport hooks as the budget and the typed refusals, which is why "
            f"they all landed in one milestone rather than three."
        )
        say.note(
            "Not shipped yet: zero-config OTLP export and validated cost tags. "
            "donkey.cost.team exists as an attribute key; the validated API that "
            "populates it is still open."
        )


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 06 — OTel GenAI spans and correlation ids",
        subtitle="Standard GenAI telemetry and one trace per run, without instrumentation code.",
        target="mock",
        extras=("openai", "opentelemetry.sdk"),
    )
