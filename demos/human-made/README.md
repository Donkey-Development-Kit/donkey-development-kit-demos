# Human-made scripts

Short, top-to-bottom Python, one folder per framework. No `_harness`, no output
masking, no `make` target — you run them with `python` exactly as you would
paste them into your own project.

| Folder | Framework | Scripts | Start with |
|---|---|---|---|
| [`openai/`](openai/) | stock `openai` via `donkey.openai()` | 01–16 | `02 - basic-responses-gw.py` |
| [`langgraph/`](langgraph/) | LangChain `ChatOpenAI` + LangGraph `create_agent` | 01–09 | `02 - basic-gw.py` |
| [`openai-agents/`](openai-agents/) | OpenAI Agents SDK | 01–03 | `03 - start-gateway.py` (no gateway) |
| [`agent-framework/`](agent-framework/) | Microsoft Agent Framework | 01–03 | `03 - start-gateway.py` (no gateway) |
| [`strands/`](strands/) | Strands Agents | 01–04 | `01 - basic-gw.py` |
| [`crewai/`](crewai/) | CrewAI | 01–02 | `01 - basic-gw.py` |
| [`llamaindex/`](llamaindex/) | LlamaIndex `OpenAILike` | 01–02 | `01 - basic-gw.py` |
| [`adk/`](adk/) | Google ADK (LiteLLM) | 01–02 | `01 - basic-gw.py` |
| [`anthropic/`](anthropic/) | native `anthropic` client, `Format=Anthropic` proxy | 01–02 | `02 - typed-refusals-simulated.py` (no network) |
| [`gemini/`](gemini/) | plain `httpx`, `Format=Gemini` proxy | 01–02 | `01 - native-generate-content.py` |

Each folder has its own README with the install line, the environment it
needs, and what every script prints.

## Before any script

Run everything from the repo root, inside the virtual environment from the
top-level [Setup](../../README.md#setup):

```bash
source .venv/bin/activate
set -a; source .env.local; set +a      # the scripts never read .env.local themselves
```

`.env.local` (git-ignored) holds the three proxy variables:

```bash
DONKEY_LLM_PROXY_URL=https://REPLACE-ME.example.invalid/REPLACE-ME/   # trailing /, no /v1
DONKEY_LLM_PROXY_CLIENT_ID=…
DONKEY_LLM_PROXY_CLIENT_SECRET=…
```

A shell `export` always wins over the file, so you can point one run at a
different proxy without editing anything:

```bash
DONKEY_LLM_PROXY_URL=https://REPLACE-ME.example.invalid/ddk-anthropic-inbound/ python "demos/human-made/anthropic/01 - native-messages.py"
```

## Three things that trip people up

1. **The model id.** The scripts say `gpt-4o`. The provisioned DDK proxies route
   `gpt-5-mini`. Change the `MODEL` constant (or the `"gpt-4o"` string) to a
   model your proxy routes, or expect a routing refusal / `ModelSubstituted`.
2. **Filenames have spaces.** Always quote the path.
3. **Policies decide refusals.** A `typed-refusals-live` script prints
   `NO REFUSAL` when the proxy does not have that policy applied — that is the
   proxy telling the truth, not the script failing.

## Scripts that need no gateway at all

These run with placeholder credentials and prove the install works:

```bash
python "demos/human-made/openai/09 - governed-and-tool.py"
python "demos/human-made/openai/11 - gateway-unavailable.py"
python "demos/human-made/openai/15 - start-gateway.py"            # needs [local]
python "demos/human-made/langgraph/08 - gateway-unavailable.py"
python "demos/human-made/langgraph/09 - start-gateway.py"         # needs [local]
python "demos/human-made/openai-agents/03 - start-gateway.py"     # needs [local]
python "demos/human-made/agent-framework/03 - start-gateway.py"   # needs [local]
```

The `*-simulated.py` scripts also make no network call, but read
`DONKEY_LLM_PROXY_*` to build the client — any placeholder values work.

## Install everything at once

Frameworks pin conflicting dependencies; one environment per framework is the
safe default. If you want one environment anyway:

```bash
python -m pip install -e "../donkey-development-kit/python[all]" "langchain>=1.0" "strands-agents[openai]"
```
