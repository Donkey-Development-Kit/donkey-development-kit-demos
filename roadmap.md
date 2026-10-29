# Demo roadmap

This is the **demos** backlog, not the SDK's. The SDK roadmap (phases, HITL,
A2A, tool access) lives in the
[DDK docs](https://docs.donkey-kit.dev/roadmap).
This page answers: *which shipped SDK surfaces already have a demo, in which
suite, and what still needs writing.*

Two suites, two jobs — see [README.md](README.md) for how they differ.

| Suites | Path | Add a demo here when… |
|---|---|---|
| **Claude-made** | `demos/claude-made/NN_name/` | The room needs a story, acts, redaction, and `make demo N=…` |
| **Human-made** | `demos/human-made/<framework>/NN - name.py` | Someone should be able to run or paste a straight-line script |

Do not duplicate a narrative demo as a second story. If claude-made already
covers it, human-made only needs a short OpenAI (or other-framework) script.
If human-made already covers it, claude-made only needs a narrative when the
room must see it.

---

## Shipped

### Claude-made (`01`-`21`)

Governed client (async and `sync=True`) and raw-vs-governed 403; typed refusals
including live regex-prompt-guard, Azure content-safety and Bedrock Guardrails,
`GatewayUnavailable` and the two `AuthError` remediations;
budget / `pace` / `wait_for_reset()` **only when `reset_at` is known**;
`simulate()` plus `--scenario` parsing and **`start_gateway()`**; conformance
plugin and `donkey test` as the CLI front-end; GenAI spans, cost tags,
routing/usage attributes, and **zero-config OTLP**; model handles; framework
objects including Agents SDK `connection_kwargs() → {openai_client}` and Agent
Framework `policy_middleware()`; LangGraph live loop; `last_call` and opt-in
`ModelSubstituted`; `@donkey.governed` / `@donkey.tool` (in 01 and 09);
**`donkey init`**; **`ToolSet.filter`**; **JWT / model-wallet auth**
(`llm_proxy_auth="jwt"`); **`donkey doctor` against the local simulator**;
**provider passthrough** — per-provider `request_id`, Gemini's list error
envelope, and the Anthropic/Gemini ingress Formats.

Browser showcase (`demos/showcase`, 44 cards): 13 live chat cards, including the
simulator-backed kill-handling, CIBA pending/denied, regex-prompt-guard,
request-rate-limit and refusal-reactions cards, plus descriptive-only
`shipped` cards. The static Pages replay is guarded by `make check-showcase`
(catalog/replay drift and missing recordings). Narrative companions are demos
17-21; the showcase does not replace them and makes no live-gateway claim
beyond each card's stated verification status.

Coverage added for #47-59:

| Story | Executable evidence | Boundary |
|---|---|---|
| 03 budget extensions | Gateway token/request windows, separate provider quotas, reset parsing and route/partial observation | Offline-only synthetic headers; provider quota is observe-only |
| 05 conformance | Same naive/fixed/exemption verdicts in in-process and server modes | Server mode is real loopback HTTP, not live gateway evidence |
| 06 telemetry extensions | Cross-hop correlation, concurrent attribution, usage details, local OTLP and flush ownership | Offline-only; business-group header is an unverified placeholder |
| 15 guardrail vendors | Vendor fields and span attributes; Model Armor and CrowdStrike; fail-closed outage | Model Armor live capture; CrowdStrike/503 policy-source-derived, not simulator selectors |
| 16 existing CI publish story | Non-executing scan, deterministic dry-run, digest changes, invalid declarations | Registration only; connected-app auth unverified live, agent publication skipped |
| 17 refusal reactions | Bounded wait/resend/fallback, local escalation, classifier scope/cleanup | Only a new governed request can succeed; synthetic reset/custom shape |
| 18 kill handling | Kill wakes waiter, latches pacing/reset waits, blocks recovery handlers | Consumes a simulated decision; no kill administration or network firewall |
| 19 approvals | Base registry decisions/expiry, native LangGraph checkpoints and approval spans | Advisory; registry is process-global memory, native pauses have no DDK expiry |
| 20 descriptors | Framework-owned schema, `auto:check` drift, official MCP `tools/list` in memory | Auto imports execute; local protocol fidelity is not discovery/binding |
| 21 A2A | Official SDK app/card/tasks, refusal recovery, task/model traces and cleanup | Narrative uses ASGI lifespan; human-made companion verifies blocking launcher over local TCP; no streaming or gateway exposure tested |

### Human-made `openai/` (`01`-`18`)

Stock client; governed call + `last_call`; `simulate()`; live refusals
(blocking), including regex-prompt-guard and Azure content-safety; budget;
host-owned OTel exporter vs zero-config OTLP; last_call + `ModelSubstituted`;
`@donkey.governed` / `@donkey.tool`; dead-origin `GatewayUnavailable`;
**streaming** (`last_call` usage on the terminal SSE event); **JWT / model-wallet**
(async-only); **`start_gateway()`**; **Bedrock Guardrails** live.
17 adds local escalation/custom classification with cleanup and no manufactured
success. 18 asserts dynamic provider-key placement beside consumer authentication,
credential stripping at an unchecked origin and omission in JWT wallet mode.
Its header name is customer-configured, not a universal gateway contract.

### Human-made per framework

**`langgraph/`** (`01`-`10`): stock vs governed `ChatOpenAI`, `simulate()` and
live refusals through a `create_agent` graph with `typed_refusals()`, run id
inside a tool, OTel, streaming, dead origin, `start_gateway()` and native approval
checkpoint resume/rejection in 10.
**`openai-agents/`** (`01`-`05`) adds serialized native `RunState` approval and
customer conformance plus task-dependent `on_llm_end` observations.
**`strands/`** (`01`-`05`) adds native interrupt approval/rejection and propagation
of a governed refusal after approval. **`adk/`** (`01`-`04`) adds native
confirmation/replay protection and streamed factory/hand-built callback
observations via `last_call_bridged`. These use real runners with scripted local
models/transports, not live model generation. Strands/ADK optional extras were
locally tested in Python 3.12, not the default Python 3.15 environment.
**`agent-framework/`** (`01`-`03`), **`crewai/`** and **`llamaindex/`**
(`01`-`02` each) retain basic governed call/refusal coverage.
**`anthropic/`** and **`gemini/`** (`01`-`02` each) cover native ingress Formats.
**`conformance/`** supplies a compact agent, ordinary pytest tests, both plugin
modes and an isolated `verify.py`, including server request counting/port cleanup.
**`a2a/`** adds the real blocking `Donkey.serve()` launcher and an isolated
subprocess verifier: card/tasks over loopback TCP, synthetic handler refusal and
recovery, correlation IDs, graceful SIGINT shutdown, facade return and closed
listener. This is locally verified, not live gateway/provider evidence.

`make coverage` runs the new core companions plus conformance/A2A verifiers;
`scripts/verify_sdk_coverage.py --frameworks` runs only Strands/ADK in a separate
Python 3.12 environment. Neither check changes live verification status.

---

## Still missing — create these

Separate missing demo coverage from missing live evidence. Local execution of
a shipped API does not verify the gateway or a framework's live round-trip.

### Both suites

| Gap | Claude-made | Human-made | Notes |
|---|---|---|---|
| **Streaming** | mentioned as live-verified, no act | **12** | `responses` stream through `donkey.openai()`, and `last_call` usage lands on the terminal SSE event. Mock streaming is truncated SSE — do not claim terminal usage against the simulator. |
| **`donkey mock --scenario` as a long-running CLI** | 04 *parses* specs and boots `start_gateway()` | **15** is the Python twin | Remaining gap is a second-pane `donkey mock --scenario pii_block:every=2` that a stock OpenAI client hits. |
| **Header injection-protection live** | 02/04 type it from docs; regex, Azure and Bedrock (15) **are** live | **13** regex + Azure, **16** Bedrock | Header-based Injection Protection is the last guardrail with no deployed proxy to capture. `simulate(PromptInjectionBlocked)` keeps the documented representative. |
| **Anthropic-native live call** | 15 constructs `donkey.anthropic.client()`; no live `/v1/messages` call | **`anthropic/01`** | Route is live-verified but needs a `Format=Anthropic` proxy — the DDK default proxies are `Format=OpenAI`. On SDK `develop`, `last_call.request_id` reads Anthropic's `request-id`. |
| **Live observation under task-spawning frameworks** | 09 shows LangGraph's task-local gap | `openai-agents/05` and `adk/04` assert local hook/bridge behavior | Agents post-run visibility depends on execution path; ADK caller stays unobserved. Live observation evidence is still missing; observation is not refusal bridging. |
| **Live JWT / model-wallet end-to-end** | 13 is config + headers + guards | **14** is the live async call | Needs an org IdP and a wallet-backed proxy. Do not pretend the mock is that. |

### Claude-made only

| Gap | Why |
|---|---|
| **Live loop for a second framework** | Only LangGraph (09) has a live narrative loop. New native companions run tools with scripted models offline; they do not fill this live-proof gap. |
| **Wire human-made into `make list`?** | Deliberately not. `run.py` only finds `demo.py`. If we ever want `make demo N=08` to be ambiguous, rename human-made scripts into `NN_name/demo.py` groups — that is a product choice, not a missing feature. |

### Human-made only

| Gap | Why |
|---|---|
| **Live runs of the optional framework scripts** | Strands, CrewAI, LlamaIndex, ADK LiteLLM, Agent Framework and Agents scripts have local stub/simulator/scripted-runner evidence, not a verified live script round-trip. ADK's separately live-verified `gemini()` adapter is not these LiteLLM scripts. |
| **Redaction / `--target mock`** | Out of scope for this suite by design. If a script is going on a recording, use claude-made. |
| **Rename files without spaces** | Convenience, not coverage. Keep the current convention until someone decides to break it. |

### SDK issues found while writing the framework folders

| Issue | Evidence | Workaround in the scripts |
|---|---|---|
| `donkey.strands.model()` / `connection_kwargs()` break on the 2nd model call | Strands (1.57) does `async with openai.AsyncOpenAI(**client_args)` per request; closing it closes the shared `http_client` → `RuntimeError: client has been closed` | `OpenAIModel(client=donkey.openai(), model_id=…)` — Strands leaves an injected client open |

### Evidence still missing

| Gap | Exact boundary |
|---|---|
| Connected-app Exchange publication | 16 exercises scan/dry-run only. User-session captures do not verify connected-app authentication, remote digest lookup or `unchanged` outcomes. Agent publication is skipped. |
| Approval durability and service integration | Base pending calls are process-global memory. LangGraph uses `MemorySaver`; no process-restart durability test, authenticated approver service, queue/UI or gateway step-up is demonstrated. Native LangGraph pauses have no DDK expiry. |
| A2A streaming and exposure | 21 covers official app behavior in an ASGI lifespan; human-made `a2a/verify.py` locally verifies the blocking `Donkey.serve()` launcher over TCP and graceful shutdown. Card advertises no streaming; narrative shutdown warnings remain visible. Gateway exposure is unimplemented; local TCP checks do not verify live gateway enforcement. |
| Attribution ingestion and remote shutdown/export failure | 06 proves isolated local scopes and flush ownership with loopback OTLP. Business-group header is unverified; no gateway authorization/ingestion or remote collector failure benchmark is established. |
| CrowdStrike live verdict/outage | 15 uses policy-source-derived shapes. Model Armor, Azure and Bedrock captures do not establish a CrowdStrike round-trip. |
| Dynamic provider-key live route | OpenAI 18 asserts local origin/auth placement only. Its customer-chosen header must match the route's Dynamic-key expression; no universal header or live route verification is claimed. |
| Kill control plane | 18 consumes the simulated kill decision; no live kill issuance, control-plane operation or arbitrary HTTP blocking is demonstrated. |

---

## Do not create yet — blocked on the SDK

Do not confuse these remaining blocked/unimplemented surfaces with the shipped
static scan, local approvals or local A2A app now demonstrated above.

| SDK surface | Phase | Demo implication |
|---|---|---|
| Exchange discovery | blocked | No "list my tools from Exchange" demo |
| MCP tool binding | verification-blocked | Filter is shipped (12); descriptor fidelity (20) is local. `@donkey.tool` registration/approval is not remote governed binding. |
| API-instance/proxy provisioning | blocked | Static scan/publication planning (16) is not "stand up an API instance" |
| A2A gateway exposure / `expose` / `dev` | unimplemented | Local official-SDK app is covered by 21 and blocking TCP launcher by human-made `a2a/`; exposure/dev are not |
| Identity / on-behalf-of | Phase 2 | No OBO token-exchange demo |
| Platform approval service / gateway step-up | not demonstrated | Local `@donkey.tool(approval=..., risk=...)` and native advisory gates are covered; no platform service is implied |
| Policy handshake / in-force policy set | Phase 3 | No "read policies before calling" demo |
| TypeScript port | Phase 5 | This repo is Python |

When any of those ship in the SDK, add **claude-made first** if it needs a
story (taxonomy, honesty, redaction), then a **human-made** straight-line
script in the matching framework folder.

---

## How to add the next demo

**Claude-made.** Copy an existing `NN_name/` directory. Keep the harness
(`preflight.cli`, `narrate`, `redact`). Prefer `--target mock`. Update the
table in README.md, a section in PRESENTING.md, and this file.

**Human-made.** Add `demos/human-made/<framework>/NN - short-name.py`. No
helpers unless the SDK API requires a `def` (decorators). Quote paths with
spaces. Do not add a `make` target unless the suite is being brought under
`run.py` on purpose. Update the table in README.md and this file.

Never vendor live captures (`**/_fixtures/`, `*.headers.txt`, `*.body.json`
are git-ignored). Load fixtures from `donkey_kit.simulator.fixtures`.
