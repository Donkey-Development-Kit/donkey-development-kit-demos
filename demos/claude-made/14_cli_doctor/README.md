# 14 — donkey doctor

**Claim:** "it doesn't work" is three failures that look identical from the
outside. `donkey doctor` makes one governed call and reads it through the typed
taxonomy, so the CLI and the exceptions never disagree about the next step.

```bash
make demo N=14
```

**Needs:** `[cli]` + `[llm]` + `[local]`. Offline — incomplete config needs no
network; the happy probe hits `start_gateway()`; the dead-origin act points at
`127.0.0.1:9`.

**Three acts.** Missing `DONKEY_LLM_PROXY_*` exits 1 and names every gap.
Pointed at the local simulator, gateway and credentials come back `[ok]` and
the budget line states how stale the reading is. A closed local port is
`GatewayUnavailable`: credentials stay `[--]`, not an `AuthError`.

**Point at:** this is not `make doctor` in this repo (install/env probe). Do
not confuse the two.

## How to run

**Offline.** No gateway, no simulator, no credentials. `--target` is ignored.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[llm,local,cli]"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=14
python run.py 14                           # same thing without make
```

**3. What you should see:**

1. Incomplete config: `donkey doctor` exits 1 and names every gap.
2. Against `start_gateway()`: gateway and credentials `[ok]`, plus how stale the budget reading is.
3. A closed port: `GatewayUnavailable`, credentials `[--]` — not an `AuthError`.

**4. If something goes wrong:**

- This is the SDK's `donkey doctor`, not this repo's `make doctor` (install and env probe).
- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §1.1` / CLI. See [PRESENTING.md](../../../PRESENTING.md#14--donkey-doctor).
