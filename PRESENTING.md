# Presenting these demos

Everything here assumes you are standing in front of people who have seen a lot
of SDK demos and are, reasonably, waiting to find out what this one is actually
for. The demos are built so you can answer that in the first ninety seconds.

- [Before you start](#before-you-start)
- [The one thing to get right](#the-one-thing-to-get-right)
- [Three talk tracks](#three-talk-tracks)
- [Demo-by-demo notes](#demo-by-demo-notes)
- [Screen-recording safety](#screen-recording-safety)
- [When something breaks on stage](#when-something-breaks-on-stage)
- [Questions you will get](#questions-you-will-get)

## Before you start

Run this the morning of, not five minutes before:

```bash
make doctor
make offline        # runs twenty credential-free narratives; inspect skips too
```

`make doctor` tells you what is installed and what will therefore run, without
printing a single credential value. If it reports a missing extra, install it
then — not while a room watches pip resolve dependencies.

Set up your terminal:

| Setting | Value | Why |
|---|---|---|
| Font size | 18pt or larger | Output is padded to 88 columns and assumes it |
| Width | ≥ 100 columns | Narrower and the tables wrap |
| Theme | Light background | Projectors wash out dark themes |
| `DEMO_PAUSE` | `1` | Pauses between acts so you can talk over each one |
| `NO_COLOR` | unset | PASS/FAIL colour helps, and never carries meaning alone |

```bash
export DEMO_PAUSE=1
```

For gateway-replay stories, a second pane running `make mock` makes the fixture
replay boundary visible. Local-only stories instead own their in-process
transports, ephemeral simulator, local OTLP receiver or ASGI lifespan; they do
not all attach to that second pane. Read each narrative README before presenting.

## The one thing to get right

The temptation is to open with "here is how you call a model through the
gateway". Resist it. That framing invites the obvious question — *why do I need
an SDK for two lines of client config?* — and you will spend the rest of the
session on the back foot.

**Open by conceding the point.** Demo 01 does this deliberately: it shows a
stock `openai` client reaching the gateway with a `base_url` and two headers,
and says out loud that you do not need this SDK for that. Then it shows the same
403 arriving at both clients, and what each one leaves you holding.

The line to land is: *the wrapper is not a way to reach the gateway. It is the
one place every request enters and every response leaves — which is the only
place budget, typed refusals, correlation ids, spans and simulation can all
attach without you wiring each one.* Everything after demo 01 is evidence for
that sentence.

## Three talk tracks

### The 10-minute version — "why this exists"

```bash
DEMO_PAUSE=1 make demo N=01     # ~4 min
DEMO_PAUSE=1 make demo N=04     # ~3 min
```

Demo 01 makes the argument. Demo 04 proves it pays: the `except PIIDetected`
branch nobody has ever executed, running in a unit test with no gateway. Stop
there. If you have 60 seconds left, run `make demo N=02` and scroll the
taxonomy without narrating it — the table speaks.

### The 30-minute version — "the six-piece minimum"

The argument, then each thing that hangs off the skeleton, in the order that
builds on itself:

| Order | Demo | Minutes | The beat |
|---|---|---|---|
| 1 | 01 governed client | 5 | Concede the easy part, then show the difference |
| 2 | 02 typed refusals | 4 | Every way the gateway says no, as a type |
| 3 | 03 budget and pacing | 5 | The window as an object; refuse before the 429 |
| 4 | 04 simulate | 4 | Test the branch, with no gateway |
| 5 | 05 conformance | 6 | Red, then green, against someone else's agent |
| 6 | 06 telemetry | 4 | What the platform team gets for free |

Demo 05 is the one to protect time for. It is the only demo where the audience
watches something *fail correctly* — three findings against an agent that looks
completely reasonable — and it reliably produces the "wait, does our agent do
that?" reaction that the rest of the session is trying to earn.

### The full version — add the live proof

Append demo 10 (offline, ~4 min) then demo 09 to the 30-minute track. Demo 10 is
the success-path counterpart to typed refusals — last_call, routing, usage,
`ModelSubstituted`. Demo 09 is the only narrative where a live model chooses
tool calls. Native framework companions exercise real runners with scripted
models offline, not live model decisions. Budget
five minutes for 09 and have a fallback (see below), because it is the one demo
that depends on a sandbox being up.

If you cannot run live, run `make demo N=08` instead: it constructs real
framework objects for every installed framework and reports honestly on the rest.
It is not as satisfying, but it is not a simulator either.

## Demo-by-demo notes

### 01 — governed client

**Say:** "You do not need us for this part." Show the stock client working. Then:
"Both of these got a 403. Watch what each one gives you."

**Point at:** the `base_url` with no `/v1` (a real, verified detail people get
wrong), and the fact that default auth is a `client_id` / `client_secret` header
pair rather than a bearer token. The model-wallet JWT ingress is demo 13. Act 2 now also prints `donkey.last_call` after the happy call —
who served it, what they served, what it cost — then repeats the same call on
`donkey.openai(sync=True)` so a room that does not want asyncio still sees
governance attach. Demo 10 is the deep dive. Act 4 is the one-line on-ramps: `@donkey.governed` opens a fresh `donkey.run()` per
call (no `id=` — that would collapse unrelated tickets), and `@donkey.tool`
records a callable without wrapping it. An undescribed tool is a `ValueError`
at decoration time.

**Expect:** the reply text is a story about a unicorn and does not answer the
prompt. That is the simulator replaying a captured response, and the demo prints
a warning saying so. Read the warning aloud — the honesty is part of the pitch.

### 02 — typed refusals

**Say:** "A PII block is a 403. So is an auth failure. If you branch on the
status code you will treat a governance decision as a credentials problem."

**Point at:** `content-safety` classifying as `ContentSafetyBlocked` (Azure,
live), and `regex-prompt-guard` as `PromptInjectionBlocked` with its own
policy name (also live). Bedrock Guardrails is live too — demo 15 shows it
next to Azure. Header-based `injection-protection` is the one shape still
typed from the documented wire format. Then point at `content-moderation`
still classifying as a generic `PolicyViolation`. Someone will ask why that
leftover 4xx is not its own class. The answer — *we have never captured that
shape from a real gateway, so we will not name it* — does more for your
credibility than any feature on the slide. Then act 5: `GatewayUnavailable`
when nothing is listening. It is not a refusal. The request never arrived.

### 03 — budget and pacing

**Say:** "There is no endpoint to ask how much budget is left. It only comes back
in-band, on response headers. So a new process knows nothing until its first call
returns — and the object says `None` rather than `0`, because `0` would be a lie
that stops an agent that could have run."

```bash
DEMO_PAUSE=1 make demo N=03
```

**Point at:** gateway token/request windows vs `budget.upstream.requests` and
`.tokens`. Provider quota belongs to the routed provider key and is observe-only;
an exhausted provider window does not drive `pace()`. Gateway reserve does.

**Boundary:** offline-only synthetic parser observations, plus a simulated 429.
OpenAI duration resets are parsed; Azure's unitless `0` remains unknown. A route
change or partial observation must not retain stale provider fields. Waiting
does not invent a fresh allowance; unknown reset returns immediately. Never
present an unconditional wait/retry loop as recovery.

### 04 — simulate

**Say:** "Every one of you has an `except PIIDetected` branch that has never
executed."

**Point at:** act 5, where `ContentSafetyBlocked` injects the live Azure
fixture — the branch runs — then `PromptInjectionBlocked` injects the
documented injection-protection representative, **not** the live regex
capture. `simulate()` picks one fixture per exception type. Then
`ToolInvocationError` still raises `ValueError`
instead of inventing a body. And act 6, where the same injection works through
LangChain's own `ChatOpenAI` — because it sits on the transport, not on a wrapper.
Act 7 is the running-simulator form of the same idea: `donkey mock --scenario`
scripts PII, injection and a real wall-clock budget window so a stock client
with no SDK in the process sees the refusal. Act 8 is the pytest-shaped form of
that: `start_gateway()` on an ephemeral port, `set_scenarios("pii_block:every=1")`,
a stock `httpx` POST, and `requests_received == 1` with `client_secret` already
`***` in the spy.

### 05 — conformance

**Say, before running:** read the naive agent's code out loud and ask the room
what is wrong with it. Nothing obviously is. Retrying is a sane default; wrapping
errors keeps stack traces out of the caller's face. Then run it.

**Point at:** three failures, each phrased as a finding about the agent rather
than an assertion error. Both in-process and server modes then give the corrected
agent four passes with matching verdict details. Server mode counts real loopback
requests without replacing the SDK transport. Then the exemption, and stress that
an exemption is an *asserted claim with a reason*, published rather than hidden,
never a silent skip. The last act proves the validation: a typo'd scenario name
fails the run at collection time.

**This is the deliverable.** Say that explicitly: the internal adapter matrix is
ours, this suite is theirs, and it runs in their CI against their agent in
whatever framework they picked. `donkey test --agent=…` is the same suite as a
CLI front-end: it execs pytest and returns pytest's exit code.
The compact [human-made example](demos/human-made/conformance/) is the customer
starting point: `python demos/human-made/conformance/verify.py` runs isolated
ordinary tests and both plugin modes. Uncaptured custom refusal shapes require
in-process mode.

### 06 — telemetry

**Say:** "Two namespaces on one span, on purpose. `gen_ai.*` is the standard
vocabulary so this lands in dashboards you already have. `donkey.*` is ours and
is stable — renaming one of those keys is a breaking change."

```bash
DEMO_PAUSE=1 make demo N=06
```

**Story:** adopt or mint an inbound ID with `run_from_headers()`, then explicitly
pass `correlation_headers()` to a plain HTTP hop. Correlation travels; consumer
credentials do not. Concurrent attribution scopes stay isolated. Cached,
cache-write and reasoning usage are observed without logging content.

**Point at:** actual protobuf spans arriving at a loopback OTLP receiver and
`flush_telemetry()` delivering the DDK-owned queue before shutdown. A later
host-owned provider wins, but its queue requires the host's `force_flush()` and
`shutdown()`. Async callers offload the blocking DDK flush with `asyncio.to_thread`.

**Boundary:** offline-only, fresh process, synthetic model transport and local
collector. The business-group header remains an unverified placeholder; these
assertions do not prove gateway attribution ingestion, authorization, remote
collector reliability or MCP binding. Cost tags stay on spans, not an invented
gateway ingestion API. Prompt/completion attributes remain absent.

### 07 — model handles

The short one. **Say:** "`GET /models` returns 404. That is verified, not
assumed. We could have guessed a path. A fabricated endpoint that 404s in your
sandbox costs more trust than the missing feature ever would."

Act 3 closes by pointing at `donkey doctor` (demo 14): the CLI that tells
wrong URL from wrong credentials from model-not-allowed, reusing the same
remediation strings.

Good filler if you are running ahead; safe to cut entirely if behind.

### 08 — framework objects

**Say:** "Two deep adapters, six at `connection_kwargs()`. That is a deliberate
cut, not a roadmap gap." The uneven roster is easier to defend when you name it
first.

**Point at:** `connection_kwargs()` being the *entire supported surface* for
six of the eight — which makes it the most load-bearing method in the module,
not the least. LangGraph and the Agents SDK are the adapters held to the
conformance bar, and both call `/chat/completions`. And at `donkey.openai_agents`, which is the Agents SDK
adapter; `donkey.openai()` is the raw client and got the good name. Then point
at `connection_kwargs()` for the Agents SDK: one key, `openai_client`, a real
`AsyncOpenAI`. Agent Framework's `chat_client()` builds an
`OpenAIChatCompletionClient(model=…)` — the kwarg is `model=`, not `model_id`. Then act 4:
a real `Agent` with `middleware=[donkey.agent_framework.policy_middleware()]`,
run under `donkey.simulate(PIIDetected)`. `agent.run()` ends as `PIIDetected`,
with the run's correlation id, not as Agent Framework's generic
`ChatClientException` (that is kept on `.framework_error`). The middleware
protocol is confirmed offline against agent-framework 1.19.0. Act 4 needs the
`[agent_framework]` extra; without it the demo prints the install line and
moves on.

### 09 — LangGraph agent (live)

**Say:** "The DDK lines are the one that builds the model, `donkey.run(id=…)`
around the loop, `typed_refusals()` so a gateway 403 is `PIIDetected`, and
`@donkey.tool` on the two functions — a marker, not a wrapper."

**Point at:** the budget after the run — several model calls in one agent loop,
one transport, all feeding the proxy's token window for this client ID. It is
shared, not a per-run total, and only fills in on a proxy that sends the header
(`ddk-token-rate-limit`, with `DEMO_LANGGRAPH_API=chat`).

**If asked why `last_call` is `unobserved`:** it is scoped per asyncio task and
LangGraph makes model calls on its own task. Demo 10 shows a direct call. The
Agents SDK companion 05 observes first turns in `on_llm_end`; later non-streamed
turns may reach the caller. ADK companion 04 uses `last_call_bridged` for streamed
callback observation. Neither observation mechanism is a typed-refusal bridge.

### 10 — last_call

**Say:** "On a refusal you already get the gateway's ids. On a 200 the same
facts used to vanish. `donkey.last_call` is that record."

**Point at:** three honest states, never a bare `None`. Then `substituted` —
against the simulator this lights up because the captured fixture was served
by a different model than the one we asked for; that is the fixture talking,
and it is exactly the mismatch the record exists to surface. Then act 4, the
same record on a semantic-routing proxy: `routing_type` flips to `Semantic` and
`matched_topic` / `routing_score` (`Finance`, `0.62`) fill in where the
model-based call had `None`. Then
`on_model_substitution="raise"` turning the flag into `ModelSubstituted`,
which is not a `PolicyViolation`. Pair this with demo 06 if the room is
platform-heavy: the same facts land on the span.

### 11 — donkey init

Short. **Say:** "The first five minutes of an SDK are usually one-missing-variable
per run." Show the json payload: the file was written, the remaining gaps are
named at once, and the proxy `client_secret` is not in the file. A second init
leaves the file untouched.

Good filler if you are running ahead. Pair with 07 if the room is ops-heavy.
`doctor` still needs a live proxy — do not pretend this demo is that.

### 12 — ToolSet.filter

**Say:** "Filter is pure; bind is governed." Show two views of the same servers
(`allow=` / `deny=`), the parent unchanged, colliding `get_employee` names
prefixed. Then `await tools.langgraph()` refusing the ungoverned servers
(`UngovernedMcpServer`, no credentials sent).

Do not let this become a discovery demo: it is offline. Discovery and governed
binding run against the live gateway (`donkey.tools.discover()`), not here. `@donkey.tool` (demo 01) is a different marker.

### 13 — JWT / model-wallet auth

**Say:** "The default header pair is not the only way in." Show jwt mode
wanting a wallet selector, not a secret. Then `X-Client-Id` only in the
snapshot, then `sync=True` refused.

**Point at:** the JWT never lives in a config file. `classify()` has no
dedicated JWT types yet — invalid 401 is `AuthError`, missing 400 is a
generic `PolicyViolation`. Do not run this against a live wallet in a room.

### 14 — donkey doctor

Short. **Say:** "Wrong URL, wrong credentials, and model-not-allowed look the
same from the outside." Incomplete config, then the simulator `[ok]`, then a
dead port as `GatewayUnavailable`.

**Point at:** this is not `make doctor` in this repo. Pair with 07 and 11 if
the room is ops-heavy.

### 15 — provider passthrough

**Say:** "The gateway does not rewrite what the provider says. So the same
question has a different wire answer on OpenAI, Bedrock and Gemini."

**Point at:** act 1's Bedrock row — `headers.get("x-request-id")` is `None`,
`request_id` is not. That id is the provider's; the gateway join key is
`correlation_id`. Act 2: Azure, Bedrock, Model Armor and CrowdStrike share
`ContentSafetyBlocked`, with vendor/categories/policy on the error and spans.
Model Armor is live-captured; CrowdStrike AIDR is policy-source-derived, not
live-captured. A fail-closed 503 is `UpstreamModelError`, not a content verdict.
Neither sibling shape is a simulator vendor selector. Act 3: Gemini's list-shaped 400 is an
`UpstreamRequestError` — before dev9 it fell through as a policy refusal that
never happened. Act 4: Format is fixed per proxy; `donkey.anthropic` needs a
`Format=Anthropic` proxy, and Gemini-native has no adapter on purpose.

### 16 — publish from CI

```bash
DEMO_PAUSE=1 make demo N=16
```

**Story:** registration, not deployment. Static `donkey scan` and publication
dry-run never import the sample project. Repeated plans are deterministic;
relocation preserves the digest, a description edit changes it, version alone
does not. Invalid semver, service ID and endpoint fail explicitly.

**Boundary:** the existing CI workflow is a separate publication path. The local
story proves planning inputs, not remote `unchanged` outcomes or authentication.
Exchange versions are immutable; changed content needs a version bump.
Connected-app publication auth remains unconfirmed live; agent publication is
skipped by the SDK.

### 17 - Refusal reactions

```bash
DEMO_PAUSE=1 make demo N=17
```

**Story:** centralize bounded wait, resend, model fallback and escalation with
`donkey.on(...)`. A revised request retains correlation but gets a fresh call ID.
**Talking point:** only a new governed request can succeed; a fabricated handler
response never lifts a refusal. Custom classifiers are process-wide, reactions
per Donkey, and temporary registrations are removed. Reset overrides and custom
policy shapes are synthetic; escalation records locally, not to a real service.

### 18 - Terminal kill handling

```bash
DEMO_PAUSE=1 make demo N=18
```

**Story:** a simulated `AgentKilled` wakes a budget waiter, latches subsequent
pacing/reset waits and leaves batch effects empty. Generic reactions never
receive it and a kill-specific recovery handler cannot be registered.
**Talking point:** consume the platform decision, do not administer or override
it. This is not a network firewall or live control-plane kill test.

### 19 - Tool approvals

```bash
DEMO_PAUSE=1 make demo N=19
python "demos/human-made/langgraph/10 - tool-approvals.py"
```

**Story:** no side effect before approval; base resolve/reject/expiry and native
LangGraph checkpoint resume; approved downstream work can still be refused.
Approval spans omit arguments, but approval/checkpoint payloads contain them.
**Talking point:** advisory local approval is not gateway authorization.
The base registry is process-global memory; native pauses use framework storage
and have no DDK timeout. `MemorySaver` recompilation is not restart durability.

For native Runner stories:

```bash
python "demos/human-made/openai-agents/04 - approvals.py"
# In the separate Python 3.12 environments documented by each folder:
python "demos/human-made/strands/05 - approvals.py"
python "demos/human-made/adk/03 - approvals.py"
```

They run real frameworks with scripted models. Agents serializes `RunState`;
Strands resumes an interrupt; ADK confirms and checks replay protection.
Rejection is respectively a function-call output, an error tool result or a
confirmation error response. Strands/ADK need separate Python 3.12 environments.

### 20 - Descriptor fidelity

```bash
DEMO_PAUSE=1 make demo N=20
```

**Story:** static scan inventories without imports; descriptor derivation reads
the framework's own model-facing schema. `auto:check` catches committed-schema
drift; `auto:live` reads an official MCP server's `tools/list` in memory.
**Talking point:** local protocol fidelity is not Exchange discovery or governed
binding. Auto modes execute imports/factories; choose import-safe entrypoints.
There is no `auto:static` mode. Install the official `mcp` package.

### 21 - Local A2A serving

```bash
DEMO_PAUSE=1 make demo N=21
```

**Story:** an `@donkey.agent` handler builds the official A2A SDK app. Fetch its
card, send success/refusal/success within one ASGI lifespan, and join SERVER task
spans to downstream model spans. Failed tasks expose typed IDs, not internal
messages or tracebacks; cleanup asserts no worker leaks.
**Talking point:** this proves the local app path used by `Donkey.serve()`, not
its blocking uvicorn launcher, a listening port, streaming delivery or gateway
exposure. Official dispatcher shutdown warnings are visible, not suppressed.

## Screen-recording safety

Output masking is on by default and you should leave it on. It covers the three
things that actually leak: the gateway hostname, the `client_id`/`client_secret`
pair, and the tenant identifiers embedded in captured responses
(`x-envoy-decorator-operation` carries an Anypoint API-instance and environment
id; `openai-organization` and `openai-project` identify the account).

Before you hit record:

1. `echo $DEMO_REDACT` — must be empty or `1`. If it is `0`, every demo prints a
   warning banner, but do not rely on noticing it.
2. Close the editor tab holding `.env.local`.
3. Clear your scrollback (`clear && printf '\e[3J'`). Earlier commands in the
   buffer are the most common leak, not the demo output.
4. Check your shell prompt does not interpolate anything — `AWS_PROFILE`,
   a kubectl context, a hostname you would rather not publish.
5. `history -c` if your prompt or a screenshot tool shows recent commands.
6. If a browser is in shot, use a fresh profile. Bookmarks and autofill are
   visible in a way people forget.

Afterwards, `make scan` before you commit anything you produced during the
session, and put recordings in `assets/` — which is git-ignored except for its
`.gitkeep`, precisely so a video cannot be committed by reflex.

If you must un-mask for debugging, do it in a pane you are not sharing, and set
it per-command rather than exporting it:

```bash
DEMO_REDACT=0 python run.py 01     # never `export DEMO_REDACT=0`
```

## When something breaks on stage

| Symptom | Cause | Do this |
|---|---|---|
| `Could not start the local simulator` | Port taken, or `[local]` / `[cli]` not installed | `DEMO_MOCK_URL=http://127.0.0.1:8099 make demo N=03` |
| `donkey: command not found` | CLI extra missing | `pip install "donkey-kit[cli,local]"` — or run demos 02, 07, 08, which need no simulator |
| Demo 05 warns about the pytest11 entry point | Editable install predates the plugin | Harmless; it loads the plugin by module instead. `pip install -e python` in the SDK checkout to clear it |
| Demo 09 exits with setup guidance | Credentials not loaded | Expected, not a failure. Switch to demo 08 |
| Demo 09 hangs | Sandbox slow or down | Ctrl-C; run `make demo N=04` and say the live proof is in the recording |
| Output wraps badly | Terminal under 100 columns | Widen, or reduce font one step |
| A demo raises | Anything | The traceback is suppressed and masked by default; `DEMO_TRACEBACK=1` shows it, still masked |

The general rule: **twenty of twenty-one narratives need no credentials**. If live access is
down, you have lost one demo, not the session. Say so plainly and move on —
trying to fix a sandbox in front of a room costs more than the demo was worth.

## Questions you will get

**"Why not just use the OpenAI client with a base_url?"**
You can, and demo 01 shows it working. The question is what happens on the
unhappy path: you get a 403 and a JSON body, and every governance concern —
budget, retries, correlation, spans, testing refusals — becomes something you
wire yourself, in each agent, consistently. The SDK's claim is not access, it is
that one attachment point is worth more than the sum of the things you would
otherwise wire six times.

**"How much of this is real versus mocked?"**
Seven rejection shapes, the base URL shape, the header pair, streaming,
inbound `X-Correlation-Id` echo, the per-provider request-id headers, and the
Anthropic- and Gemini-native ingress routes are live-verified against a real
gateway.
The simulator replays *those captures*,
byte for byte — it is not a hand-written fake, and the SDK's own `classify()`
tests read the same files, so a drifted capture breaks both at once. What is not
verified is stated in the demos as they run: the simulator's illustrative
happy-path budget numbers, header-based injection-protection (typed from
docs), the unnamed leftover content-moderation 4xx,
gateway cost-tag ingestion (verified-negative — tags live on spans), and the
framework adapters themselves: local conformance and native runner scripts are
not live round-trips. The new stories use synthetic budgets, transports,
scripted models and local protocols where stated. Model Armor is live-captured;
CrowdStrike and the fail-closed outage are source-derived. Only ADK's `gemini()`
has the stated live adapter round-trip.

**"What about tool discovery / provisioning?"**
Exchange discovery and governed MCP binding remain verification-blocked. Demo
16 shows static registration/dry-run, not provisioning; demo 20 shows local schema
fidelity, not remote discovery. Local A2A is demoed in 21, but gateway exposure,
`donkey expose` and `donkey dev` remain outside implemented scope. Connected-app
publication auth is still unverified live.

**"Does this lock us into your framework?"**
Every adapter returns the framework's own object. Demo 08 prints the concrete
class each one returns: `langchain_openai.ChatOpenAI`, `anthropic.AsyncAnthropic`.
There is no wrapper type to unwrap and nothing new in your stack traces.

**"Can we run the conformance suite against an agent that doesn't use the SDK?"**
It needs the agent to be built against a `Donkey` so the harness can swap the
transport underneath it. What it does *not* need is any particular framework, or
any knowledge of your agent's internals — it grades behaviour observed at the
wire and in the logs.
