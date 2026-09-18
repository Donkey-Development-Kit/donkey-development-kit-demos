import os

from donkey_kit import Donkey

# Needs DONKEY_LLM_PROXY_URL, DONKEY_LLM_PROXY_CLIENT_ID, DONKEY_LLM_PROXY_CLIENT_SECRET
# Set OTEL_EXPORTER_OTLP_ENDPOINT to export; with no endpoint this is inert and silent.
# DONKEY_TELEMETRY=false opts out even if an endpoint is set.
#
# python "demos/human-made/openai/10 - zero-config-otlp.py"

print(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    or "(unset — Donkey.from_env() will not install an exporter)",
)

donkey = Donkey.from_env()
client = donkey.openai(sync=True)

with donkey.run(id="otel-zero-config", team="cx", project="welcome"):
    reply = client.responses.create(model="gpt-4o", input="Say hello in exactly three words.")
    print(reply.output_text)
    print("last_call", donkey.last_call.status.value, donkey.last_call.served_model)

donkey.close()
