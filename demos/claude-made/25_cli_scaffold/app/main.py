"""The code demo 25 scans: one MCP tool and one agent, declared in code.

`donkey scan` and `donkey scaffold` read this file statically. They never
import it, so nothing here runs. Where the MCP server is reached and how the
agent is served are deployment facts, so they are not in this file: that is
what `.donkey-kit.toml` is for, and what demo 25 builds.
"""

from __future__ import annotations

from donkey_kit import Donkey

donkey = Donkey.from_env()


@donkey.tool(server="sku-manager")
def lookup_sku(sku: str) -> dict:
    """Look up a SKU's price and stock level by its code."""
    return {}


@donkey.agent(name="support-triage", skills=["triage"])
async def triage(task):
    """Triage a support ticket and draft a reply for a human to send."""
