# 12 — ToolSet.filter

**Claim:** filtering MCP tools is shipped and pure. Binding them into a
framework is not, and the SDK says so.

```bash
make demo N=12
```

**Needs:** nothing at all. No gateway, no simulator, no MCP session — the
handles are constructed in-process with obviously-fake endpoints.

**Two acts.** `ToolSet.filter(allow=…)` / `deny=…` each return a new ToolSet;
the parent `name_map` is unchanged, and colliding `get_employee` names are
prefixed `hr__get_employee`. Then `tools.langgraph()` raises `blocked on
verification` because Exchange / MCP Bridge class names are unconfirmed.

**Point at:** this is not `@donkey.tool` (demo 01). That marker records a
Python callable. This filters descriptors from MCP server handles.

## How to run

**Offline.** No gateway, no simulator, no credentials. `--target` is ignored.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=12
python run.py 12                           # same thing without make
```

**3. What you should see:**

1. `ToolSet.filter(allow=…)` and `deny=…` returning new sets; the parent `name_map` unchanged; `hr__get_employee` prefixing.
2. `tools.langgraph()` raising `blocked on verification`.

**4. If something goes wrong:**

- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §2.7`. See [PRESENTING.md](../../../PRESENTING.md#12--toolsetfilter).
