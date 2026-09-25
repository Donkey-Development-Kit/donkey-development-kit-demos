# 05 — the conformance suite

**Claim:** four questions a team usually cannot answer about its own agent,
answered without reading its code.

```bash
make demo N=05
```

**Needs:** nothing (`[test]` + `[llm]`).

**What it grades.** Does the agent retry a budget refusal (it must not)? Does a
typed refusal survive its error handling? Does the run's correlation id reach its
logs? Does it still work when the gateway sends no budget headers? It answers by
swapping a fixture-serving transport underneath, calling `agent.run(...)`, and
watching the wire and the logs — so it grades behaviour, in any framework.

**Files here.** `shipping_agent.py` holds `NaiveAgent` (written the way people
actually write them) and `GovernedAgent` (the same agent after the findings).
`exemptions.py` holds one real exemption and two deliberately broken ones.

**Four acts.** Three failures against the naive agent; what each finding means;
four passes against the fixed one; then exemptions — one asserted correctly, then
a typo'd scenario name and an empty reason, both of which fail the run at
collection time.

**Point at:** an exemption is an asserted claim with a published reason, never a
silent skip. There is deliberately no `KNOWN_LIMITATIONS` in `shipping_agent.py`,
because the plugin auto-discovers one next to the factory and it would have
quietly excused a scenario the demo needs to fail.

**This is the deliverable** — the internal adapter matrix is ours, this suite is
theirs, and it runs in their CI. `donkey test --agent=my_app.agent:build` is
the same front-end: it execs `pytest --donkey-conformance` and returns pytest's
exit code. For an agent that never imports `donkey_kit`, the `gateway` fixture
in demo 04 is the other entry point.

## How to run

**Offline.** No gateway, no simulator, no credentials. `--target` is ignored.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[llm,test]"   # or: python -m pip install -e ".[sdk]"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=05
python run.py 05                           # same thing without make
```

**3. What you should see:**

1. Three conformance failures against `NaiveAgent` (budget retry, swallowed refusal, lost correlation id).
2. `What each failure actually means`.
3. Four passes against `GovernedAgent`.
4. Exemptions: one asserted correctly, then a typo'd scenario and an empty reason both failing at collection.

**4. If something goes wrong:**

- A warning about the `pytest11` entry point is harmless: the demo loads the plugin by module. Reinstall the SDK editable to clear it.
- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §1.5`. See [PRESENTING.md](../../../PRESENTING.md#05--conformance).
