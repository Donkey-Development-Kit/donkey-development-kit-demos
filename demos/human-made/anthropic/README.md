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

## Scripts

| # | Script | Gateway | Extra needs |
|---|---|---|---|
| 01 | `native-messages.py` | live, `Format=Anthropic` | — |
| 02 | `typed-refusals-simulated.py` | none (in-process) | any `DONKEY_LLM_PROXY_*` values |

### 01 — native-messages

```bash
python "demos/human-made/anthropic/01 - native-messages.py"
```

**You should see:** the reply; `served_provider`, `served_model`, input and
output tokens from `last_call`; then Anthropic's `request-id` header next to
`last_call.request_id`. `request-id` is not one of the headers the SDK reads
for `request_id` yet, so the two can differ (or the field be `None`).

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
