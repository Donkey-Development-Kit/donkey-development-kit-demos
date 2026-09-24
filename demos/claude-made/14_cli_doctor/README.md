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

Build guide: `BG §1.1` / CLI. See [PRESENTING.md](../../../PRESENTING.md#14--donkey-doctor).
