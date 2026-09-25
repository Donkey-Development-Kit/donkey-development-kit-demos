# Human-made — `openai/`

The stock `openai` client, governed by `donkey.openai()`. Every call goes
through the SDK's transport, so `last_call`, the budget, spans, correlation ids
and `simulate()` all work. The route is `/responses`, which is live-verified on
the DDK proxies.

## Install

```bash
source .venv/bin/activate
python -m pip install -e "../donkey-development-kit/python[llm,local]"
python -m pip install -e "../donkey-development-kit/python[otel]"   # 06, 07, 10 only
```

## Environment

```bash
set -a; source .env.local; set +a       # DONKEY_LLM_PROXY_URL / _CLIENT_ID / _CLIENT_SECRET
```

Change `"gpt-4o"` to a model your proxy routes (the provisioned DDK proxies
route `gpt-5-mini`). See [the human-made README](../README.md) for details.

## Scripts

| # | Script | Gateway | Extra needs |
|---|---|---|---|
| 01 | `basic-responses-no-gw.py` | none — api.openai.com | `OPENAI_API_KEY` |
| 02 | `basic-responses-gw.py` | live | — |
| 03 | `typed-refusals-simulated.py` | none (in-process) | any `DONKEY_LLM_PROXY_*` values |
| 04 | `typed-refusals-live.py` | live | PII + token-rate policies |
| 05 | `budget_and_pacing.py` | live | token-rate policy |
| 06 | `otel exporter simple.py` | live | `[otel]`, OTLP endpoint |
| 07 | `otel exporter advanced.py` | live | `[otel]`, OTLP endpoint, PII policy |
| 08 | `last-call.py` | live | — |
| 09 | `governed-and-tool.py` | none | — |
| 10 | `zero-config-otlp.py` | live | optional OTLP endpoint |
| 11 | `gateway-unavailable.py` | none (closed port) | — |
| 12 | `streaming.py` | live only | — |
| 13 | `regex-and-content-safety.py` | live | regex-prompt-guard + Azure content safety |
| 14 | `jwt-wallet.py` | live, wallet proxy | IdP JWT |
| 15 | `start-gateway.py` | local simulator | `[local]` |
| 16 | `bedrock-guardrails.py` | live | Bedrock Guardrails policy |

### 01 — basic-responses-no-gw

Stock OpenAI with no gateway, the baseline everything else is compared to.

```bash
export OPENAI_API_KEY=…
python "demos/human-made/openai/01 - basic-responses-no-gw.py"
```

**You should see:** a three-word greeting. Nothing else — there is no SDK here.

### 02 — basic-responses-gw

The same call through `donkey.openai()`, then the `last_call` record.

```bash
python "demos/human-made/openai/02 - basic-responses-gw.py"
```

**You should see:** the reply, then `last_call.status observed`, the served
model, total tokens and `substituted False` (or `True` if the proxy served a
different model than you asked for).

### 03 — typed-refusals-simulated

`donkey.simulate(...)` replays five captured refusals in-process; each is
classified and printed with its policy, remediation, correlation id, call id
and request id. Ends with `simulate(GatewayUnavailable)` refusing — there is
no response to replay.

```bash
python "demos/human-made/openai/03 - typed-refusals-simulated.py"
```

**You should see:** one block each for `PIIDetected` (entities `Email`),
`PromptInjectionBlocked`, `ContentSafetyBlocked` (categories),
`TokenBudgetExceeded` (`retry_after`) and `PolicyViolation`, then a
`ValueError` message for `GatewayUnavailable`.

### 04 — typed-refusals-live

Four real refusals with the blocking client, no `async`:
`UpstreamRequestError` (unknown model), `PIIDetected`, `TokenBudgetExceeded`,
`AuthError` (deliberately wrong credentials). This one has its own
`MODEL = "gpt-4-turbo-2024-04-09"` constant at the top.

```bash
python "demos/human-made/openai/04 - typed-refusals-live.py"
```

**Needs:** `llm-pii-detection-policy` with `Email` in its entities and action
`Reject` (the default `Log` lets it through); `llm-token-rate-limit` with a
tiny `maximumTokens` for the budget case. **You should see:** `REFUSED
<Type> (HTTP n)` blocks. A case whose policy is missing prints `NO REFUSAL`
with the served model or budget window instead.

### 05 — budget_and_pacing

`donkey.budget.pace(reserve=0.99999)` lets the first call through, observes
the window in-band, then stops the second call locally with
`BudgetReserveReached`; `wait_for_reset()` then sleeps until a crafted 1-second
window resets.

```bash
python "demos/human-made/openai/05 - budget_and_pacing.py"
```

**Needs:** a proxy that sends the token-window header (`ddk-token-rate-limit`).
**You should see:** budget fields after request 1, then `stopped locally
[in-script]` and `Ended script after reset`. Without the header every field is
`None` and the second call simply goes through.

### 06 — otel exporter simple

The host owns a `TracerProvider` with an OTLP exporter; Donkey rides it. Two
calls inside `donkey.run(id="otel-demo")`.

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=https://<collector>   OTEL_EXPORTER_OTLP_HEADERS=…
python "demos/human-made/openai/06 - otel exporter simple.py"
```

**You should see:** two replies in the terminal and two spans sharing one
correlation id (`otel-demo`) in your collector, under `service.name
donkey-dev-kit`. Nothing about spans is printed locally.

### 07 — otel exporter advanced

Three `donkey.run(...)` scopes with different `team` / `project` cost tags: a
greeter, a PII refusal, and a second model. Prints budget and `last_call`
between them.

```bash
python "demos/human-made/openai/07 - otel exporter advanced.py"
```

**You should see:** `greeter:` reply with budget and `last_call`, `support:
PIIDetected ['Email']` (or `no refusal`), `researcher:` and the final budget.
In the collector: three traces, one `ERROR` span naming the PII policy.

### 08 — last-call

The full `last_call` record on a success, then `on_model_substitution="raise"`.

```bash
python "demos/human-made/openai/08 - last-call.py"
```

**You should see:** `before any call unobserved`, then status, request id,
requested vs served model, provider, routing type, fallback, substituted and
the token counts. The second half prints `NO RAISE` when the proxy served the
model you asked for, or `RAISED … ModelSubstituted` with both model ids.

### 09 — governed-and-tool

`@donkey.governed(team=…, project=…)` gives each handler call its own run id
and cost tags; `@donkey.tool` records a callable without wrapping it and
rejects one with no docstring.

```bash
python "demos/human-made/openai/09 - governed-and-tool.py"
```

**You should see:** `run id before None`, two different ids inside the handler
with the cost tags, `run id after None`, the `lookup_sku('AF-1001')` result,
`same function object True`, the registered name and signature, and the
`undescribed tool` error.

### 10 — zero-config-otlp

`Donkey.from_env()` installs an OTLP exporter itself when
`OTEL_EXPORTER_OTLP_ENDPOINT` is set and no provider exists.

```bash
python "demos/human-made/openai/10 - zero-config-otlp.py"                       # inert
OTEL_EXPORTER_OTLP_ENDPOINT=https://<collector> python "demos/human-made/openai/10 - zero-config-otlp.py"
```

**You should see:** the endpoint (or `(unset …)`), the reply and `last_call`.
`DONKEY_TELEMETRY=false` opts out even with an endpoint set.

### 11 — gateway-unavailable

A governed client aimed at `127.0.0.1:9`, where nothing listens.

```bash
python "demos/human-made/openai/11 - gateway-unavailable.py"
```

**You should see:** `raised APIConnectionError`, `cause GatewayUnavailable`,
the base URL, `request_id None` (no response ever came back), a call id, and
the remediation text naming the three usual causes.

### 12 — streaming

`responses.create(stream=True)`; the text deltas are joined and `last_call`
usage is read after the terminal event.

```bash
python "demos/human-made/openai/12 - streaming.py"
```

**Live only.** The simulator's stream is truncated SSE, so terminal usage would
be a lie there. **You should see:** the reply, `observed`, the served model and
total tokens.

### 13 — regex-and-content-safety

Two live guardrails: `regex-prompt-guard` → `PromptInjectionBlocked`, and
Azure Content Safety → `ContentSafetyBlocked` with its categories.

```bash
python "demos/human-made/openai/13 - regex-and-content-safety.py"
```

**Needs:** a proxy with both policies (e.g. `ddk-injection-guard` and
`ddk-azure-content-safety`; point `DONKEY_LLM_PROXY_URL` at each in turn if
they are separate proxies). **You should see:** the type and policy per case,
or `NO REFUSAL`.

### 14 — jwt-wallet

`llm_proxy_auth="jwt"`: `X-Client-Id` plus a rotating JWT, no client secret.
Async-only.

```bash
export DONKEY_LLM_PROXY_WALLET_CLIENT_ID=…  DONKEY_LLM_JWT=…
python "demos/human-made/openai/14 - jwt-wallet.py"
```

**Needs:** a wallet-backed proxy URL in `DONKEY_LLM_PROXY_URL` and a JWT from
your IdP. **You should see:** the reply, `observed` and the served model. An
invalid JWT is an `AuthError`.

### 15 — start-gateway

`start_gateway()` boots the SDK's simulator on an ephemeral port;
`set_scenarios("pii_block:every=1")` arms it; a stock `httpx.post` gets the
captured PII 403.

```bash
python "demos/human-made/openai/15 - start-gateway.py"
```

**You should see:** `PIIDetected 403` and `requests 1`.

### 16 — bedrock-guardrails

Amazon Bedrock Guardrails rejecting a prompt: same `ContentSafetyBlocked` as
Azure in 13, with the vendor in the message.

```bash
python "demos/human-made/openai/16 - bedrock-guardrails.py"
```

**Needs:** a proxy with Bedrock Guardrails applied (e.g.
`ddk-bedrock-guardrails`). **You should see:** `ContentSafetyBlocked
content-safety ['content_filter']`, the message, `x-request-id None` and a
`request_id` — Bedrock's own id comes from `x-amzn-requestid`.

## If something goes wrong

- `ConfigError … llm_proxy_url` — the variables are not exported. Re-run the
  `set -a; source .env.local; set +a` line in this shell.
- `ModuleNotFoundError: donkey_kit` / `openai` — the virtual environment is not
  active, or the extra is missing.
- `UNREACHABLE GatewayUnavailable` — wrong URL or no network route to the
  gateway. `donkey doctor` tells wrong URL from wrong credentials.
- `UpstreamRequestError` on every call — the proxy does not route `gpt-4o`;
  change the model.
