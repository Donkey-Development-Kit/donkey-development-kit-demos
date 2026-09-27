"""OpenTelemetry wiring for the demo.

DDK emits one OTel GenAI span per governed call with no code from us. We do two
things here:

1. Register an in-memory span exporter so the UI can *show* the exact
   ``donkey.llm.chat`` span JSON DDK produced — the same spans that would flow
   to Grafana/Tempo over OTLP.
2. If ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, DDK's own zero-config export path
   also fires (e.g. into the optional ``grafana/`` stack). We don't wire that;
   DDK does. We only add the in-memory exporter for the in-UI viewer.

Must run before the first ``Donkey`` call, so ``main.py`` imports this at
module load.
"""

from __future__ import annotations

import json
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

# One process-wide in-memory exporter the routes read back from.
_exporter = InMemorySpanExporter()


def install() -> None:
    """Install the in-memory span processor. Idempotent-ish: only sets a
    provider if one is not already configured (so we ride an
    ``opentelemetry-instrument`` provider if present, like DDK does)."""
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    provider.add_span_processor(SimpleSpanProcessor(_exporter))


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


def span_to_dict(span: Any) -> dict[str, Any]:
    """Render a finished ReadableSpan the way the DDK docs show it."""
    ctx = span.get_span_context()
    return {
        "name": span.name,
        "trace_id": f"0x{ctx.trace_id:032x}",
        "span_id": f"0x{ctx.span_id:016x}",
        "status": span.status.status_code.name,
        "attributes": {k: _jsonable(v) for k, v in dict(span.attributes or {}).items()},
    }


def recent_spans(limit: int = 20) -> list[dict[str, Any]]:
    spans = list(_exporter.get_finished_spans())
    return [span_to_dict(s) for s in spans[-limit:]][::-1]


def latest_span() -> dict[str, Any] | None:
    spans = list(_exporter.get_finished_spans())
    return span_to_dict(spans[-1]) if spans else None


def clear() -> None:
    _exporter.clear()


def dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2)
