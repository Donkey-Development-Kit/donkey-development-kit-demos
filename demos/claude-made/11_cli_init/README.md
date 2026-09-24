# 11 — donkey init

**Claim:** the first five minutes of an SDK should not be one-missing-variable
per run. `donkey init` writes a commented `.donkey-kit.toml`, names every
required field that is still missing, and never puts a secret in the file.

```bash
make demo N=11
```

**Needs:** `[cli]` (typer). Offline — no gateway, no simulator. The file is
written into a temp directory, not your repo.

**Three acts.** `--json init` against a fake env: the file appears and the
missing list is the same report `DonkeyConfig.validated` uses. Then the file
is scanned: the proxy `client_secret` value is absent. Then a second init
leaves the file untouched (`written: false`) unless `--force`.

**Point at:** secrets surface as commented env pointers. `doctor`, `mock` and
`test` are the other three shipped commands — doctor needs a live proxy
(demo 07); mock and test are demos 04 and 05.

Build guide: `BG §1.1` / CLI. See [PRESENTING.md](../../../PRESENTING.md#11--donkey-init).
