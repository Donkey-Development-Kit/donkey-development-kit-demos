import openai
from donkey_kit import Donkey
from donkey_kit.core.errors import classify
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# Needs DONKEY_LLM_PROXY_URL, DONKEY_LLM_PROXY_CLIENT_ID, DONKEY_LLM_PROXY_CLIENT_SECRET
# Needs OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_HEADERS

MODEL = "gpt-4o"
PII_PROMPT = (
    "Summarise this contact record in one line: "
    "John Doe, john.doe@example.com, +1 415 555 0132."
)

provider = TracerProvider(resource=Resource.create({"service.name": "donkey-dev-kit"}))
provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

donkey = Donkey.from_env()
client = donkey.openai(sync=True)

with donkey.run(id="agent-greeter", team="cx", project="welcome"):
    reply = client.responses.create(model=MODEL, input="Say hello in exactly three words.")
    print("greeter:", reply.output_text)
    print("  remaining", donkey.budget.remaining, "used", donkey.budget.fraction_used)

with donkey.run(id="agent-support", team="cx", project="tickets"):
    try:
        client.responses.create(model=MODEL, input=PII_PROMPT)
        print("support: no refusal")
    except openai.APIStatusError as err:
        error = classify(err.response)
        print("support:", type(error).__name__, getattr(error, "entities", None))

with donkey.run(id="agent-researcher", team="labs", project="eval"):
    try:
        client.responses.create(model="gpt-4o-mini", input="Say hello in exactly three words.")
        print("researcher: no refusal")
    except openai.APIStatusError as err:
        error = classify(err.response)
        print("researcher:", type(error).__name__)

print("budget remaining", donkey.budget.remaining, "/", donkey.budget.limit)
provider.force_flush()
donkey.close()