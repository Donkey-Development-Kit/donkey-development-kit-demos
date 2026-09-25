# 02 — typed refusals

**Claim:** governance outcomes should be something you branch on, not something
you parse. The discriminator is deliberately not the status code — a PII block
is a 403 but is not an auth failure, and an injection block is identified by a
header.

```bash
make demo N=02
```

**Needs:** nothing at all. No gateway, no simulator, no credentials.

**Where the fixtures come from:** the installed SDK
(`donkey_kit.simulator.fixtures`), not copies in this repo. Those are the same
bytes `classify()` is unit-tested against and the same bytes `donkey mock`
serves, so a drifted capture fails this demo and the SDK's tests together. It
also keeps live captures — which carry real Anypoint instance and organisation
identifiers — out of this repository entirely.

**Point at:** `content-safety` classifying as `ContentSafetyBlocked` (Azure,
live-verified) and `regex-prompt-guard` as `PromptInjectionBlocked` with
`policy="regex-prompt-guard"` (also live). Bedrock Guardrails is live too — same
reject-header family as Azure, walked in [demo 15](../15_provider_passthrough/).
Header-based `injection-protection` is the one shape still typed from the
documented wire format, pending a live capture. Then point at
`content-moderation` still classifying as a generic `PolicyViolation`. That
leftover 4xx has never been captured from a real gateway, so it is left unnamed
rather than given a class that implies more certainty than exists.
`ModelSubstituted` is not in the table: it is not a gateway refusal and
`classify()` never produces it — see [demo 10](../10_last_call/).
`GatewayUnavailable` is the other type `classify()` cannot produce: there is
no HTTP response. Act 5 points a governed client at a closed local port so
you see the typed error, not a raw `httpx.ConnectError`. It is deliberately
not a `PolicyViolation` — nothing was refused, because nothing arrived.
`AuthError` names two credential planes: the data-plane default
(`DONKEY_LLM_PROXY_*`) versus `connected_app_remediation` for Anypoint
control-plane token fetch. JWT classify types are not shipped — demo 13.

## How to run

**Offline.** No gateway, no simulator, no credentials. `--target` is ignored.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[llm]"   # or: python -m pip install -e ".[sdk]"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=02
python run.py 02                           # same thing without make
```

**3. What you should see:**

1. `Nine captured responses through classify()` — one row per fixture: status, discriminator, exception type, key fields.
2. `Why the hierarchy is shaped this way` and `What that looks like in your agent` — the `except` ladder.
3. `What is typed from docs, and what is still unnamed` — header injection-protection and the unnamed `content-moderation` 4xx.
4. `AuthError names two credential planes` — data-plane vs control-plane remediation.
5. A governed client aimed at a closed port raising `GatewayUnavailable`, not `httpx.ConnectError`.

**4. If something goes wrong:**

- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §1.2`. See [PRESENTING.md](../../../PRESENTING.md#02--typed-refusals).
