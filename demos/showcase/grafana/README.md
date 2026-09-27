# Grafana + Tempo (optional)

The DDK demo shows every governed call's OpenTelemetry span **live in the UI**
already — this stack is for seeing those same spans in a real tracing backend,
exactly as they'd flow to Grafana Cloud / Tempo in production.

DDK exports over OTLP with **zero SDK-specific code** — it honours the standard
`OTEL_EXPORTER_OTLP_ENDPOINT`. The demo's backend does nothing special: if that
variable is set, DDK's export path fires alongside the in-memory viewer.

## Bring it up

```bash
cd grafana
docker compose up -d

export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_SERVICE_NAME=ddk-demo
../run.sh
```

## See the spans

1. Open Grafana → <http://localhost:3000> (anonymous admin, no login).
2. **Explore** → datasource **Tempo** → **Search** (or run TraceQL
   `{ name = "donkey.llm.chat" }`).
3. Fire any feature in the demo, then refresh. Open a trace to see the
   governance attributes on the span: `donkey.policy.decision`,
   `donkey.budget.remaining`, `donkey.cost.team` / `donkey.cost.project`,
   `donkey.correlation_id`, and `gen_ai.usage.*`. Refused calls carry
   `donkey.policy.decision=refuse` and `otel.status_code=ERROR`.

## Tear down

```bash
docker compose down
unset OTEL_EXPORTER_OTLP_ENDPOINT OTEL_SERVICE_NAME
```

Without those env vars the demo runs entirely on the in-memory exporter — no
Docker needed.

## Ports

| Port | Service |
| --- | --- |
| 3000 | Grafana UI |
| 4318 | Tempo OTLP HTTP (the export target) |
| 4317 | Tempo OTLP gRPC |
| 3200 | Tempo query API |
