"""Official MCP SDK server, accessed only through its in-memory protocol."""


def build_server():
    """Import the optional official SDK only when derivation calls this factory."""
    try:
        from mcp.server import MCPServer
    except ImportError:
        # Official SDK 1.x spells the server FastMCP; 2.x spells it MCPServer.
        from mcp.server.fastmcp import FastMCP as MCPServer

    server = MCPServer("offline-stock")

    @server.tool()
    def stock_count(sku: str, warehouse: str = "main") -> int:
        """Return the offline stock count for a SKU at a warehouse."""
        return 12

    return server
