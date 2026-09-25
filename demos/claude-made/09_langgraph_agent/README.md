# 09 — a governed LangGraph agent

**Claim:** a real multi-step agent — the model calls two tools and composes an
answer — with governance at the boundary and nothing in the control flow.

```bash
make demo N=09          # needs real credentials
```

**To show a populated `budget`**, point this one run at `ddk-token-rate-limit`,
the only proxy that sends the token-window header. Its Azure upstream has no
`/responses` route, so switch the adapter to chat completions. Exported
variables win over `.env`, so nothing needs editing:

```bash
DONKEY_LLM_PROXY_URL=… DONKEY_LLM_PROXY_CLIENT_ID=… DONKEY_LLM_PROXY_CLIENT_SECRET=… \
DEMO_MODEL=azureopenai/gpt-5-mini DEMO_LANGGRAPH_API=chat make demo N=09
```

One run uses roughly half of that proxy's 500-token/minute window, so a second
run within the minute is likely to be refused with a 429.

**Needs:** live credentials, plus `[langgraph]` and `langchain>=1.0` (for
`create_agent`; not part of any donkey-kit extra). Without them it exits cleanly
with setup guidance; that is the expected path, not a failure.

**Why there is no offline version.** This is a real tool-calling loop, and the
simulator only replays a captured `/responses` completion — it will not decide
to call tools. The adapter itself targets the live-verified `/responses` route
(`use_responses_api=True`), the same one `donkey.openai()` uses. The refusal
path *can* be exercised offline — act 6 of [demo 04](../04_simulate_refusals/)
drives this same `ChatOpenAI` through `donkey.simulate()`.

**Point at:** the only DDK lines in the file are the one that builds the model,
`donkey.run(id=…)` around the loop, `typed_refusals()` so a proxy 403 comes
out of `astream` as `PIIDetected` rather than a framework-wrapped generic
error, and `@donkey.tool` on the two functions — a marker, not a wrapper.
And afterwards: the budget, which is the proxy's shared token window for this
client ID, filled in-band by every call in the loop (not a per-run total, and
only on a proxy that sends the header). `donkey.last_call` reads `unobserved`
here on purpose. It is scoped per asyncio task, and LangGraph makes each model
call on its own task. Demo 10 shows it populated on a direct call, and DDK #613
tracks a run-level record of every call.

**Fallback if the sandbox is down:** run [demo 08](../08_framework_objects/)
instead. It constructs real framework objects and is not a simulator, which is
what the room wants at that point in the session.

Build guide: `BG §1.8`. See [PRESENTING.md](../../../PRESENTING.md#09--langgraph-agent-live).
