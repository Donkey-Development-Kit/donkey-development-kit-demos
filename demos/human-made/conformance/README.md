# Conformance - Compact Pytest Example

`agent.py` is a small customer-style agent: build its client from the Donkey
injected into `build`, log the correlation ID, and surface typed refusals without
retrying. Needs SDK develop with `donkey-kit[llm,test,local]`.

## Credential-Free Verification

From the demos root:

```bash
.venv/bin/python demos/human-made/conformance/verify.py
```

This runs three ordinary tests plus the public plugin in both modes, asserts exit
0 for each subprocess, and prints their reports. It uses an empty HOME, XDG config
and working directory, exposing only this folder on PYTHONPATH. It does not read
dotenv, user credentials or project SDK configuration. No external network.

## Customer Commands

From this folder in an activated environment:

```bash
python -m pytest -q test_agent.py
python -m pytest --donkey-conformance --donkey-agent=agent:build --donkey-mode=in-process
python -m pytest --donkey-conformance --donkey-agent=agent:build --donkey-mode=server
```

Ordinary tests expect `3 passed`, exit 0. Each plugin invocation expects four
scenario passes, exit 0. A scenario failure exits 1; invalid plugin usage or
missing server-mode extras exits 4. `--donkey-conformance` replaces ordinary test
collection, so the plugin commands do not run `test_agent.py` as well.
Use `verify.py` when you need the explicit configuration isolation above.

`test_agent.py` asserts all four verdicts in each mode, then makes one real HTTP
request to the local simulator, asserts typed `PIIDetected` and a server log
count of exactly one, closes in `finally` and asserts that the port no longer
accepts connections. Server mode uses ephemeral loopback HTTP and counts retries
from the request log, leaving the SDK transport untouched. In-process mode swaps
a counting fixture transport and needs no socket. These are simulator checks,
not live gateway evidence or client-side governance.

Custom `classify.register()` refusal shapes without simulator captures require
in-process mode. For the deliberately naive agent (three findings, exit 1),
matching cross-mode details and exemption usage errors, see
[`../../claude-made/05_conformance`](../../claude-made/05_conformance/README.md).
