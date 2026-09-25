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

## How to run

**Offline.** No gateway, no simulator, no credentials. `--target` is ignored.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[llm]"   # or: python -m pip install -e ".[sdk]"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=13
python run.py 13                           # same thing without make
```

**Live note:** The live wallet call is human-made `openai/14 - jwt-wallet.py`; it needs a wallet-backed proxy and an IdP JWT.

**3. What you should see:**

1. `validated(need="llm")` in jwt mode asking for `llm_proxy_wallet_client_id`, not a secret.
2. `proxy_auth_headers()` carrying `X-Client-Id` only.
3. `Donkey(llm_auth=StaticToken(...))` building an async client; `sync=True` and a missing provider as `ConfigError`.
4. A `MockTransport` showing `Authorization` overwritten on every send.
5. `classify()` honesty: invalid 401 is `AuthError`, missing 400 a generic `PolicyViolation`.

**4. If something goes wrong:**

- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §1.1`. See [PRESENTING.md](../../../PRESENTING.md#13--jwt--model-wallet-auth).
