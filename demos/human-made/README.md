# Human-made scripts

Short, top-to-bottom Python, one folder per framework. No `_harness`, no output
masking, no individual `make demo` target — you run them with `python` exactly as you would
paste them into your own project.

| Folder | Framework | Scripts | Start with |
|---|---|---|---|
| [`openai/`](openai/) | stock `openai` via `donkey.openai()` | 01-18 | `17 - refusal-handlers.py` (offline) |
| [`langgraph/`](langgraph/) | LangChain + native LangGraph checkpoints | 01-10 | `10 - tool-approvals.py` (offline) |
| [`openai-agents/`](openai-agents/) | OpenAI Agents SDK | 01-05 | `04 - approvals.py` (offline scripted model) |
| [`agent-framework/`](agent-framework/) | Microsoft Agent Framework | 01–03 | `03 - start-gateway.py` (no gateway) |
| [`strands/`](strands/) | Strands Agents | 01-05 | `05 - approvals.py` (offline, Python 3.12) |
| [`crewai/`](crewai/) | CrewAI | 01–02 | `01 - basic-gw.py` |
| [`llamaindex/`](llamaindex/) | LlamaIndex `OpenAILike` | 01–02 | `01 - basic-gw.py` |
| [`adk/`](adk/) | Google ADK (LiteLLM / scripted BaseLlm) | 01-04 | `03 - approvals.py` (offline, Python 3.12) |
| [`anthropic/`](anthropic/) | native `anthropic` client, `Format=Anthropic` proxy | 01–02 | `02 - typed-refusals-simulated.py` (no network) |
| [`gemini/`](gemini/) | plain `httpx`, `Format=Gemini` proxy | 01–02 | `01 - native-generate-content.py` |
| [`conformance/`](conformance/) | Customer-style agent + public pytest plugin | agent/tests/verifier | `verify.py` (isolated local checks) |
| [`a2a/`](a2a/) | Official A2A SDK + blocking `Donkey.serve()` | launcher/verifier | `verify.py` (isolated loopback TCP checks) |

Each folder has its own README with the install line, the environment it
needs, and what every script prints.

## Before live scripts

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
python "demos/human-made/openai-agents/03 - start-gateway.py"     # needs [local,openai-agents]
python "demos/human-made/agent-framework/03 - start-gateway.py"   # needs [local,agent_framework]
python "demos/human-made/openai/17 - refusal-handlers.py"
python "demos/human-made/openai/18 - dynamic-provider-key.py"
python "demos/human-made/langgraph/10 - tool-approvals.py"
python "demos/human-made/openai-agents/04 - approvals.py"
python "demos/human-made/openai-agents/05 - governed-observations.py"
python demos/human-made/conformance/verify.py
python demos/human-made/a2a/verify.py                           # needs [a2a]
```

The `*-simulated.py` scripts also make no network call, but read
`DONKEY_LLM_PROXY_*` to build the client — any placeholder values work.

The new local reaction, dynamic-key, native approval and observation scripts
need no exported proxy values or dotenv. Approval scripts exercise real runners
with scripted models, not live generation. Approval is advisory, never gateway
authorization. Agents rejection is a function-call output, Strands rejection an
error tool result, ADK rejection a confirmation error response; LangGraph raises
`ApprovalRejected` on rejected resume. Framework storage owns native pauses;
the base DDK registry is process-global memory, and native LangGraph has no DDK
timeout. Protect approval/state payloads containing tool arguments.

Agents 05 observes first turns in `on_llm_end`; post-run visibility depends on
the execution path. ADK 04 bridges streamed callback observation, with usage on
the complete response and an unobserved caller. Neither is a refusal bridge.

The A2A verifier launches `01 - serve.py` in an isolated subprocess and checks
the generated card, success/synthetic handler refusal/recovery, correlation IDs
and graceful SIGINT shutdown over a real loopback TCP socket. It verifies the
blocking launcher and closed listener locally, not downstream gateway enforcement,
streaming or gateway exposure. The launcher uses no dotenv, credentials, model
calls or external collectors.

## Install by environment

Use the full narrative environment for the core stories and Agents/LangGraph
companions:

```bash
python -m pip install -e "../donkey-development-kit/python[llm,local,test,cli,otel,langgraph,openai-agents,a2a]" "langchain>=1.0" "mcp"
```

Framework dependencies can conflict; use separate environments for optional
frameworks. Strands/ADK need their separate extras and Python 3.12; the new scripts
were locally tested there, not in the default Python 3.15 environment. Their
folder READMEs give install/run commands. `[all]` does not replace the explicit
extras above or install every optional framework.

Run the new credential-free coverage set from the repo root:

```bash
make coverage PY=.venv/bin/python
.venv-frameworks/bin/python scripts/verify_sdk_coverage.py --frameworks
```

The first command includes the conformance and A2A verifiers. The second runs only
Strands/ADK in their separate Python 3.12 environment with the required extras.
These are local checks, not evidence that all framework scripts are live-verified.

## After updating the SDK

If `donkey mock` or `donkey doctor` fails with
`ModuleNotFoundError: No module named 'donkey_kit.provisioning.cli'`, the
console script is stale (the CLI moved to `donkey_kit.cli`). Reinstall the
editable SDK with the extras you use, e.g.:

```bash
python -m pip install -e "../donkey-development-kit/python[llm,local,cli]"
```
