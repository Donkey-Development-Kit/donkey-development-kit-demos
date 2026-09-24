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

Build guide: `BG §2.7`. See [PRESENTING.md](../../../PRESENTING.md#12--toolsetfilter).
