# 16 - Static Registration From CI

This is the offline half of the existing publication story: registration, not
deployment or provisioning. It does not run the live CI workflow, import the sample
project, or contact Exchange. No external network is needed. The narrative uses
offline harness preflight, which does not load dotenv configuration. The CLI
subprocesses are also isolated from ambient configuration.

## Run

Needs `donkey-kit[cli]` from SDK develop. From the demos root:

```bash
.venv/bin/python demos/claude-made/16_publish_from_ci/demo.py
.venv/bin/python demos/claude-made/16_publish_from_ci/offline.py
```

The first command also checks that the existing CI action reference is present.
The narrative checks the `[cli]` prerequisite (`typer`) before executing its
lazy imports. Missing extras produce harness guidance and exit 0 without running
the assertions. Otherwise both exit 0 only when assertions pass; a regression
exits nonzero. `DEMO_PAUSE=1` enables pauses during an interactive presentation;
plan fields use the harness's default masking.
They invoke the installed CLI with isolated HOME, XDG config and working directory,
no ambient SDK or Anypoint environment, and only a deliberately fake org ID.

The exact CLI operations exercised are:

```bash
donkey scan demos/claude-made/16_publish_from_ci/server --json
donkey publish demos/claude-made/16_publish_from_ci/server --dry-run --json
```

Both entrypoints provide credential-free verification without dotenv loading;
`offline.py` runs standalone without the narrative harness. They isolate the CLI
so it cannot resolve your local configuration. `server/app.py` declares `lookup_sku`
with `@donkey.tool(server="ddk-demo-sku-lookup")`; its `.donkey-kit.toml` declares
the MCP transport/endpoint, the publication version, the MCP protocol version and
provider Agent Fabric shows, and the asset's name, description and documentation
file. `server/README.md` is that file: a publish puts it at the top of the asset's
generated Exchange page, above the tools, connection details and provenance.
Static scanning does not derive a framework-owned input schema.

## Asserted Coverage

- Scan and dry-run JSON are byte-for-byte deterministic across repeated runs.
- Exactly one MCP asset names `lookup_sku`, its endpoint and version, and carries
  the declared name, description, protocol version, provider and documentation.
- A temporary import-time raising statement is never executed by scan or planning.
- Relocating code and shifting source line numbers preserve its digest.
- Editing the tool description or the documentation file changes the digest;
  changing only version does not.
- The three reusable `invalid/*.toml` samples replace the declaration in temporary
  copies: invalid semver, unknown service ID and invalid endpoint each exit 1 with
  the expected issue kind. Only dry runs are invoked, including these failures.

## Publication Boundary

The existing `.github/workflows/publish-from-ci.yml` remains the separate live
path. Its PR dry run and develop publication behavior are not exercised here.
The default `--if-changed` compares published content digests and skips matching
content. Exchange versions are immutable: changed content at an existing version
requires a version bump. The offline digest assertions demonstrate the inputs to
that decision, not remote lookup, skip outcomes or Exchange authentication.

Agent publication is skipped by the SDK. Connected-app publication authentication
remains unconfirmed live; user-session captures do not establish connected-app
authentication. This demo changes no verification status and provisions nothing.
