# 09 — a governed LangGraph agent

**Claim:** a real multi-step agent — the model calls two tools and composes an
answer — with governance at the boundary and nothing in the control flow.

```bash
make demo N=09          # needs real credentials
```

**Needs:** live credentials, plus `[langgraph]`. Without them it exits cleanly
with setup guidance; that is the expected path, not a failure.

**Why there is no offline version.** LangChain's `ChatOpenAI` talks to
`/chat/completions`. The local simulator serves `/responses` and the captured
404, and deliberately does not implement a route it has never captured. The
refusal path *can* be exercised offline — act 6 of [demo 04](../04_simulate_refusals/)
drives this same `ChatOpenAI` through `donkey.simulate()`.

**Point at:** the only DDK line in the file is the one that builds the
model; everything else is ordinary LangGraph. And the budget afterwards — several
model calls in one agent loop through one transport, so the number is the run's
real consumption and one correlation id ties the whole loop together.

**Fallback if the sandbox is down:** run [demo 08](../08_framework_objects/)
instead. It constructs real framework objects and is not a simulator, which is
what the room wants at that point in the session.

Build guide: `BG §1.8`. See [PRESENTING.md](../../../PRESENTING.md#09--langgraph-agent-live).
