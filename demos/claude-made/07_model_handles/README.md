# 07 — model handles and honest gaps

**Claim:** the SDK refuses to invent an endpoint. This is a small demo carrying a
large point about how the whole package is built.

```bash
make demo N=07
```

**Needs:** nothing at all.

**Three acts.** `resolve()` returning local, explicitly heuristic capability
handles; `list_models(live=True)` raising a `ConfigError` that explains the
verified absence of a catalog endpoint; and config validation reporting every
missing field at once rather than one per run. Act 3 also points at
`donkey doctor` — the CLI that tells wrong URL from wrong credentials from
model-not-allowed, reusing the same remediation strings.

**Point at:** `GET /models` returns 404 — verified against a real gateway, not
assumed — because model-based routing only routes requests that already carry
`model` in the body. The SDK could have guessed a path or shipped a list that
goes stale. A fabricated endpoint that 404s in a customer's sandbox costs more
trust than the missing feature ever would.

Good filler if you are ahead of time; safe to cut if behind.

Build guide: `BG §1.1`. See [PRESENTING.md](../../../PRESENTING.md#07--model-handles).
