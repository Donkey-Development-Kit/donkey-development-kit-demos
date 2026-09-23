# 13 — JWT / model-wallet auth

**Claim:** the default CIE header pair is not the only data-plane ingress. A
wallet-backed proxy identifies the caller from an IdP JWT plus `X-Client-Id`,
and there is no `client_secret`.

```bash
make demo N=13
```

**Needs:** `[llm]`. Offline — no wallet, no IdP, no gateway. The JWT value is
an obviously-fake string; the transport is mocked.

**Five acts.** `validated(need="llm")` in jwt mode names `llm_proxy_wallet_client_id`
and does not ask for a secret. `proxy_auth_headers()` carries `X-Client-Id`
only. `Donkey(llm_auth=StaticToken(...))` constructs an async client;
`sync=True` and a missing provider are `ConfigError`s. A `MockTransport` shows
the sentinel `Authorization` overwritten per send. Then honesty:
`classify()` has no dedicated JWT types — invalid `401` is `AuthError`, missing
`400` falls through to generic `PolicyViolation`.

**Point at:** the rotating JWT is never a config field. Inferring jwt mode from
"no client_id" is deliberately not done.

Build guide: `BG §1.1`. See [PRESENTING.md](../../../PRESENTING.md#13--jwt--model-wallet-auth).
