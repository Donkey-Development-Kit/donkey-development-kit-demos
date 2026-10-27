# 20 - Descriptor Fidelity And Drift

Read the schema the framework already owns, rather than reconstructing it from
Python annotations. Needs SDK develop, `langchain-core` (included with
`donkey-kit[langgraph]`) and the official `mcp` SDK. This environment has MCP 2.x;
`memory_server.py` also supports the official 1.x FastMCP spelling.

## Run

From the demos root, with no credentials or external network:

```bash
.venv/bin/python demos/claude-made/20_descriptor_fidelity/demo.py
.venv/bin/python demos/claude-made/20_descriptor_fidelity/example.py
.venv/bin/python run.py 20
```

The narrative uses `preflight.cli(target="offline")` with explicit
`langchain_core` and `mcp` prerequisite checks. Missing extras produce guidance
and exit 0 without running assertions. Otherwise exit 0 means all assertions
passed; schema drift or unexpected acceptance of invalid objects exits nonzero.
Optional SDK/framework imports run only after preflight; the MCP server factory
imports the official MCP package lazily. The protocol derivation has a 15-second
`asyncio.wait_for` timeout.

Offline harness preflight does not load dotenv configuration. This demo constructs
no Donkey/client and passes no configuration or credentials into derivation.
`example.py` also runs standalone without dotenv loading. Narrative fields
use default masking; `DEMO_PAUSE=1` enables interactive pauses between acts.

## Asserted Coverage

- A non-executing static `scan()` leaves `tools` absent from `sys.modules`.
- `derive_descriptor("tools:TOOLS")` imports that module and exactly equals its
  real LangChain tool's name, description and `tool_call_schema.model_json_schema()`.
- `auto:check` matches the committed `descriptor.json`; changing a schema field
  in a temporary comparison file raises `DescriptorMismatch`.
- An unsupported plain object raises `TypeError`; two tools with the same name
  raise `ValueError`. Unverified framework objects can instead be verification-blocked;
  the SDK does not invent a second schema converter for them.
- `auto:live` initializes an official MCP SDK server and reads `tools/list` over
  the SDK's in-memory protocol transport. Its result exactly matches the server's
  native descriptor, including the input schema.

`example.py` is the compact, copyable descriptor/check example. The committed
descriptor is intentionally sensitive to framework schema changes; investigate a
failure before regenerating it if the contract change was intended.

## Honesty Boundary

`auto` and `auto:check` execute imports, decorators and zero-argument factories.
Choose explicit, import-safe entrypoints. Static scan can inventory code without
executing it, but cannot claim the framework's model-facing schema fidelity.
There is no supported `auto:static` mode.

Here `auto:live` means **local protocol fidelity**, not remote discovery, Exchange
access, gateway verification or governed binding. It opens no remote connection
and starts no socket server. The in-memory session is closed by the SDK's context
manager. Publication and provisioning are not part of this example. `BG §2.5`.
