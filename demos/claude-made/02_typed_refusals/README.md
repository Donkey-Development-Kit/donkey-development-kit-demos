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

**Point at:** `content-safety` classifying as `ContentSafetyBlocked` (and
`regex-prompt-guard` as `PromptInjectionBlocked` with `policy="regex-prompt-guard"`).
Those shapes are typed from the documented wire format and pending a live
capture — the same posture as header-based injection. Then point at
`content-moderation` still classifying as a generic `PolicyViolation`. That
leftover 4xx has never been captured from a real gateway, so it is left unnamed
rather than given a class that implies more certainty than exists.

Build guide: `BG §1.2`. See [PRESENTING.md](../../../PRESENTING.md#02--typed-refusals).
