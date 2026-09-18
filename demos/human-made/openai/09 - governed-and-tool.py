from donkey_kit import Donkey, DonkeyConfig, registered_tools
from donkey_kit.core.telemetry import current_correlation_id, current_cost_tags

# No gateway. Decorators only.
#
# python "demos/human-made/openai/09 - governed-and-tool.py"

donkey = Donkey(
    DonkeyConfig(
        llm_proxy_url="http://127.0.0.1:8080/",
        llm_proxy_client_id="demo-client-id-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
    )
)


@donkey.governed(team="support", project="triage")
def handle_ticket(ticket: str) -> str:
    print("run id inside", current_correlation_id())
    print("cost tags    ", current_cost_tags())
    return ticket


print("run id before", current_correlation_id())
handle_ticket("4417")
handle_ticket("4418")
print("run id after ", current_correlation_id())


@donkey.tool
def lookup_sku(sku: str) -> str:
    """Return stock for a product SKU."""
    return "42"


print("lookup_sku('AF-1001')", lookup_sku("AF-1001"))
print("same function object ", lookup_sku is registered_tools()[-1].func)
print("registered           ", registered_tools()[-1].name, registered_tools()[-1].signature)

try:

    @donkey.tool
    def undescribed(sku: str) -> str:
        return sku

except ValueError as err:
    print("undescribed tool     ", err)

donkey.close()
