import httpx
from donkey_kit.conformance.gateway import start_gateway
from donkey_kit.core.errors import classify

# No live gateway. Needs donkey-kit[local]. Same fixtures as 03, on a real port.
#
# python "demos/human-made/openai/15 - start-gateway.py"

gw = start_gateway()
gw.set_scenarios("pii_block:every=1")

response = httpx.post(
    f"{gw.url}/responses",
    json={"model": "gpt-4o", "input": "hello"},
    headers={
        "client_id": "demo-client-id-not-a-real-credential",
        "client_secret": "demo-client-secret-not-a-real-credential",
    },
)
error = classify(response)
print(type(error).__name__, response.status_code)
print("requests", gw.requests_received)

gw.close()
