# 22 — typed MCP tool refusals

**Claim:** an Omni Gateway refusal on an MCP tool call raises the same typed
error as on a model call. `donkey.simulate_mcp()` replays the gateway's captured
refusal into your real binding offline, with no gateway, no Exchange and no
credentials.

```bash
make demo N=22
```

**Needs:** `donkey-kit[langgraph,mcp]` and `langchain-mcp-adapters`. No gateway,
no simulator, no credentials. SDK 0.2.1 or later.

**Three acts.**

1. `pii-request` and `pii-response-sse` raise `PIIDetected` (request and response
   phase) out of a native LangChain tool from `tools.langgraph()`. With `times=1`,
   the next call in the same block is answered by the offline baseline.
2. `abac-denied` and `global-access` raise `ToolNotInProfile`, with the tool
   name taken from the gateway's reply.
3. `schema-invalid-args` and `poisoning-block-list` stay generic (`McpError`,
   `ToolInvocationError`). The demo asserts they are **not** guessed as a
   `PolicyViolation`.

**Point at:** inside the block, `donkey.tools.discover()` returns the declared
servers, so the agent's own discover → bind → call code runs unchanged. The
model client is untouched; combine with `donkey.simulate(...)` for that.

**Boundary.** These are packaged Omni Gateway captures, replayed with
`x-donkey-simulator: true` and reserialized (not byte-verbatim). They are not
live gateway evidence. The injection matches the RPC method, not the tool, so a
captured diagnostic can name a different tool (`calculate`, `current_time`).
ADK and CrewAI bindings are refused by `simulate_mcp()`.

## How to run

**Offline.** `--target` is ignored.

```bash
python -m pip install -e "../donkey-development-kit/python[langgraph,mcp]" langchain-mcp-adapters
make demo N=22
```

**What you should see:** six `PASS` lines, two per act, and two baseline
results after the PII blocks.

**If something goes wrong:**

- `Missing prerequisites`: install the line above. The demo exits 0 without running.
- `AttributeError: simulate_mcp`: your SDK checkout is older than 0.2.1.
- `The demo raised`: re-run with `DEMO_TRACEBACK=1`.

Docs: [Simulator: MCP](https://docs.donkey-kit.dev/simulator),
[MCP gateway policies](https://docs.donkey-kit.dev/tool-access/gateway-policies).
Build guide: `BG §1.5`. See [PRESENTING.md](../../../PRESENTING.md#22---typed-mcp-tool-refusals).
