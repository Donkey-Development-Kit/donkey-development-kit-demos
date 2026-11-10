# Delegate to a governed A2A agent; a captured gateway refusal is a typed error.
# Offline: donkey.simulate_a2a() declares the agent and replays Omni Gateway captures.
# Needs: pip install "donkey-kit[a2a]"  (SDK >= 0.2.1)
import asyncio
import os

os.environ["OTEL_INSTRUMENTATION_A2A_SDK_ENABLED"] = "false"  # before importing a2a

from a2a.types import Message, Part, Role, SendMessageRequest  # noqa: E402
from donkey_kit import (  # noqa: E402
    ContentSafetyBlocked,
    Donkey,
    DonkeyConfig,
    TokenBudgetExceeded,
)

config = DonkeyConfig(
    llm_proxy_url="https://demo-gateway.example.invalid/a2a-demo/",
    llm_proxy_client_id="not-a-real-id",
    llm_proxy_client_secret="not-a-real-secret",
)
ref = "acme/claims-triage-agent/1.0.0"
request = SendMessageRequest(
    message=Message(
        message_id="claim-1", role=Role.ROLE_USER, parts=[Part(text="Triage claim 1.")]
    )
)


async def main():
    async with Donkey(config) as donkey:
        with donkey.simulate_a2a("azure-block-send", agents=[ref]):
            try:
                await donkey.a2a.send(ref, request)
            except ContentSafetyBlocked as exc:
                print("blocked:", exc.categories)
            response = await donkey.a2a.send(ref, request)  # times=1: next call passes
            print("reply:", response.message.parts[0].text)

        with donkey.simulate_a2a("rate-stream", agents=[ref]):
            try:
                async with donkey.a2a.stream(ref, request) as events:
                    async for _ in events:
                        pass
            except TokenBudgetExceeded as exc:
                print("rate limited, retry after", exc.retry_after, "s")


asyncio.run(main())
