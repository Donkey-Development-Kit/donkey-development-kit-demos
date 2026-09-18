from donkey_kit import Donkey, DonkeyConfig, GatewayUnavailable

# Nothing is listening on :9. No live gateway, no credentials.
#
# python "demos/human-made/openai/11 - gateway-unavailable.py"

donkey = Donkey(
    DonkeyConfig(
        llm_proxy_url="http://127.0.0.1:9/",
        llm_proxy_client_id="demo-client-id-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
        timeout_s=2.0,
        max_retries=0,
    )
)
client = donkey.openai(sync=True)

try:
    client.responses.create(model="gpt-4o", input="hello")
    print("NO ERROR — something was listening on :9")
except Exception as err:
    hit = err if isinstance(err, GatewayUnavailable) else err.__cause__
    print("raised", type(err).__name__)
    print("cause ", type(hit).__name__ if hit is not None else None)
    if isinstance(hit, GatewayUnavailable):
        print("base_url   ", hit.base_url)
        print("request_id ", hit.request_id)
        print("call_id    ", hit.call_id)
        print(hit.remediation)

donkey.close()
