# 10 — last_call, routing, and per-call usage

**Claim:** a successful call now answers the same question a refusal already
did — which gateway served this, what it actually routed to, and what it cost —
without parsing headers or needing a span backend.

```bash
make demo N=10
```

**Needs:** nothing (`[llm]` + `[local]`).

**Five acts.** A cold process reporting `UNOBSERVED` rather than `None`; one
governed call populating `donkey.last_call` with the gateway's identity, routing
and usage; the substitution flag lighting up because the captured fixture was
served by a different model than the one we asked for; the same record on a
**semantic-routing** proxy, where `matched_topic` and `routing_score` fill in;
and `on_model_substitution="raise"` turning that flag into `ModelSubstituted`.

**Point at:** three honest states, never a bare `None`. `UNOBSERVED` is a cold
read; `OBSERVED` means the SDK saw a response (fields may still be `None` if the
gateway said nothing); `UNAVAILABLE` names the adapter surfaces that never route
through our transport (ADK via LiteLLM, CrewAI via its native OpenAI provider,
default_headers-only LlamaIndex, Agent Framework — `observes_last_call = False`).
Then `substituted`
— a silent model swap is otherwise
invisible to your cost model and your eval. Then `cached_tokens` /
`reasoning_tokens`: reading only `total_tokens` draws the wrong conclusion about
both cost and latency. An absent count is `None`, never `0`.

`request_id` is the upstream **provider's** id, passed through by the gateway —
`x-request-id` on OpenAI, `x-amzn-requestid` on Bedrock. Quote it to the
provider; the gateway-side join key is `correlation_id`. Demo 15 shows the
per-provider header names.

**Semantic routing.** Act 4 requests the simulator sentinel
`donkey-sim/success-semantic`, which replays the live-captured semantic-routing
`200` (the `Finance` topic). `routing_type` reads `Semantic` instead of
`ModelBased`, and two fields the model-based call left `None` fill in:
`matched_topic == "Finance"` and `routing_score == 0.62`. Both come from the
semantic-only `x-llm-proxy-semantic-routing-success` header. `substituted` is
`True` there too, and on a semantic proxy that is expected: the gateway picks
the model from the prompt's meaning, so the request's `model` is a placeholder.
With `--target live` the sentinel is skipped and act 4 reads act 2's record
against your proxy.

`ModelSubstituted` is deliberately not a `PolicyViolation`. The request
succeeded, against a model you did not choose. Same shape as
`BudgetReserveReached`: a client-side signal you opted into.

**Simulator honesty.** The captured happy-path fixture was recorded against
`gpt-5.1`. Asking for a different model id therefore looks like a substitution.
That is the fixture, not a live failover — and it is exactly the mismatch
`last_call` exists to surface. The SDK also never double-retries a `503` the
gateway already marked as a failover.

## How to run

**Local simulator by default.** The harness starts `donkey mock` on `127.0.0.1:8080`, points the SDK at it with fake credentials, and stops it afterwards. `--target live` runs the same acts against your proxy.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[llm,local,cli]"   # or: python -m pip install -e ".[sdk]"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=10                              # local simulator, auto-started
make demo N=10 ARGS="--target live"         # your proxy
python run.py 10                           # same thing without make
```

Live runs read three variables from your shell or a git-ignored `.env.local`
(see [Setup](../../../README.md#setup) for where the values come from):

```bash
cp .env.example .env.local     # then fill in:
# DONKEY_LLM_PROXY_URL=https://REPLACE-ME.example.invalid/REPLACE-ME/   (trailing /, no /v1)
# DONKEY_LLM_PROXY_CLIENT_ID=…
# DONKEY_LLM_PROXY_CLIENT_SECRET=…
```

**3. What you should see:**

1. A cold `last_call` reading `UNOBSERVED`.
2. `What the gateway did with the request` — provider, served model, routing type, fallback.
3. `What this call cost` — input, output, cached and reasoning tokens (`None` when absent, never `0`).
4. `Model-based (act 2) vs this call` — `routing_type` `ModelBased → Semantic`, `matched_topic` `None → Finance`, `routing_score` `None → 0.62`.
5. `substituted: True` (the fixture was served by `gpt-5.1`), then `on_model_substitution="raise"` raising `ModelSubstituted`.

**4. If something goes wrong:**

- `Could not start the local simulator` — the port is taken or `[local]` / `[cli]` is missing. Use another port: `DEMO_MOCK_URL=http://127.0.0.1:8099 make demo N=10`.
- Want the simulator in its own pane? Run `make mock` there, then `make demo N=10 ARGS="--no-autostart"`. `DEMO_QUIET_MOCK=0` shows its log.
- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §1.1`. See [PRESENTING.md](../../../PRESENTING.md#10--last_call).
