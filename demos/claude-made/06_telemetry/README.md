# 06 — OTel GenAI spans and correlation ids

**Claim:** standard GenAI telemetry and one trace per logical run, with no
instrumentation code in the agent.

```bash
pip install "donkey-kit[otel]"
make demo N=06
```

**Needs:** `[otel]` on top of `[llm]` + `[local]`. Without it the demo prints the
install command and exits cleanly.

**Three acts.** One call producing one span with both attribute namespaces, and
prompt/completion **absent** unless you opt in; `donkey.run(id=…, team=…,
project=…)` giving three calls one correlation id and one set of `donkey.cost.*`
tags; and a refused call producing an `ERROR` span that names the policy.

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
per `run()`.

Also point at act 1: `gen_ai.prompt` / `gen_ai.completion` stay off unless
`telemetry_capture_content=True`. Spans are emitted upstream of the gateway's
PII mask, so defaulting capture on would re-export the content the platform
just masked. And act 3: a span that ends OK on a refused request makes a
dashboard say everything is fine, so refusals set `ERROR` and record
`donkey.policy.decision=refuse` with the specific `donkey.policy.type`.

**Not shipped yet:** zero-config OTLP export. Cost tags *are* shipped.

Build guide: `BG §1.6`, `BG §1.7`. See [PRESENTING.md](../../../PRESENTING.md#06--telemetry).
