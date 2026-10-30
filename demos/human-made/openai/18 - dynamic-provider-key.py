"""Dynamic provider key + consumer auth, JWT omission and origin protection.

Local only: synthetic secrets, MockTransport, no dotenv/config-file reads.
X-Demo-Provider-Key is chosen by this example's customer route, NOT a universal
gateway contract. Configure the name that the route's Dynamic-key expression
actually reads. See SDK test_proxy_key_header.py.
"""

import asyncio

import httpx
from donkey_kit.core.auth import StaticToken
from donkey_kit.core.config import DonkeyConfig
from donkey_kit.core.transport import DonkeyAsyncClient, proxy_auth_headers
from openai import AsyncOpenAI


async def main():
    """Prove credential placement without contacting a gateway or provider."""
    cfg = DonkeyConfig(
        llm_proxy_url="https://proxy.example.invalid/openai/",
        llm_proxy_client_id="demo-client-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
        llm_proxy_key="demo-provider-key-not-a-real-credential",
        llm_proxy_key_header="X-Demo-Provider-Key",
        telemetry=False,
    )
    seen = []

    def local_model(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "id": "local-completion",
                "object": "chat.completion",
                "created": 0,
                "model": "local-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "local result"},
                    }
                ],
            },
        )

    headers = proxy_auth_headers(cfg)
    assert cfg.llm_proxy_key not in repr(headers)
    async with DonkeyAsyncClient(
        cfg, None, transport=httpx.MockTransport(local_model), trust_env=False
    ) as http:
        async with AsyncOpenAI(
            base_url=cfg.llm_proxy_url,
            api_key="unused-synthetic-openai-key",
            default_headers=headers,
            http_client=http.view(),
            max_retries=0,
        ) as client:
            await client.chat.completions.create(
                model="local-model",
                messages=[{"role": "user", "content": "synthetic-input"}],
            )
        proxy = seen[-1]
        assert proxy.headers[cfg.llm_proxy_key_header] == cfg.llm_proxy_key
        assert proxy.headers["client_id"] == cfg.llm_proxy_client_id
        assert proxy.headers["client_secret"] == cfg.llm_proxy_client_secret
        # Deliberately pass the same credentials to an unchecked origin. The
        # governed client strips them before the mock sees the outgoing request.
        await http.post(
            "https://unchecked.example.invalid/chat/completions", headers=headers
        )
        other = seen[-1]
        assert cfg.llm_proxy_key_header not in other.headers
        assert "client_id" not in other.headers and "client_secret" not in other.headers
        assert cfg.llm_proxy_key not in other.headers.values()

    wallet_cfg = cfg.with_overrides(
        llm_proxy_auth="jwt",
        llm_proxy_wallet_client_id="synthetic-wallet",
    )
    async with DonkeyAsyncClient(
        wallet_cfg,
        StaticToken("synthetic-wallet-token"),
        transport=httpx.MockTransport(local_model),
        trust_env=False,
    ) as wallet_http:
        await wallet_http.post(
            f"{wallet_cfg.llm_proxy_url}chat/completions",
            headers=proxy_auth_headers(wallet_cfg),
        )
    wallet = seen[-1]
    assert cfg.llm_proxy_key_header not in wallet.headers
    assert cfg.llm_proxy_key not in wallet.headers.values()
    assert wallet.headers["Authorization"] == "Bearer synthetic-wallet-token"
    assert wallet.headers["X-Client-Id"] == "synthetic-wallet"
    assert "client_id" not in wallet.headers and "client_secret" not in wallet.headers
    assert len(seen) == 3
    print("LOCAL ONLY: OpenAI client + governed MockTransport; no network or secrets read")
    print(
        "PASS: customer-configured provider-key header travels beside consumer authentication"
    )
    print("PASS: unchecked origin receives neither provider key nor consumer credentials")
    print(
        "PASS: JWT wallet sends token + wallet selector, NOT provider key or consumer pair"
    )
    print(
        "Header name belongs to the customer's Dynamic-key route; no universal header is claimed."
    )
    print("Synthetic credential values and prompt/completion content are not printed.")


if __name__ == "__main__":
    asyncio.run(main())
