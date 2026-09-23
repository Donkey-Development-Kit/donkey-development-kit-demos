"""Demo 13 — JWT / model-wallet auth is a parallel ingress, not a bearer CIE.

Default `llm_proxy_auth="client-id"` is the LIVE-VERIFIED `client_id` /
`client_secret` header pair (demo 01). A wallet-backed proxy disables that
enforcement: the caller is identified from an IdP JWT (`Authorization: Bearer`)
plus a durable wallet-selector `X-Client-Id`. There is no `client_secret`.

The rotating JWT is never a config field. It enters through an `AuthProvider`
(`Donkey(llm_auth=...)`) and is injected per-send. This demo stays offline:
config, headers, and the two guards. It does not call a live wallet.

    python demos/claude-made/13_jwt_wallet/demo.py
"""

from __future__ import annotations

import asyncio

import httpx
from donkey_kit import ConfigError, Donkey, DonkeyConfig
from donkey_kit.core.auth import StaticToken
from donkey_kit.core.errors import AuthError, PolicyViolation, classify
from donkey_kit.core.transport import DonkeyAsyncClient, proxy_auth_headers

from _harness import narrate as say
from _harness import preflight, redact

WALLET = "demo-wallet-selector-not-a-real-id"
JWT = "demo-jwt-not-a-real-credential"
URL = "https://demo-gateway.example.invalid/openai-sdk/"


def _jwt_cfg() -> DonkeyConfig:
    return DonkeyConfig(
        llm_proxy_auth="jwt",
        llm_proxy_url=URL,
        llm_proxy_wallet_client_id=WALLET,
    )


def act_1_config_does_not_want_a_secret() -> None:
    say.step(1, "jwt mode requires a wallet selector, not a client_secret")
    say.code(
        """
        DonkeyConfig(
            llm_proxy_auth="jwt",
            llm_proxy_url=...,
            llm_proxy_wallet_client_id=...,   # X-Client-Id
        ).validated(need="llm")
        """
    )
    try:
        DonkeyConfig(llm_proxy_auth="jwt", llm_proxy_url=URL).validated(need="llm")
        say.fail("expected ConfigError")
    except ConfigError as exc:
        say.ok("missing llm_proxy_wallet_client_id — named at once")
        for line in str(exc).splitlines():
            if "wallet" in line.lower() or "secret" in line.lower() or "Missing" in line:
                print(f"    {line}")

    ok = _jwt_cfg().validated(need="llm")
    say.field("llm_proxy_auth", ok.llm_proxy_auth, raw=True)
    say.field("wallet selector", redact.text(ok.llm_proxy_wallet_client_id))
    say.field("client_secret required", False, raw=True)
    print()
    say.note(
        "The mode is explicit. Inferring jwt from 'no client_id' would turn a "
        "typo into a silent switch. The rotating JWT is not a config field — "
        "it arrives as Donkey(llm_auth=...)."
    )


def act_2_headers_are_not_cie() -> None:
    say.step(2, "proxy_auth_headers() carries X-Client-Id only")
    headers = proxy_auth_headers(_jwt_cfg())
    say.table(redact.headers(dict(headers)), title_="jwt-mode snapshot:")
    if "client_id" not in headers and "client_secret" not in headers:
        say.ok("no CIE pair — Client ID Enforcement is disabled on a wallet proxy")
    if "Authorization" not in headers:
        say.ok("no Authorization in the snapshot — the JWT is injected per-send")
    print()
    say.note(
        "A static header dict cannot carry a credential that rotates. The "
        "transport reads AuthProvider.token() on every request and overrides "
        "the OpenAI SDK's mandatory api_key bearer."
    )


async def act_3_guards() -> None:
    say.step(3, "Two guards config alone cannot check")
    say.code(
        """
        donkey = Donkey(cfg, llm_auth=StaticToken(jwt))
        donkey.openai()            # async — ok
        donkey.openai(sync=True)   # ConfigError: async-only
        """
    )
    cfg = _jwt_cfg()
    with Donkey(cfg) as donkey:
        try:
            donkey.openai()
            say.fail("expected ConfigError without llm_auth")
        except ConfigError as exc:
            say.ok("no provider — names Donkey(llm_auth=...)")
            say.field("message", redact.text(str(exc).split(".")[0] + "."))

    with Donkey(cfg, llm_auth=StaticToken(JWT)) as donkey:
        client = donkey.openai()
        say.field("async client", f"{type(client).__module__}.{type(client).__name__}")
        try:
            donkey.openai(sync=True)
            say.fail("expected async-only ConfigError")
        except ConfigError as exc:
            say.ok("sync=True refused — the blocking client cannot await a rotating JWT")
            say.field("message", redact.text(str(exc).split(":")[0]))


async def act_4_per_send_bearer() -> None:
    say.step(4, "The transport overrides the sentinel bearer on every send")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("authorization", ""))
        return httpx.Response(200)

    cfg = _jwt_cfg()
    client = DonkeyAsyncClient(
        cfg, StaticToken(JWT), transport=httpx.MockTransport(handler)
    )
    try:
        await client.get("https://example.invalid/", headers={"Authorization": "Bearer sentinel"})
        await client.get("https://example.invalid/", headers={"Authorization": "Bearer sentinel"})
    finally:
        await client.aclose()

    if seen and all(value == f"Bearer {JWT}" for value in seen) and len(seen) == 2:
        say.ok("Authorization was the provider JWT twice — not the SDK sentinel")
    else:
        say.field("Authorization values", [redact.text(v) for v in seen], raw=True)
    say.note(
        "A wallet proxy reads Authorization as the JWT. Leaving the OpenAI "
        "api_key sentinel in place would authenticate as garbage."
    )


def act_5_classify_has_no_jwt_types() -> None:
    say.step(5, "classify() has no dedicated JWT types yet")
    invalid = httpx.Response(
        401,
        headers={"www-authenticate": "Bearer"},
        json={"error": "Invalid token."},
    )
    missing = httpx.Response(
        400,
        headers={"www-authenticate": "Bearer"},
        json={"error": "JWT Token is required."},
    )
    bad = classify(invalid)
    none = classify(missing)
    say.field("invalid JWT 401", type(bad).__name__)
    say.field("missing JWT 400", type(none).__name__)
    if isinstance(bad, AuthError):
        say.ok("401 + www-authenticate: Bearer → AuthError (the CIE 401 rule)")
    if isinstance(none, PolicyViolation) and type(none) is PolicyViolation:
        say.ok("400 missing-JWT falls through to generic PolicyViolation")
    print()
    say.note(
        "Those shapes are live-captured against a wallet proxy. Dedicated "
        "classify() types are not shipped — do not branch on JWT-specific "
        "classes that do not exist. CIE vs wallet is selected by "
        "llm_proxy_auth, not inferred from a 401."
    )


def main() -> None:
    act_1_config_does_not_want_a_secret()
    say.pause()
    act_2_headers_are_not_cie()
    say.pause()
    asyncio.run(act_3_guards())
    say.pause()
    asyncio.run(act_4_per_send_bearer())
    say.pause()
    act_5_classify_has_no_jwt_types()

    print()
    say.section("The point")
    say.note(
        "Two ingresses, one SDK. Default CIE is still demo 01. Wallet mode is "
        "opt-in, async-only, and the JWT never lives in a config file."
    )


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 13 — JWT / model-wallet auth",
        subtitle="A parallel ingress: X-Client-Id + a rotating JWT, no client_secret.",
        target="offline",
        extras=("openai",),
    )
