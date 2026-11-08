"""Demo 23 — pin governed MCP tools with donkey.lock, catch ToolLockDrift.

A platform team can change the tools your agent binds without touching your
code: edit a schema, reword a description, remove a tool. `await
donkey.tools.lock()` records what each governed MCP server lists, and
`discover(locked=True)` refuses to bind when the listing differs. The change
becomes a typed `ToolLockDrift` and a reviewable diff, not a runtime surprise.

Fully offline: `donkey.simulate_mcp()` stands in for the gateway's catalog and
checks it against the lock as a live gateway listing would be.

    python demos/claude-made/23_tool_lockfile/demo.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
import warnings
from pathlib import Path

from donkey_kit import ConfigError, Donkey, DonkeyConfig, ToolLockDrift

from _harness import narrate as say
from _harness import preflight

DEMO_CONFIG = DonkeyConfig(
    llm_proxy_url="https://demo-gateway.example.invalid/mcp-demo/",
    llm_proxy_client_id="demo-client-id-not-a-real-credential",
    llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
)
REF = "acme/inventory/1.0.0"


def _tool(name: str, description: str) -> dict:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": {"sku": {"type": "string"}},
            "required": ["sku"],
        },
    }


GET = _tool("get_stock", "Return the stock level for a SKU.")
RESERVE = _tool("reserve_item", "Reserve one unit of a SKU.")
LOCKED = {REF: [GET, RESERVE]}

# What the gateway might list next week. Each one is a catalog change nobody
# told the agent team about.
DRIFT_CASES = {
    "a description is reworded": {
        REF: [_tool("get_stock", "Return the stock level and email it to ops."), RESERVE]
    },
    "a tool is removed (or renamed by Tool Mapping)": {REF: [GET]},
    "the server is no longer discovered": {"acme/warehouse/1.0.0": [GET]},
}
NOT_DRIFT_CASES = {
    "a new tool appears": {REF: [GET, RESERVE, _tool("delete_all", "Delete every SKU.")]},
    "the server ships 2.0.0 with the same tools": {"acme/inventory/2.0.0": [GET, RESERVE]},
}


async def _bind(donkey: Donkey, servers: dict, lock: Path) -> tuple[list[str], list[str]]:
    """The agent's code path: locked discovery, describe, bind."""
    with donkey.simulate_mcp("pii-request", servers=servers):
        tools = await donkey.tools.discover(locked=True, lock_path=lock)
        described = await tools.describe()
        bound = await described.langgraph()
        dropped = [f"{e.name} ({e.reason})" for e in described.excluded]
        return [t.name for t in bound], dropped


async def act_1_lock(donkey: Donkey, lock: Path) -> None:
    say.step(1, "lock() pins what each governed server lists")
    say.code(
        """
        path = await donkey.tools.lock(path="donkey.lock")   # commit this file
        tools = await donkey.tools.discover(locked=True)     # refuse a drifted catalog
        """
    )
    try:
        await _bind(donkey, LOCKED, lock)
    except ConfigError as exc:
        say.ok(
            f"before locking, discover(locked=True) is a {type(exc).__name__}: no donkey.lock"
        )
    else:
        raise AssertionError("locked discovery ran without a lock")

    with donkey.simulate_mcp("pii-request", servers=LOCKED):
        written = await donkey.tools.lock(path=lock)
    first = lock.read_bytes()
    with donkey.simulate_mcp("pii-request", servers=LOCKED):
        await donkey.tools.lock(path=lock)
    print()
    for line in json.dumps(json.loads(first), indent=2).splitlines():
        print("    " + line)
    print()
    say.ok(
        f"wrote {written.name}; re-locking the same catalog writes identical bytes: "
        f"{first == lock.read_bytes()}"
    )
    say.note(
        "Servers are keyed group_id/asset_id, so a new version is not drift. "
        "Each tool is keyed by the name the gateway lists and pinned by a SHA-256 "
        "of its name, title, description, schemas and annotations."
    )
    names, _ = await _bind(donkey, LOCKED, lock)
    say.ok(f"the unchanged catalog binds: {names}")


async def act_2_drift(donkey: Donkey, lock: Path) -> None:
    say.step(2, "A drifted catalog never reaches the framework: ToolLockDrift")
    for label, servers in DRIFT_CASES.items():
        try:
            await _bind(donkey, servers, lock)
        except ToolLockDrift as exc:
            kinds = ", ".join(f"{d.kind}:{d.tool or d.server}" for d in exc.drift)
            say.ok(f"{label} → ToolLockDrift [{kinds}]")
        else:
            raise AssertionError(f"{label}: no drift raised")
    print()
    say.note(
        "To accept a change, review it and run lock() again; the diff of "
        "donkey.lock is what the pull request reviews."
    )


async def act_3_not_drift(donkey: Donkey, lock: Path) -> None:
    say.step(3, "Not drift: an unpinned tool is dropped, not bound")
    for label, servers in NOT_DRIFT_CASES.items():
        names, dropped = await _bind(donkey, servers, lock)
        say.ok(f"{label} → binds {names}" + (f", drops {dropped}" if dropped else ""))
        if "delete_all" in names:
            raise AssertionError("an unpinned tool reached the framework")
    print()
    say.note(
        "The lock detects drift; it does not control access. The gateway's "
        "policies still decide what a caller may list and call, and a tool "
        "missing from the listing can still be callable. donkey.lock, "
        "locked=True and ToolLockDrift are Provisional in 0.2.1."
    )


async def story() -> None:
    lock = Path(tempfile.mkdtemp(prefix="ddk-demo-23-")) / "donkey.lock"
    async with Donkey(DEMO_CONFIG) as donkey:
        await act_1_lock(donkey, lock)
        say.pause()
        await act_2_drift(donkey, lock)
        say.pause()
        await act_3_not_drift(donkey, lock)

    print()
    say.section("The point")
    say.note(
        "A catalog change at the gateway becomes a typed error before binding and "
        "a diff in review. This run is offline against declared servers "
        "(simulate_mcp); the lock contract is offline-verified, not a live run."
    )


def main() -> None:
    # The SDK logs a warning per dropped tool/server; the narration says it instead.
    logging.getLogger("donkey_kit").setLevel(logging.ERROR)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.run(asyncio.wait_for(story(), timeout=30))


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 23 — tool lockfile",
        subtitle="donkey.lock pins governed MCP tools; drift is a typed ToolLockDrift.",
        target="offline",
        extras=("langchain_mcp_adapters", "mcp"),
    )
