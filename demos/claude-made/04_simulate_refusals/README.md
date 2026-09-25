# 04 — simulating refusals in-process

**Claim:** the `except PIIDetected:` branch in your agent has never executed, and
this is how it gets to.

```bash
make demo N=04
```

**Needs:** nothing (`[llm]` + `[local]`). The LangGraph act runs only if
`[langgraph]` is installed and is skipped silently otherwise.

**Eight acts.** The happy path being all you normally exercise; one context
manager running the refusal branch; each refusal type in one line (PII, token
budget, prompt-injection, Azure content-safety); `times=` counting calls and
normal service resuming; what `simulate()` actually injects versus what it
refuses to fake (`ToolInvocationError`, `GatewayUnavailable`); the same
injection working through LangChain's own `ChatOpenAI`; `donkey mock --scenario`
scripting the running simulator; and `start_gateway()` — a real port, a stock
httpx client, `requests_received`, and a spy that redacts `client_secret`.

**Point at:** `donkey.simulate(ContentSafetyBlocked)` injecting the
live-captured Azure content-safety fixture — the branch runs, categories and
all. Then `simulate(PromptInjectionBlocked)`: that maps to the documented
`injection-protection` representative (`x-injection-protection: blocked`),
**not** the live-verified regex-prompt-guard. Walk regex in demo 02;
`simulate()` picks one fixture per exception type. Then act 5's last beats,
where `ToolInvocationError` still raises `ValueError`: that is not a gateway
refusal and has no captured wire shape, so injecting a plausible body would let
you write a handler against a body that does not exist. `GatewayUnavailable` is
the same refusal-to-fake for a different reason: there is no HTTP response, so
there is nothing to replay. And act 6 — the
injection sits on the transport, which is why it reaches a framework object the
SDK does not wrap. Act 7 is the other half: `donkey mock --scenario` scripts
the running simulator (PII every Nth call, injection on a substring, a real
wall-clock budget window) so a stock client with no SDK in the process sees
the same fixtures. Act 8 is that idea as a pytest-shaped object:
`start_gateway()` binds an ephemeral port; `set_scenarios("pii_block:every=1")`
arms it live; the spy records the request with `client_secret` already `***`.

**Why it matters:** this needs no gateway, so it belongs in your unit tests
rather than in a manual pre-release checklist.

## How to run

**Local simulator by default.** The harness starts `donkey mock` on `127.0.0.1:8080`, points the SDK at it with fake credentials, and stops it afterwards. `--target live` runs the same acts against your proxy.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[llm,local]"   # or: python -m pip install -e ".[sdk]"
make doctor                    # what is installed; prints no secrets
```

Optional: `[langgraph]` adds act 6; it is skipped silently otherwise.

**2. Run it:**

```bash
make demo N=04                              # local simulator, auto-started
make demo N=04 ARGS="--target live"         # your proxy
python run.py 04                           # same thing without make
```

Live runs read three variables from your shell or a git-ignored `.env.local`
(see [Setup](../../../README.md#setup) for where the values come from):

```bash
cp .env.example .env.local     # then fill in:
# DONKEY_LLM_PROXY_URL=https://REPLACE-ME.example.invalid/REPLACE-ME/   (trailing /, no /v1)
# DONKEY_LLM_PROXY_CLIENT_ID=…
# DONKEY_LLM_PROXY_CLIENT_SECRET=…
```

**3. What you should see:**

1. Acts 1–4: the happy path, then `donkey.simulate(PIIDetected)` running the `except` branch, each refusal type, and `times=`.
2. Act 5: `ToolInvocationError` and `GatewayUnavailable` refused with `ValueError` — no captured wire shape to replay.
3. Act 6: the same injection reaching LangChain's `ChatOpenAI` (only with `[langgraph]`).
4. Act 7: `donkey mock --scenario` specs parsed and explained (the command is printed, not run).
5. Act 8: `start_gateway()` on an ephemeral port, `requests_received`, and a spy with `client_secret` already `***`.

**4. If something goes wrong:**

- `No simulator at http://127.0.0.1:8080` — the port is taken or `[local]` is missing. Use another port: `DEMO_MOCK_URL=http://127.0.0.1:8099 make demo N=04`.
- Want the simulator in its own pane? Run `make mock` there, then `make demo N=04 ARGS="--no-autostart"`. `DEMO_QUIET_MOCK=0` shows its log.
- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §1.5`. See [PRESENTING.md](../../../PRESENTING.md#04--simulate).
