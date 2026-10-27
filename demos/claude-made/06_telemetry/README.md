# 06 - Cross-Hop Telemetry and Flush Ownership

Local-only assertions for issue #58, `BG §1.6` and `BG §1.7`. Run in a fresh
process from the demos repo:

```bash
.venv/bin/python demos/claude-made/06_telemetry/demo.py
```

Needs the SDK `[llm,local,test,cli,otel]` extras. No config files, dotenv files,
real credentials or external collectors are read. The script discards inherited
`OTEL_*` settings in its own process and explicitly configures synthetic consumer
credentials. It does not support a live mode.

Offline `_harness.preflight.cli` prints the run context and masking status,
checks optional dependencies before lazy imports, and contains errors. The six
narrated acts use projector-friendly headings and `DEMO_PAUSE=1` pauses.

## What Is Asserted

- Without an endpoint, bootstrap stays inert and flush succeeds as a no-op.
  With the explicitly local endpoint, one call produces a `donkey.llm.chat`
  span. Tables show pinned GenAI model/usage attributes, synthetic routing
  fallback, and cached/cache-write/reasoning token counts without content.
- Three calls in `run(id="ticket-4417", team="support", project="triage")`
  share a business ID and override team/project while inheriting env. Each call
  has its own call ID. This reproduces the original run/cost narrative.
- `run_from_headers()` adopts a valid incoming ID and replaces a malformed ID
  with a fresh 32-character hex ID. Both travel on the governed model request.
- `correlation_headers()` is explicitly passed to a **plain HTTP hop** on a
  separate `httpx.AsyncClient`; the hop gets the ID, not consumer credentials.
  The hop is a MockTransport stand-in, not a working Exchange/MCP binding.
- Two concurrently interleaved `run(business_group=...)` scopes stay isolated;
  leaving them restores the outer attribution, then the configured default.
  The SDK's business-group header name is still an **unverified placeholder**.
  Observing it locally does not verify gateway ingestion or authorization.
- Eleven real OTLP/protobuf spans reach a loopback HTTP receiver (four original
  capability demonstrations, then seven cross-hop/refusal spans). The model calls
  themselves use MockTransport and the refusal uses public `donkey.simulate()`.
  Spans carry adopted/minted provenance, a refusal has ERROR status, and prompt
  and completion attributes remain absent. No caller-supplied cost claims are
  adopted from inbound headers or printed.
- `await asyncio.to_thread(donkey.flush_telemetry, timeout_s=2.0)` returns `True`
  and delivers queued DDK-owned spans before the receiver is stopped. A local
  elapsed-time assertion allows one second of scheduling overhead. This is not
  a hard real-time or remote-collector failure benchmark.
- A host-owned batched provider installed later receives subsequent DDK spans.
  DDK's flush does **not** flush that host queue; the host explicitly calls its
  own `force_flush()` and `shutdown()`.

## Ownership Matters

DDK's OTLP provider is process-wide, not per `Donkey` instance. It is scoped by
default and does not take the global provider. A host provider wins, even if
installed later. `flush_telemetry()` flushes only the DDK-owned provider; `True`
also means success/no-op when DDK owns no provider. `False` means a timeout or
export failure, not successful delivery. Exporter retry/socket timeouts also
matter; configure them for the application's shutdown budget. The call blocks,
so async applications should offload it with `asyncio.to_thread`.

The receiver is a minimal real local OTLP sink, not a production collector or
dashboard. Shutdown closes its port and joins its thread. Assertions fail the
script rather than printing a success-looking warning. SDK APIs used here are
covered by `test_inbound_correlation.py`, `test_per_request_business_group.py`
and `test_otlp_export.py` in the read-only SDK checkout.
