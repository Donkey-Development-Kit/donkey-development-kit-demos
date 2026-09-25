# Human-made — `crewai/`

CrewAI 1.x with `donkey.crewai.llm("…")`. `openai/` models
go through CrewAI's native OpenAI provider to **`/chat/completions`, which is
not live-verified on the DDK proxies** (`/responses` is). CrewAI owns the
transport: the credentials go on the wire, but **no run id and no
`last_call`**.

## Install

```bash
source .venv/bin/activate
python -m pip install -e "../donkey-development-kit/python[llm,crewai]"
```

## Environment

```bash
set -a; source .env.local; set +a       # DONKEY_LLM_PROXY_URL / _CLIENT_ID / _CLIENT_SECRET
```

Both scripts set `CREWAI_TRACING_ENABLED=false` (unless you set it yourself)
because CrewAI otherwise stops on an interactive "view your traces?" prompt.
Change `"gpt-4o"` to a model your proxy routes.

## Scripts

| # | Script | Gateway | Extra needs |
|---|---|---|---|
| 01 | `basic-gw.py` | live | — |
| 02 | `typed-refusals-live.py` | live | PII policy for the first case |

### 01 — basic-gw

```bash
python "demos/human-made/crewai/01 - basic-gw.py"
```

A direct `llm.call(...)`, then a one-agent, one-task `Crew`. **You should
see:** the greeting, the crew's answer, CrewAI's `usage_metrics`, and
`last_call unavailable …`.

### 02 — typed-refusals-live

```bash
python "demos/human-made/crewai/02 - typed-refusals-live.py"
```

Three cases: `PIIDetected` (needs `llm-pii-detection-policy` with `Email`,
action `Reject`), `UpstreamRequestError`, `AuthError`. The native provider keeps
the openai error's response, so `classify()` types it. **You should see:**
`<case> -> <Type> <entities>` or `<case> NO REFUSAL`.

## If something goes wrong

- The script hangs with no output — the tracing prompt is waiting; export
  `CREWAI_TRACING_ENABLED=false`.
- `404` — the proxy's upstream has no `/chat/completions` route.
