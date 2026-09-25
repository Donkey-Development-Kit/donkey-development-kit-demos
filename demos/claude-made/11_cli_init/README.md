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

## How to run

**Offline.** No gateway, no simulator, no credentials. `--target` is ignored.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[cli]"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=11
python run.py 11                           # same thing without make
```

**3. What you should see:**

1. `donkey --json init` in a temp directory: the file written and the list of still-missing fields.
2. The file scanned — the `client_secret` value is absent; secrets appear as commented env pointers.
3. A second `init` leaving the file alone (`written: false`) unless `--force`.

**4. If something goes wrong:**

- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §1.1` / CLI. See [PRESENTING.md](../../../PRESENTING.md#11--donkey-init).
