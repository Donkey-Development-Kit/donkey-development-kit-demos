from donkey_kit import Donkey
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# Needs DONKEY_LLM_PROXY_URL, DONKEY_LLM_PROXY_CLIENT_ID, DONKEY_LLM_PROXY_CLIENT_SECRET
# Needs OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_HEADERS

provider = TracerProvider(resource=Resource.create({"service.name": "donkey-dev-kit"}))
provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

donkey = Donkey.from_env()
client = donkey.openai(sync=True)

with donkey.run(id="otel-demo"):
    first = client.responses.create(model="gpt-4o", input="Say hello in exactly three words.")
    print(first.output_text)
    second = client.responses.create(model="gpt-4o", input="Say goodbye in exactly three words.")
    print(second.output_text)

provider.force_flush()
donkey.close()