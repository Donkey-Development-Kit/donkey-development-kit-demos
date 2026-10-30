"""The MCP server demo 16 publishes: one tool, declared in code.

`donkey publish` reads this file statically. It never imports it, so nothing
here runs in CI.
"""

from __future__ import annotations

from donkey_kit import Donkey

donkey = Donkey.from_env()


@donkey.tool(server="ddk-demo-sku-lookup")
def lookup_sku(sku: str) -> dict:
    """Look up a product by its SKU: name, price and stock level."""
    return {"sku": sku, "name": "Demo widget", "price": 9.99, "in_stock": 12}
