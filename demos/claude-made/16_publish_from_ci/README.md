# 16 — publish from CI

**Claim:** the Exchange entry for an MCP server is a consequence of its code.
Declare the tool, set a version, merge: the scan-and-publish GitHub Action
publishes it, and a merge that changes nothing publishes nothing.

```bash
make demo N=16
```

**Needs:** nothing (`[cli]`). The demo runs `donkey publish --dry-run`
in-process against a fake org ID, with every `DONKEY_*` and `ANYPOINT_*`
variable stripped from its environment. Nothing is sent.

**What is published.** [`server/`](server/) is a one-tool MCP server:
`lookup_sku`, declared with `@donkey.tool(server="ddk-demo-sku-lookup")` in
`app.py`. Its `.donkey-kit.toml` holds the `[donkey.publication]` version and
the server's endpoint. `donkey publish` reads `app.py` statically and never
imports it. `group_id` is left out on purpose: it defaults to the org ID, which
CI passes from a secret, so no org identifier is committed.

**Three acts.** The plan a PR's dry run prints: one `mcp` asset, its tools,
endpoint and digest. The digest staying put across runs and moving when a tool's
docstring changes. The workflow step that runs it.

**The live half** is
[`.github/workflows/publish-from-ci.yml`](../../../.github/workflows/publish-from-ci.yml),
which runs on changes to `server/` or to the workflow file itself:

- **Pull request:** a dry run. The job summary shows the plan, and nothing is sent.
- **Push to `develop`:** a real publish to Exchange. An asset whose digest is
  already published is left `unchanged`.
- **Edit a tool without bumping `version`:** the job fails before sending
  anything, because Exchange never overwrites a version.
- **Fork PRs:** the job skips them, because they get no secrets.

The workflow needs three repository secrets: `ANYPOINT_CLIENT_ID`,
`ANYPOINT_CLIENT_SECRET` (a connected app with Exchange Contributor) and
`ANYPOINT_ORG_ID`.

**Pinned to `@develop`.** The action lives in the SDK repo's `action/` folder
and has not shipped in a release yet. Demos `develop` tracks SDK `develop`; the
pin moves to a release tag when demos `main` does.

## How to run

**Offline.** No gateway, no simulator, no credentials. `--target` is ignored.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[cli]"   # or: python -m pip install -e ".[sdk]"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=16
python run.py 16                           # same thing without make
```

**3. What you should see:**

1. Act 1: `exit 0`, one `mcp` asset `demo-org-id-not-real:ddk-demo-sku-lookup:1.0.0`, tool `lookup_sku`, a `sha256:` digest.
2. Act 2: the same digest on a second run, and a different one after a docstring edit.
3. Act 3: the workflow's `uses: Donkey-Development-Kit/donkey-development-kit/action@develop` step.
4. `The point`.

**4. If something goes wrong:**

- `Missing prerequisites`: the demo names the module and the `pip install` line, then exits 0 without running anything.
- Act 1 `FAIL` with `missing-group-id`: the SDK is older than `donkey publish`'s org-ID default. Reinstall it from `develop`.
- `The demo raised`: re-run with `DEMO_TRACEBACK=1` for the full traceback, which stays masked.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

See [PRESENTING.md](../../../PRESENTING.md#16--publish-from-ci).
