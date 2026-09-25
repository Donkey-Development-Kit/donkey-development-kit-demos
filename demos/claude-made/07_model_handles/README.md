# 07 — model handles and honest gaps

**Claim:** the SDK refuses to invent an endpoint. This is a small demo carrying a
large point about how the whole package is built.

```bash
make demo N=07
```

**Needs:** nothing at all.

**Three acts.** `resolve()` returning local, explicitly heuristic capability
handles; `list_models(live=True)` raising a `ConfigError` that explains the
verified absence of a catalog endpoint; and config validation reporting every
missing field at once rather than one per run. Act 3 also points at
`donkey doctor` — the CLI that tells wrong URL from wrong credentials from
model-not-allowed, reusing the same remediation strings. Demo 14 runs it
against the local simulator.

**Point at:** `GET /models` returns 404 — verified against a real gateway, not
assumed — because model-based routing only routes requests that already carry
`model` in the body. The SDK could have guessed a path or shipped a list that
goes stale. A fabricated endpoint that 404s in a customer's sandbox costs more
trust than the missing feature ever would.

Good filler if you are ahead of time; safe to cut if behind.

## How to run

**Offline.** No gateway, no simulator, no credentials. `--target` is ignored.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[llm]"   # or: python -m pip install -e ".[sdk]"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=07
python run.py 07                           # same thing without make
```

**3. What you should see:**

1. Act 1: `resolve()` returning local, explicitly heuristic capability handles.
2. Act 2: `list_models(live=True)` raising a `ConfigError` that explains why there is no catalog endpoint (`GET /models` is a verified 404).
3. Act 3: config validation naming every missing field at once, and a pointer to `donkey doctor` (demo 14).

**4. If something goes wrong:**

- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §1.1`. See [PRESENTING.md](../../../PRESENTING.md#07--model-handles).
