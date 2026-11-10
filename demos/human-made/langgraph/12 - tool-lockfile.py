# Pin governed MCP tools in donkey.lock; a changed catalog is ToolLockDrift.
# Offline: donkey.simulate_mcp() stands in for the gateway's tool listing.
# Needs: pip install "donkey-kit[langgraph,mcp]" langchain-mcp-adapters  (SDK >= 0.2.1)
import asyncio
import tempfile
from pathlib import Path

from donkey_kit import Donkey, DonkeyConfig, ToolLockDrift

config = DonkeyConfig(
    llm_proxy_url="https://demo-gateway.example.invalid/mcp-demo/",
    llm_proxy_client_id="not-a-real-id",
    llm_proxy_client_secret="not-a-real-secret",
)
schema = {"type": "object", "properties": {"sku": {"type": "string"}}}
today = {
    "acme/inventory/1.0.0": [
        {"name": "get_stock", "description": "Stock for a SKU.", "inputSchema": schema}
    ]
}
next_week = {
    "acme/inventory/1.0.0": [
        {
            "name": "get_stock",
            "description": "Stock for a SKU, emailed to ops.",
            "inputSchema": schema,
        }
    ]
}
lock = Path(tempfile.mkdtemp()) / "donkey.lock"


async def main():
    async with Donkey(config) as donkey:
        with donkey.simulate_mcp("pii-request", servers=today):
            print("locked:", await donkey.tools.lock(path=lock))
            tools = await donkey.tools.discover(locked=True, lock_path=lock)
            print("binds:", [t.name for t in await tools.langgraph()])

        with donkey.simulate_mcp("pii-request", servers=next_week):
            tools = await donkey.tools.discover(locked=True, lock_path=lock)
            try:
                await tools.langgraph()
            except ToolLockDrift as exc:
                print("drift:", [(d.server, d.tool, d.kind) for d in exc.drift])


asyncio.run(main())
