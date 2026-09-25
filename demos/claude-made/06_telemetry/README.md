# 06 — OTel GenAI spans and correlation ids

**Claim:** standard GenAI telemetry and one trace per logical run, with no
instrumentation code in the agent.

```bash
pip install "donkey-kit[otel]"
make demo N=06
```

**Needs:** `[otel]` on top of `[llm]` + `[local]`. Without it the demo prints the
install command and exits cleanly.

**Four acts.** One call producing one span with both attribute namespaces, and
prompt/completion **absent** unless you opt in — plus `gen_ai.response.model` /
`donkey.routing.*` / `donkey.usage.*` on that same span; `donkey.run(id=…,
team=…, project=…)` giving three calls one correlation id and one set of
`donkey.cost.*` tags; a refused call producing an `ERROR` span that names the
policy; and zero-config OTLP — set `OTEL_EXPORTER_OTLP_ENDPOINT`, or stay silent.

Act 2 binds a **business** id (`ticket-4417`), not a uuid — that is the point of
binding it yourself. It propagates by async context, so a node the framework
runs on a child task is inside the same run without being told. Two ids go out
on every request: the run id (`X-Correlation-Id`) answers "everything this
ticket did", the per-call id (`X-Donkey-Request-Id`) answers "which call was
this". Act 3 shows both arriving on the caught exception — `classify()` reads
them back off the failed request, so `.correlation_id` and `.call_id` are
populated with no wiring.

**Point at:** two namespaces on one span, deliberately. `gen_ai.*` follows the
OpenTelemetry GenAI conventions **pinned** to a specific version — the keys are
transcribed in the SDK rather than imported from the semconv package, whose
default drifts release to release, so what lands on a span changes only by a
reviewable edit. `donkey.*` is the stable Donkey namespace, where renaming
a key is a breaking change. Cost tags are the fixed four
(`team` / `project` / `env` / `enduser.id`), set on `from_env()` and overridable
per `run()`. They land on `donkey.cost.*` as the authoritative carrier — the
gateway has no inbound cost-tag ingestion (verified-negative). `X-Correlation-Id`
is the opposite: the gateway reads it and echoes it.

Also point at act 1: `gen_ai.prompt` / `gen_ai.completion` stay off unless
`telemetry_capture_content=True`. Spans are emitted upstream of the gateway's
PII mask, so defaulting capture on would re-export the content the platform
just masked. And act 3: a span that ends OK on a refused request makes a
dashboard say everything is fine, so refusals set `ERROR` and record
`donkey.policy.decision=refuse` with the specific `donkey.policy.type`.

Zero-config OTLP **is** shipped: `Donkey.from_env()` installs an OTLP
`BatchSpanProcessor` when `OTEL_EXPORTER_OTLP_ENDPOINT` (or
`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`) is set. No endpoint → inert and silent.
`DONKEY_TELEMETRY=false` opts out. A host `TracerProvider` is never clobbered
— this demo installs an in-memory one first so the spans can be a table, and
Donkey rides it. Cost tags, routing (`donkey.routing.*`) and cached/reasoning
usage (`donkey.usage.*`) land on the same span. The same routing/usage facts
live on `donkey.last_call` without a span backend (demo 10).

## How to run

**Local simulator by default.** The harness starts `donkey mock` on `127.0.0.1:8080`, points the SDK at it with fake credentials, and stops it afterwards. `--target live` runs the same acts against your proxy.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[llm,local,otel]"   # or: python -m pip install -e ".[full]"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=06                              # local simulator, auto-started
make demo N=06 ARGS="--target live"         # your proxy
python run.py 06                           # same thing without make
```

Live runs read three variables from your shell or a git-ignored `.env.local`
(see [Setup](../../../README.md#setup) for where the values come from):

```bash
cp .env.example .env.local     # then fill in:
# DONKEY_LLM_PROXY_URL=https://REPLACE-ME.example.invalid/REPLACE-ME/   (trailing /, no /v1)
# DONKEY_LLM_PROXY_CLIENT_ID=…
# DONKEY_LLM_PROXY_CLIENT_SECRET=…
```

**Live note:** To ship spans to a collector, export `OTEL_EXPORTER_OTLP_ENDPOINT` (and `OTEL_EXPORTER_OTLP_HEADERS` if it needs auth) before running.

**3. What you should see:**

1. Act 1: one span per call with `gen_ai.*` and `donkey.*` attributes; prompt and completion absent; `Routing and usage, on the same span`.
2. Act 2: `donkey.run(id="ticket-4417", team=…, project=…)` — three calls, one correlation id, one set of `donkey.cost.*` tags; `Two ids, two questions`.
3. Act 3: a refused call as an `ERROR` span naming the policy; `The same two ids, on the exception`.
4. Act 4: zero-config OTLP — silent without `OTEL_EXPORTER_OTLP_ENDPOINT`, exporting with it.

**4. If something goes wrong:**

- `No simulator at http://127.0.0.1:8080` — the port is taken or `[local]` is missing. Use another port: `DEMO_MOCK_URL=http://127.0.0.1:8099 make demo N=06`.
- Want the simulator in its own pane? Run `make mock` there, then `make demo N=06 ARGS="--no-autostart"`. `DEMO_QUIET_MOCK=0` shows its log.
- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §1.6`, `BG §1.7`. See [PRESENTING.md](../../../PRESENTING.md#06--telemetry).
