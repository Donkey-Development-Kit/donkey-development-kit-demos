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

See [PRESENTING.md](../../../PRESENTING.md#15--provider-passthrough).
