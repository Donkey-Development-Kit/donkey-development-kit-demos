# 09 — a governed LangGraph agent

**Claim:** a real multi-step agent — the model calls two tools and composes an
answer — with governance at the boundary and nothing in the control flow.

```bash
make demo N=09          # needs real credentials
```

**Needs:** live credentials, plus `[langgraph]`. Without them it exits cleanly
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
And afterwards: the budget (the run's real consumption) and
`donkey.last_call` on the most recent model call.

**Fallback if the sandbox is down:** run [demo 08](../08_framework_objects/)
instead. It constructs real framework objects and is not a simulator, which is
what the room wants at that point in the session.

Build guide: `BG §1.8`. See [PRESENTING.md](../../../PRESENTING.md#09--langgraph-agent-live).
