# 23 — tool lockfile

**Claim:** `await donkey.tools.lock()` pins what each governed MCP server lists
in a `donkey.lock`. A later `discover(locked=True)` refuses to bind a changed
catalog with a typed `ToolLockDrift`, before the framework sees a tool.

```bash
make demo N=23
```

**Needs:** `donkey-kit[langgraph,mcp]` and `langchain-mcp-adapters`, SDK 0.2.1
or later. No gateway, no Exchange, no credentials: `donkey.simulate_mcp()`
supplies the catalog, and locked discovery checks it as it would at a gateway.

**Three acts.**

1. Locked discovery without a lock is a `ConfigError`. `lock()` writes sorted
   JSON (servers keyed `group_id/asset_id`, tools pinned by SHA-256), and
   re-locking an unchanged catalog writes identical bytes.
2. Drift raises `ToolLockDrift`: a reworded description (`changed`), a removed
   tool (`tool_missing`), and a server no longer discovered (`server_missing`).
3. Not drift: a new tool is dropped and shows in `ToolSet.excluded` with
   `reason="unpinned"`, and a new server version with the same tools binds.

**Point at:** commit `donkey.lock`. Accepting a catalog change means re-running
`lock()`, and the reviewable diff is that file.

**Boundary.** The lock detects drift; it does not control access. The gateway's
policies still decide what a caller may list and call. `donkey.lock`,
`locked=True` and `ToolLockDrift` are **Provisional** in 0.2.1, and the SDK docs
mark the contract offline-verified. This demo uses declared servers, not a live
gateway listing.

## How to run

```bash
python -m pip install -e "../donkey-development-kit/python[langgraph,mcp]" langchain-mcp-adapters
make demo N=23
```

**What you should see:** the printed lock, then eight `PASS` lines.

**If something goes wrong:**

- `Missing prerequisites`: install the line above.
- `AttributeError` on `lock` or `simulate_mcp`, or `NotImplementedError`: your SDK is older than 0.2.1.
- `The demo raised`: re-run with `DEMO_TRACEBACK=1`.

Docs: [Pinning & lockfile](https://docs.donkey-kit.dev/tool-access/lockfile).
Build guide: `BG §2.7`. See [PRESENTING.md](../../../PRESENTING.md#23---tool-lockfile).
