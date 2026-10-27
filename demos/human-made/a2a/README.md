# Local A2A Blocking Launcher

Issue #55: this straight-line example calls the actual **blocking**
`donkey.serve()` facade, which runs the official `a2a-sdk` app with uvicorn
on `127.0.0.1`. Unlike narrative demo 21's ASGI transport, verification here
crosses a real local TCP socket.

```bash
.venv/bin/python "demos/human-made/a2a/01 - serve.py" --port 8000
# Ctrl-C drains server lifespan and returns from donkey.serve().

.venv/bin/python demos/human-made/a2a/verify.py
# Or select a known free port:
.venv/bin/python demos/human-made/a2a/verify.py --port 8099
```

Requires `donkey-kit[a2a]` (including starlette and uvicorn). Both scripts parse
arguments and check optional prerequisites before importing their dependencies.
No dotenv/config files, real secrets, authentication, provider calls or external
collectors are used. `DonkeyConfig(telemetry=False)` is explicit, not resolved
from environment or disk.

## What Is Verified

- Start the real example as a subprocess using the verifier's Python interpreter.
  Its environment allowlist excludes inherited proxies, OTEL settings and DDK /
  Anypoint credentials; the loopback HTTP client also uses `trust_env=False`.
- Poll card readiness for at most ten seconds, with one-second HTTP timeouts.
  Assert generated name, version, skill, advertised loopback URL and A2A 1.0.
- Send documented A2A 1.0 JSON-RPC `SendMessage` requests over TCP: completed
  task, failed `PIIDetected` task, and completed recovery task on the same server.
- Assert adopted/minted correlation IDs and no internal refusal message or
  traceback in the caller's task. The refusal is **directly synthetic in the
  handler**, not a claim of downstream gateway enforcement. The deterministic
  success path makes no model call.
- Confirm the process remains blocking after requests. SIGINT requests graceful
  uvicorn shutdown; assert lifespan completion, facade return, transport cleanup,
  child exit zero within five seconds and a no-longer-reachable listener.
  A failure path also requests shutdown; a stuck child is forcibly killed and
  reaped as a last resort. Such cleanup does not count as successful verification.

Default port selection binds a temporary loopback socket to port zero and then
releases it before launch. There is a small allocation race; a conflicting
process causes a bounded startup failure, not a silent pass. Use `--port` when
coordinating a known port. Raw server logs are captured, not printed, because
the official server logs operator-only exception detail.

Narrative demo 21 independently verifies task/downstream trace parenting,
sanitized downstream refusals, and task-worker drainage via ASGI lifespan with
an isolated in-memory OTel provider. No gateway exposure, `donkey expose`,
`donkey dev`, deployment or live verification status is changed by either demo.
