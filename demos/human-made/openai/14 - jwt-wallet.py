import asyncio
import os

from donkey_kit import Donkey, DonkeyConfig
from donkey_kit.core.auth import StaticToken

# Needs a wallet-backed proxy URL, DONKEY_LLM_PROXY_WALLET_CLIENT_ID (X-Client-Id),
# and DONKEY_LLM_JWT. The JWT is never a config field. jwt mode is async-only.
#
# python "demos/human-made/openai/14 - jwt-wallet.py"

cfg = DonkeyConfig.from_env().with_overrides(
    llm_proxy_auth="jwt",
    llm_proxy_wallet_client_id=os.environ["DONKEY_LLM_PROXY_WALLET_CLIENT_ID"],
)


async def main() -> None:
    async with Donkey(cfg, llm_auth=StaticToken(os.environ["DONKEY_LLM_JWT"])) as donkey:
        client = donkey.openai()
        response = await client.responses.create(
            model="gpt-4o",
            input="Say hello in exactly three words.",
        )
        print(response.output_text)
        last = donkey.last_call
        print("last_call.status      ", last.status.value)
        print("last_call.served_model", last.served_model)


asyncio.run(main())
