# 21 - Local A2A Serving

Issue #55, `BG §2.9.1`: an `@donkey.agent` handler becomes an official
`a2a-sdk` app, with governed inbound tasks and downstream model spans.

```bash
.venv/bin/python demos/claude-made/21_a2a_serving/demo.py
```

Needs SDK `[llm,local,test,otel,a2a]`. Run as a fresh process because the demo
owns its global in-memory OTel provider. It does not read SDK config, dotenv
files or real secrets; it clears inherited `OTEL_*` settings. Synthetic
credentials are never printed.

Offline `_harness.preflight.cli` checks missing extras before lazy optional
imports, prints masking/run context and contains errors without loading dotenv.
Four narrated acts cover card discovery, refusal/recovery, trace relationships
and shutdown; `DEMO_PAUSE=1` supports a live presentation of this local story.

## Local Boundary

This uses `donkey_kit.a2a.build_app()`, the same official-SDK server that
`donkey.serve(handler)` runs with uvicorn. The caller uses `httpx.ASGITransport`
inside the application's **ASGI lifespan**. There is no TCP listener and no
claim that a real port or `Donkey.serve()`'s blocking uvicorn launcher was tested.
The documented A2A 1.0 request uses `A2A-Version: 1.0`, JSON-RPC `SendMessage`,
`ROLE_USER`, and text parts. The wire shape follows SDK `test_a2a_serve.py`.
The demo does not implement its own A2A protocol/task lifecycle.

## Assertions

- Fetch `/.well-known/agent-card.json`; assert the generated name, description,
  skill and protocol version from the decorator.
- Send success, refusal and another success through the **same** app/lifespan.
  Success returns a completed task with a text artifact.
- Adopt two supplied correlation IDs and mint one when absent. Assert each
  governed downstream request carries its inbound task's ID.
- A synthetic downstream 403 is classified as `PIIDetected`; the failed task
  carries type, refusal flag, correlation ID and call ID, without the internal
  error message or traceback. The server remains usable after this failure.
- Three SERVER task spans parent three downstream model spans in matching
  traces. Refusal spans are ERROR; error messages, prompts and completions do
  not leak into task replies/spans.
- Exit lifespan and assert no new asyncio task workers remain **before**
  `asyncio.run()` could cancel them. Close the Donkey transport and explicitly
  flush/shut down the host-owned OTel provider.

The model transport is an in-process `httpx.MockTransport` installed through
the SDK's dev-only `_testing` seam, not a real gateway/provider. No private
telemetry internals are patched. Reference: SDK `test_a2a_governed_inbound.py`.

Gateway exposure, `donkey expose`, and `donkey dev` remain outside implemented
scope. These local assertions do not change any live verification status.

With `a2a-sdk` 1.2.3 the official dispatcher emits `Dispatcher task was cancelled
or finished. Events may be lost.` and `Dispatcher task is not running. Cannot
wait for event dispatch.` at shutdown. The demo does not suppress those warnings;
it independently asserts completed/failed task results and no worker leaks. It
does not prove streaming-event delivery (the generated card advertises no
streaming support).
