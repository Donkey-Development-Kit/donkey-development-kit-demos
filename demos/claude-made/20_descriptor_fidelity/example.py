"""Compact descriptor/check example: run directly with the demo's environment."""

import asyncio
from pathlib import Path

from donkey_kit.registry.introspect import derive_descriptor


async def main() -> None:
    """Compare a real tool's descriptor to the committed model-facing schema."""
    descriptor = await derive_descriptor("tools:TOOLS")
    checked = await derive_descriptor(
        "tools:TOOLS",
        mode="auto:check",
        against=Path(__file__).with_name("descriptor.json"),
    )
    assert checked == descriptor
    print("PASS: committed descriptor matches the framework-owned schema")


if __name__ == "__main__":
    asyncio.run(main())
