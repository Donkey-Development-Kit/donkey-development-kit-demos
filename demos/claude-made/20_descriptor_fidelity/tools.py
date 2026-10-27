"""Import-safe, framework-owned tool definitions; no clients or credentials."""

from langchain_core.tools import tool

# Importing this module executes this assignment. Static scan must not do so.
IMPORTED = True


@tool
def stock_count(sku: str, warehouse: str = "main") -> int:
    """Return the offline stock count for a SKU at a warehouse."""
    return 12


TOOLS = [stock_count]
DUPLICATE_TOOLS = [stock_count, stock_count]
UNSUPPORTED = {"not_a_tool": True}
