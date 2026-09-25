# 03 — budget and pacing

**Claim:** the token window is an object, not a header you parse; and you can
refuse to cross your own reserve *before* issuing the request, instead of
recovering from a 429 afterwards.

```bash
make demo N=03
```

**Needs:** nothing (`[llm]` + `[local]`).

**Five acts.** A cold process knowing nothing; the window updating in-band from
each response; `pace(reserve=0.05)` tripping `BudgetReserveReached` before the
request goes out, then `wait_for_reset()` actually sleeping until `reset_at`;
when `reset_at` is `None`, waiting returns immediately (do not spin) and an
elapsed window lets the next call through; and the terminal 429 if you do
cross it.

**Point at:** an unobserved budget reports `None` for every field, never `0` —
because `0` would be a lie that stops an agent that could have run. And
`BudgetReserveReached` is deliberately not a `PolicyViolation`: a refusal is the
gateway saying no and is terminal, this is a local signal you are expected to
recover from — **only when `reset_at` is known**. An unconditional
`wait_for_reset()` loop cannot make progress if the gateway never sent a reset.

**Two header shapes, both live-verified.** A successful 200 (with the token-rate
policy applied) carries the window as prose `x-llm-proxy-ratelimit`. The numeric
`x-token-*` trio is verified on the 429. The simulator synthesises a decreasing
window in the prose shape so pacing can be exercised locally; act 3 also observes
a crafted near-exhausted window rather than issuing the ~200 calls it would take
to drain it.

## How to run

**Local simulator by default.** The harness starts `donkey mock` on `127.0.0.1:8080`, points the SDK at it with fake credentials, and stops it afterwards. `--target live` runs the same acts against your proxy.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[llm,local]"   # or: python -m pip install -e ".[sdk]"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=03                              # local simulator, auto-started
make demo N=03 ARGS="--target live"         # your proxy
python run.py 03                           # same thing without make
```

Live runs read three variables from your shell or a git-ignored `.env.local`
(see [Setup](../../../README.md#setup) for where the values come from):

```bash
cp .env.example .env.local     # then fill in:
# DONKEY_LLM_PROXY_URL=https://REPLACE-ME.example.invalid/REPLACE-ME/   (trailing /, no /v1)
# DONKEY_LLM_PROXY_CLIENT_ID=…
# DONKEY_LLM_PROXY_CLIENT_SECRET=…
```

**Live note:** Live, the window comes from the token-rate policy; without it every budget field stays `None` and pacing never trips.

**3. What you should see:**

1. A cold budget: every field `None`, never `0`.
2. The window filling in-band from each response (`remaining`, `limit`, `fraction_used`, `reset_at`).
3. `pace(reserve=0.05)` raising `BudgetReserveReached` before the request leaves, then `wait_for_reset()` sleeping until the (crafted, short) window resets.
4. `reset_at is None`: waiting returns immediately; `An elapsed reset_at is stale` lets the next call through.
5. The terminal 429 as `TokenBudgetExceeded` if you do cross the window.

**4. If something goes wrong:**

- `No simulator at http://127.0.0.1:8080` — the port is taken or `[local]` is missing. Use another port: `DEMO_MOCK_URL=http://127.0.0.1:8099 make demo N=03`.
- Want the simulator in its own pane? Run `make mock` there, then `make demo N=03 ARGS="--no-autostart"`. `DEMO_QUIET_MOCK=0` shows its log.
- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §1.3`. See [PRESENTING.md](../../../PRESENTING.md#03--budget-and-pacing).
