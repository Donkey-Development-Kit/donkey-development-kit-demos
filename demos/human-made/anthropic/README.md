# Human-made — `anthropic/`

The native `anthropic` client from `donkey.anthropic.client()`, on the governed
transport. It sends `/v1/messages`, so it needs a proxy provisioned
**`Format=Anthropic`** (e.g. `ddk-anthropic-inbound`). The default DDK proxies
are `Format=OpenAI` and return 404 on `/v1/messages`.

## Install

```bash
source .venv/bin/activate
python -m pip install -e "../donkey-development-kit/python[llm,anthropic]"
```

## Environment

```bash
set -a; source .env.local; set +a
export DONKEY_LLM_PROXY_URL=https://REPLACE-ME.example.invalid/ddk-anthropic-inbound/   # 01 only; overrides the file
```

The client id and secret are the same pair as the other proxies. The model is
`claude-haiku-4-5-20251001` (the `MODEL` constant).

### Offline: `donkey mock`

`donkey mock` (SDK 0.2.1 or later) serves the native `POST /v1/messages` route from a
captured `Format=Anthropic` proxy, so `01` runs without a gateway:

```bash
donkey mock --port 8799 &                     # needs donkey-kit[cli,local]
export DONKEY_LLM_PROXY_URL=http://127.0.0.1:8799/
export DONKEY_LLM_PROXY_CLIENT_ID=mock-id DONKEY_LLM_PROXY_CLIENT_SECRET=mock-secret
python "demos/human-made/anthropic/01 - native-messages.py"
```

The reply is the replayed capture, not a model answer. Every response carries
`x-donkey-simulator: true`. `last_call` reports `served_provider anthropic`.

## Scripts

| # | Script | Gateway | Extra needs |
|---|---|---|---|
| 01 | `native-messages.py` | live `Format=Anthropic`, or `donkey mock` | — |
| 02 | `typed-refusals-simulated.py` | none (in-process) | any `DONKEY_LLM_PROXY_*` values |

### 01 — native-messages

```bash
python "demos/human-made/anthropic/01 - native-messages.py"
```

**You should see:** the reply; `served_provider`, `served_model`, input and
output tokens from `last_call`; then Anthropic's `request-id` header next to
`last_call.request_id`. On SDK `develop` the SDK reads `request-id`, so the two
match. On the released SDK the field may be `None`.

### 02 — typed-refusals-simulated

```bash
python "demos/human-made/anthropic/02 - typed-refusals-simulated.py"
```

`donkey.simulate(...)` works for the Anthropic client too, because it shares
the governed transport. **You should see:** one line per refusal —
`<anthropic error> -> <SDK type> <policy> <correlation id>`.

## If something goes wrong

- `404 … /v1/messages` — the URL points at a `Format=OpenAI` proxy.
- `ModuleNotFoundError: anthropic` — install the `[anthropic]` extra.
