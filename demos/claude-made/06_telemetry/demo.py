"""Demo 06 — OpenTelemetry GenAI spans and the run-scoped correlation id.

Two things a platform team asks for and an agent team rarely delivers: a trace
that follows one logical run across every model call it fans out into, and spans
that speak the standard GenAI vocabulary so they land in existing dashboards
rather than a bespoke one.

Both come from the same place the budget and the typed refusals come from — the
one client every request leaves through. Set `OTEL_EXPORTER_OTLP_ENDPOINT` and
`Donkey.from_env()` installs the exporter; with no endpoint the path is inert
and silent. This demo installs an in-memory exporter so the spans can be a table.

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
    DONKEY_ROUTING_FALLBACK,
    DONKEY_ROUTING_TYPE,
    DONKEY_USAGE_CACHE_WRITE_TOKENS,
    DONKEY_USAGE_CACHED_TOKENS,
    DONKEY_USAGE_REASONING_TOKENS,
    GEN_AI_COMPLETION,
    GEN_AI_PROMPT,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_RESPONSE_MODEL,
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
    spans = exporter.get_finished_spans()
    _show_spans(exporter, expect=1)
    print()
    attributes = dict(spans[0].attributes or {}) if spans else {}
    leaked = [k for k in (GEN_AI_PROMPT, GEN_AI_COMPLETION) if k in attributes]
    if leaked:
        say.fail(f"content attributes present by default: {leaked}")
    else:
        say.ok("gen_ai.prompt / gen_ai.completion are absent — capture is opt-in")
    print()
    say.note(
        f"The gen_ai.* keys are pinned to semantic-convention version "
        f"{GEN_AI_SEMCONV_VERSION}. They are transcribed in the SDK rather than "
        f"imported from the semconv package, whose default version drifts release "
        f"to release — so what lands on your span is decided by a reviewable edit, "
        f"not by a transitive upgrade."
    )
    say.note(
        "Prompt and completion stay off the span unless you set "
        "telemetry_capture_content=True (or DONKEY_TELEMETRY_CAPTURE_CONTENT=1). "
        "The gateway masks PII in its logs; spans are emitted upstream of that, "
        "so defaulting capture on would re-export the content the platform just "
        "masked."
    )
    print()
    say.section("Routing and usage, on the same span")
    routing = {
        "gen_ai.request.model": attributes.get(GEN_AI_REQUEST_MODEL),
        "gen_ai.response.model": attributes.get(GEN_AI_RESPONSE_MODEL),
        DONKEY_ROUTING_TYPE: attributes.get(DONKEY_ROUTING_TYPE),
        DONKEY_ROUTING_FALLBACK: attributes.get(DONKEY_ROUTING_FALLBACK),
    }
    usage = {
        k: attributes.get(k)
        for k in (
            DONKEY_USAGE_CACHED_TOKENS,
            DONKEY_USAGE_CACHE_WRITE_TOKENS,
            DONKEY_USAGE_REASONING_TOKENS,
        )
        if k in attributes
    }
    say.table({k: str(v) for k, v in routing.items() if v is not None}, title_="routing")
    if usage:
        say.table({k: str(v) for k, v in usage.items()}, title_="donkey.usage.*")
    else:
        say.note("donkey.usage.* is absent when the gateway reported no cached/reasoning counts.")
    print()
    say.note(
        "gen_ai.response.model is what the gateway actually served. When it "
        "differs from gen_ai.request.model, a failover happened — the fastest "
        "read on a latency spike. donkey.routing.fallback is emitted even when "
        "False: 'we routed normally' is a signal, not the absence of one. The "
        "same facts live on donkey.last_call without a span backend (demo 10)."
    )


async def act_2_correlation(donkey: Donkey, exporter) -> None:
    say.step(2, "One correlation id for a whole run, however many calls it makes")
    say.code(
        """
        async with donkey.run(id=ticket.id, team="support", project="triage"):
            await client.responses.create(...)     # all three calls share
            await client.responses.create(...)     # one id, and the cost
            await client.responses.create(...)     # tags, on wire and spans
        """
    )
    client = donkey.openai()
    # A ticket number, not a uuid: the value of binding the id yourself is that
    # the gateway record is searchable by something the business already knows.
    ticket = "ticket-4417"
    async with donkey.run(id=ticket, team="support", project="triage"):
        say.field("run id", current_correlation_id(), raw=True)
        for _ in range(3):
            await client.responses.create(model=MODEL, input="fan out")

    spans = exporter.get_finished_spans()
    ids = {(s.attributes or {}).get("donkey.correlation_id") for s in spans}
    teams = {(s.attributes or {}).get("donkey.cost.team") for s in spans}
    projects = {(s.attributes or {}).get("donkey.cost.project") for s in spans}
    envs = {(s.attributes or {}).get("donkey.cost.env") for s in spans}
    say.field("spans emitted", len(spans), raw=True)
    say.field("distinct correlation ids", len(ids), raw=True)
    if ids == {ticket}:
        say.ok(f"all {len(spans)} spans carry the one run id")
    if teams == {"support"} and projects == {"triage"} and envs == {"dev"}:
        say.ok("run() overrode team/project; env inherited from from_env()")
    else:
        say.warn(
            f"cost tags: team={teams} project={projects} env={envs} "
            "(expected support / triage / dev)"
        )
    exporter.clear()

    print()
    say.note(
        "Nothing was threaded through the agent. The id is bound to the async "
        "context, and tasks the framework spawns copy that context — so a "
        "LangGraph node running the model on a child task is inside the same run "
        "without knowing the run exists. Concurrent runs do not leak into each "
        "other, and nested run() blocks rebind then restore. Cost tags ride the "
        "same context: run(team=..., project=...) overrides those dimensions for "
        "the block and inherits the rest from from_env()."
    )

    print()
    say.section("Two ids, two questions")
    say.field("run    header", CORRELATION_HEADER)
    say.field("call   header", CALL_ID_HEADER)
    say.note(
        "The run id answers 'show me everything this ticket did'. The per-call id "
        "answers 'which one of those calls was this'. X-Correlation-Id is "
        "live-verified inbound: the gateway reads it and echoes it, which is what "
        "lets a line in your log join to the gateway's own record. Cost tags do "
        "not: they live on donkey.cost.* spans; the gateway has no inbound "
        "cost-tag ingestion (verified-negative)."
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


async def act_4_otlp_export() -> None:
    say.step(4, "Zero-config OTLP: set the standard env var, or stay silent")
    say.code(
        """
        # no Donkey-specific variable
        export OTEL_EXPORTER_OTLP_ENDPOINT=https://…
        donkey = Donkey.from_env()   # installs OTLP behind a BatchSpanProcessor
        # no endpoint → inert, silent, nothing connects
        # DONKEY_TELEMETRY=false    → opt out even if an endpoint is set
        """
    )
    traces = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").strip()
    endpoint = traces or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if endpoint:
        say.field(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT" if traces else "OTEL_EXPORTER_OTLP_ENDPOINT",
            "set",
        )
        say.note(
            "An endpoint is set, so Donkey.from_env() would install OTLP — unless "
            "a TracerProvider is already in place. This demo installed an "
            "in-memory one first, so Donkey rode it rather than replacing it. "
            "Your spans still land in the table above. Opt out with "
            "DONKEY_TELEMETRY=false."
        )
    else:
        say.ok("no OTEL_EXPORTER_OTLP_ENDPOINT — export stayed inert and silent")
        say.note(
            "Donkey.from_env() installs OTLP only when that standard env var is "
            "set. It will not clobber a TracerProvider the host already installed "
            "— which is why this demo's in-memory table still works. Opt out with "
            "DONKEY_TELEMETRY=false (or telemetry = false in .donkey-kit.toml). "
            "Cost tags on donkey.run(team=..., project=...) are what let a "
            "backend slice refusals, budget and latency by agent without another "
            "attribute convention."
        )


async def _main() -> None:
    exporter = _install_exporter()
    async with Donkey.from_env(team="platform", env="dev") as donkey:
        await act_1_a_span_per_call(donkey, exporter)
        say.pause()
        await act_2_correlation(donkey, exporter)
        say.pause()
        await act_3_refusal_spans(donkey, exporter)
        say.pause()
        await act_4_otlp_export()

        print()
        say.section("The point")
        say.note(
            f"Span name is {SPAN_LLM_CHAT!r}. Nothing in the agent code above "
            f"mentions OpenTelemetry — the instrumentation hangs off the same "
            f"transport hooks as the budget and the typed refusals, which is why "
            f"they all landed in one milestone rather than three."
        )
        say.note(
            "Cost tags are the fixed four — team / project / env / enduser.id — "
            "set on from_env() and overridable per donkey.run(). They land on "
            "donkey.cost.* as the authoritative carrier: the gateway has no "
            "inbound cost-tag ingestion (verified-negative). X-Correlation-Id is "
            "the opposite — the gateway reads it and echoes it. Routing "
            "(donkey.routing.*) and cached/reasoning usage (donkey.usage.*) land "
            "on the same span. Zero-config OTLP is shipped: "
            "OTEL_EXPORTER_OTLP_ENDPOINT, otherwise silent."
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
