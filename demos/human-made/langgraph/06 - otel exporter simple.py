import asyncio

from donkey_kit import Donkey
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# Needs donkey-kit[langgraph], DONKEY_LLM_PROXY_*, OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_HEADERS.
# Host owns the TracerProvider; Donkey rides it (same as openai/06).
#
# python "demos/human-made/langgraph/06 - otel exporter simple.py"

provider = TracerProvider(resource=Resource.create({"service.name": "donkey-dev-kit"}))
provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)


async def main() -> None:
    async with Donkey.from_env() as donkey:
        model = donkey.langgraph("gpt-4o")
        async with donkey.run(id="lg-otel-demo", team="cx", project="welcome"):
            print((await model.ainvoke("Say hello in exactly three words.")).text)
            print((await model.ainvoke("Say goodbye in exactly three words.")).text)


asyncio.run(main())
provider.force_flush()
