"""Demo 20: descriptor fidelity and drift, with no external network."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from _harness import narrate as say
from _harness import preflight

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


async def demonstrate() -> None:
    """Assert framework schema fidelity, CI drift checks and MCP protocol reads."""
    from donkey_kit.registry.introspect import DescriptorMismatch, derive_descriptor
    from donkey_kit.registry.scan import scan

    say.step(1, "Static inventory versus the framework-owned schema")
    assert "tools" not in sys.modules
    scanned = scan(HERE / "tools.py")
    assert not scanned.issues and "tools" not in sys.modules
    descriptor = await derive_descriptor("tools:TOOLS")
    import tools

    assert tools.IMPORTED
    assert descriptor == {
        "tools": [
            {
                "name": tools.stock_count.name,
                "description": tools.stock_count.description,
                "inputSchema": tools.stock_count.tool_call_schema.model_json_schema(),
            }
        ]
    }
    say.ok("static scan did not import; auto imported and preserved the native schema")
    say.field("tool", descriptor["tools"][0]["name"])
    say.field("input schema", descriptor["tools"][0]["inputSchema"])
    say.pause()
    say.step(2, "The committed contract and deliberate schema drift")
    checked = await derive_descriptor(
        "tools:TOOLS", mode="auto:check", against=HERE / "descriptor.json"
    )
    assert checked == descriptor
    say.ok("auto:check matches the committed descriptor")
    with TemporaryDirectory(prefix="ddk-descriptor-") as directory:
        drift = json.loads(json.dumps(descriptor))
        drift["tools"][0]["inputSchema"]["properties"]["sku"]["type"] = "integer"
        against = Path(directory) / "drift.json"
        against.write_text(json.dumps(drift), encoding="utf-8")
        try:
            await derive_descriptor("tools:TOOLS", mode="auto:check", against=against)
        except DescriptorMismatch:
            say.ok("auto:check detects schema drift as DescriptorMismatch")
        else:
            raise AssertionError("schema drift was silently accepted")

    for entrypoint, error, fragment in (
        ("tools:UNSUPPORTED", TypeError, "not a framework tool"),
        ("tools:DUPLICATE_TOOLS", ValueError, "more than one tool named"),
    ):
        try:
            await derive_descriptor(entrypoint)
        except error as exc:
            assert fragment in str(exc), str(exc)
            say.field("rejected entrypoint", entrypoint)
            say.field("exception", error.__name__)
            say.ok("invalid descriptor input rejected")
        else:
            raise AssertionError(f"{entrypoint} was silently accepted")

    say.pause()
    say.step(3, "Official MCP initialize and tools/list over memory")
    protocol = await asyncio.wait_for(
        derive_descriptor("memory_server:build_server", mode="auto:live"), timeout=15
    )
    native = await derive_descriptor("memory_server:build_server")
    assert protocol == native and len(protocol["tools"]) == 1
    assert protocol["tools"][0]["name"] == "stock_count"
    assert protocol["tools"][0]["inputSchema"]["properties"]["sku"]["type"] == "string"
    say.ok("official MCP initialize/tools-list over memory preserves its tool schema")
    say.field("protocol tool", protocol["tools"][0]["name"])
    say.section("The fidelity boundary")
    say.note(
        "auto:live here means local protocol fidelity, NOT remote discovery or governed "
        "binding. auto and auto:check execute imports: use explicit, import-safe entrypoints. "
        "Static scan does not execute code and cannot claim framework schema fidelity. "
        "auto:static is not supported."
    )


def main() -> None:
    """Run the async assertions after preflight checks the optional dependencies."""
    asyncio.run(demonstrate())


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 20 - descriptor fidelity and drift",
        subtitle="Framework-owned schemas and an official MCP memory session.",
        target="offline",
        extras=("langchain_core", "mcp"),
    )
