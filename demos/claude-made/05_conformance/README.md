# 05 - Conformance In Two Modes

Four behavioral questions, answered without reading the agent's code: does it
retry a terminal budget refusal, lose the PII refusal type, lose the correlation
ID in logs, or fail when budget headers are absent?

## Run

Needs SDK develop with `donkey-kit[llm,test,local]`. From the demos root:

```bash
.venv/bin/python demos/claude-made/05_conformance/demo.py
.venv/bin/python run.py 05
```

No credentials or external network. Each pytest subprocess gets an empty HOME,
XDG config and working directory, without ambient SDK, Anypoint or telemetry
configuration. The entrypoint deliberately bypasses the demo harness's implicit
dotenv loading. The public pytest plugin must be registered by the SDK install.

## What Is Asserted

`shipping_agent.py` defines `NaiveAgent` and the corrected `GovernedAgent`.
The demo invokes the real public plugin in **both** modes and asserts:

- Naive: one pass, three failures; pytest exit 1.
- Corrected: four passes, zero failures; pytest exit 0.
- The four scenario verdicts and their detail strings match across modes.
- The asserted exemption produces one pass, two failures, one exempt; exit 1.
- A misspelled exemption or empty reason produces a collection usage error; exit 4.

`exemptions.py` supplies the illustrative asserted limitation and invalid examples.
The actual agents deliberately declare no auto-discovered `KNOWN_LIMITATIONS`.
The script exits nonzero if a count, exit status, row or cross-mode comparison
does not match. Expected naive pytest failures do not fail the enclosing demo.

## Observation Boundary

In-process mode replaces the Donkey transport with a counting fixture responder.
Server mode leaves the SDK transport untouched, starts the local simulator on an
ephemeral `127.0.0.1` port and uses real loopback HTTP. Retry observation comes
from the simulator request log, not an in-process transport counter. The harness
closes the server in `finally`, including failed runs; scenario state is reset.
These captured, simulator-stamped responses are not live gateway verification or
client-side policy enforcement.

Custom `classify.register()` refusal shapes **without simulator captures require
in-process mode**. Server mode cannot replay an uncaptured custom shape.

For a small standalone agent, the exact
`pytest --donkey-conformance --donkey-mode=server` command, ordinary pytest
assertions on the server log and port cleanup, see
[`../../human-made/conformance`](../../human-made/conformance/README.md).

Build guide: `BG §1.5`.
