# Demo roadmap

This is the **demos** backlog, not the SDK's. The SDK roadmap (phases, HITL,
A2A, tool access) lives in the
[DDK docs](https://donkey-development-kit.github.io/donkey-development-kit/roadmap).
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

## Shipped in this branch (vs `develop`)

`develop` still has the pre-split deliverables layout. This branch rebuilds
the repo around the two suites and tracks the current SDK.

### Claude-made (`01`–`14`)

Governed client (async and `sync=True`) and raw-vs-governed 403; typed refusals
including live regex-prompt-guard and Azure content-safety,
`GatewayUnavailable` and the two `AuthError` remediations;
budget / `pace` / `wait_for_reset()` **only when `reset_at` is known**;
`simulate()` plus `--scenario` parsing and **`start_gateway()`**; conformance
plugin and `donkey test` as the CLI front-end; GenAI spans, cost tags,
routing/usage attributes, and **zero-config OTLP**; model handles; framework
objects including Agents SDK `connection_kwargs() → {openai_client}` and Agent
Framework `policy_middleware()`; LangGraph live loop; `last_call` and opt-in
`ModelSubstituted`; `@donkey.governed` / `@donkey.tool` (in 01 and 09);
**`donkey init`**; **`ToolSet.filter`**; **JWT / model-wallet auth**
(`llm_proxy_auth="jwt"`); **`donkey doctor` against the local simulator**.

### Human-made OpenAI (`01`–`15`)

Stock client; governed call + `last_call`; `simulate()`; live refusals
(blocking), including regex-prompt-guard and Azure content-safety; budget;
host-owned OTel exporter vs zero-config OTLP; last_call + `ModelSubstituted`;
`@donkey.governed` / `@donkey.tool`; dead-origin `GatewayUnavailable`;
**streaming** (`last_call` usage on the terminal SSE event); **JWT / model-wallet**
(async-only); **`start_gateway()`**.

---

## Still missing — create these

Work that maps to **already-shipped** SDK APIs. Safe to write; nothing below
is blocked on verification.

### Both suites

| Gap | Claude-made | Human-made | Notes |
|---|---|---|---|
| **Streaming** | mentioned as live-verified, no act | **12** | `responses` stream through `donkey.openai()`, and `last_call` usage lands on the terminal SSE event. Mock streaming is truncated SSE — do not claim terminal usage against the simulator. |
| **`donkey mock --scenario` as a long-running CLI** | 04 *parses* specs and boots `start_gateway()` | **15** is the Python twin | Remaining gap is a second-pane `donkey mock --scenario pii_block:every=2` that a stock OpenAI client hits. |
| **Header injection-protection / Bedrock live** | 02/04 type them from docs; regex + Azure content-safety **are** live | **13** hits regex + Azure; 04 already hits PII / token / auth / upstream | Header-based Injection Protection and Bedrock Guardrails still have no deployed proxy to capture. `simulate(PromptInjectionBlocked)` keeps the documented injection-protection representative. |
| **Live JWT / model-wallet end-to-end** | 13 is config + headers + guards | **14** is the live async call | Needs an org IdP and a wallet-backed proxy. Do not pretend the mock is that. |

### Claude-made only

| Gap | Why |
|---|---|
| **Live loop for a second framework** | 08 constructs ADK / Strands / Agents SDK / Anthropic / CrewAI / LlamaIndex / Agent Framework and stops. Only LangGraph (09) runs tools. A CrewAI or Anthropic "hello + one tool" would show `connection_kwargs()` is enough. |
| **Wire human-made into `make list`?** | Deliberately not. `run.py` only finds `demo.py`. If we ever want `make demo N=08` to be ambiguous, rename human-made scripts into `NN_name/demo.py` groups — that is a product choice, not a missing feature. |

### Human-made only

| Gap | Why |
|---|---|
| **`human-made/langgraph/` (and friends)** | Folder is OpenAI-only. A 20-line `donkey.langgraph.chat_model` + `create_agent` script would match claude-made 09 without the narrator. Same pattern for Anthropic / CrewAI if someone is pasting into those stacks. |
| **Conformance as a pytest file** | Claude-made 05 is the story. A human-made `test_agent.py` that is *just* the plugin against a tiny agent would be the thing people copy into their repo. |
| **Redaction / `--target mock`** | Out of scope for this suite by design. If a script is going on a recording, use claude-made. |
| **Rename files without spaces** | Convenience, not coverage. Keep the current convention until someone decides to break it. |

---

## Do not create yet — blocked on the SDK

These code paths raise `NotImplementedError("blocked on verification")` or are
Phase 2/3 on the SDK roadmap. A demo that pretends they work would be a lie.

| SDK surface | Phase | Demo implication |
|---|---|---|
| Exchange discovery | blocked | No "list my tools from Exchange" demo |
| MCP tool binding | Phase 2 | Filter is shipped (demo 12). Binding still raises. `@donkey.tool` is only the **marker**. Do not demo discovery or bind. |
| Provisioning verbs other than `validate` / `mock` | blocked | No "stand up an API instance" demo |
| A2A `serve` / `expose` / `dev` | Phase 2 | Agent-card generator will read `registered_tools()`; neither consumer is built |
| Identity / on-behalf-of | Phase 2 | No OBO token-exchange demo |
| Human-in-the-loop | Phase 2 | `@donkey.governed` has no `approval=` / `risk=` yet |
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
