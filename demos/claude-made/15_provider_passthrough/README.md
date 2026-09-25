# 15 — provider passthrough

**Claim:** the gateway forwards what the upstream provider says, so the wire
answer differs per provider. The SDK absorbs that: one `request_id`, one
`ContentSafetyBlocked`, one `UpstreamRequestError`.

```bash
make demo N=15
```

**Needs:** nothing (`[llm]`; act 4 uses `[anthropic]` if installed). Shapes the
SDK packages load from `donkey_kit.simulator.fixtures`; the Bedrock and Gemini
shapes are rebuilt inline from their live captures, discriminating headers only.
Nothing is vendored.

**Four acts.** The request id arriving as `x-request-id` (OpenAI, Azure),
`x-amzn-requestid` (Bedrock) or `apim-request-id`, and landing on one field.
Azure Content Safety and Bedrock Guardrails rejecting with vendor-named headers,
both classifying as `ContentSafetyBlocked`. OpenAI's object error envelope and
Gemini's list envelope both classifying as `UpstreamRequestError`. The three
ingress Formats and which adapter each one pairs with.

**Point at:** act 1's Bedrock row — `headers.get("x-request-id")` is `None`,
`request_id` is not. That id is the *provider's*; quote it to the provider. The
gateway-side join key is `correlation_id` (demo 06). Then act 3: before
`0.1.0.dev9`, Gemini's 400 fell through to a generic `PolicyViolation` — a
governance refusal that never happened.

**Act 4 honesty.** Format is fixed per proxy. The DDK proxies are
`Format=OpenAI`, where `/v1/messages` 404s. `donkey.anthropic` needs a
`Format=Anthropic` proxy; it no longer warns because that route is
live-verified. Gemini-native is verified but no adapter ships. Native ingress
is single-route — fallback stays OpenAI-only.

**Still documented-only:** header-based Injection Protection. The
`AsyncAnthropic` constructor signature is matrix-checked, not asserted.

## How to run

**Offline.** No gateway, no simulator, no credentials. `--target` is ignored.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[llm]"   # or: python -m pip install -e ".[sdk]"
make doctor                    # what is installed; prints no secrets
```

Optional: `[anthropic]` lets act 4 construct `donkey.anthropic.client()`; it is skipped otherwise.

**2. Run it:**

```bash
make demo N=15
python run.py 15                           # same thing without make
```

**3. What you should see:**

1. Act 1: the provider's request id arriving as `x-request-id`, `x-amzn-requestid` or `apim-request-id`, landing on `request_id`.
2. Act 2: Azure Content Safety and Bedrock Guardrails both as `ContentSafetyBlocked`, the message naming the vendor.
3. Act 3: OpenAI's error object and Gemini's list envelope both as `UpstreamRequestError`.
4. Act 4: the three ingress Formats and which adapter each pairs with.
5. `What is still not verified`, then `The point`.

**4. If something goes wrong:**

- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

See [PRESENTING.md](../../../PRESENTING.md#15--provider-passthrough).
