import asyncio

from donkey_kit import Donkey, DonkeyConfig, GatewayUnavailable

# Nothing is listening on :9. No live gateway, no credentials.
# LangChain wraps openai's APIConnectionError, so GatewayUnavailable is two causes down.
#
# python "demos/human-made/langgraph/08 - gateway-unavailable.py"

cfg = DonkeyConfig(
    llm_proxy_url="http://127.0.0.1:9/",
    llm_proxy_client_id="demo-client-id-not-a-real-credential",
    llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
    timeout_s=2.0,
    max_retries=0,
)


async def main() -> None:
    async with Donkey(cfg) as donkey:
        try:
            with donkey.langgraph.typed_refusals():   # passes transport failures through
                await donkey.langgraph("gpt-4o").ainvoke("hello")
            print("NO ERROR — something was listening on :9")
        except Exception as err:
            print("raised", type(err).__name__)
            hit = err
            while hit is not None and not isinstance(hit, GatewayUnavailable):
                hit = hit.__cause__
            print("cause ", type(hit).__name__ if hit is not None else None)
            if hit is not None:
                print("base_url", hit.base_url)
                print(hit.remediation)


asyncio.run(main())
