# 25 - donkey scaffold

From code to a publish-ready `.donkey-kit.toml`, offline. `donkey scan` names
what the code cannot say, `donkey scaffold` turns that into the declaration
tables, `--set` fills the values you know, and a readiness report says what
publish and each expose still need. It is the onboarding half of demo 16: that
demo publishes a project that is already declared, this one gets a project
there.

Static and offline. Nothing is imported, no network is used and no credential
is needed. Every step runs the real CLI in a subprocess on a temporary copy of
`app/`, with an isolated `HOME` and config, so your own `.donkey-kit.toml` and
environment are out of reach.

## Run

Needs `donkey-kit[cli]` from SDK develop. From the demos root:

```bash
.venv/bin/python demos/claude-made/25_cli_scaffold/demo.py
make demo N=25
```

Missing extras produce harness guidance and exit 0 without running the
assertions. Otherwise it exits 0 only when every assertion passes.
`DEMO_PAUSE=1` pauses between acts for a live audience.

## What it shows

1. **Scan names the gap.** `app/main.py` declares one tool and one agent.
   Scan lists the MCP server as `transport undeclared (set transport in
   [donkey.mcp_servers.sku-manager]; ...)`. That is not an issue, so it exits 0.
2. **Scaffold previews.** `donkey scaffold --dry-run` prints the tables and the
   readiness report and writes no file. What the code says becomes a key; what it
   cannot say is a commented placeholder.
3. **`--set` fills values and refuses what it must.** A credential in a URL and
   a secret-looking key each exit 2, write nothing and are never echoed. A
   valid set writes real values, and publish becomes `ready`. A second scaffold
   adds nothing and leaves the file byte-for-byte alone.
4. **Set but wrong is invalid, not undeclared.** An unknown transport and an
   endpoint with a credential in it each exit 1. The scan line says `invalid`
   and points at the `invalid-transport` or `invalid-endpoint` issue instead of
   telling you to set a key that is already set, and the rejected value is not
   printed.

## Boundary

Readiness reads the committed file only. It never says a service is verified:
`donkey doctor`, `donkey preflight` and `donkey expose --dry-run` check the live
credentials, gateway and upstreams, and this demo runs none of them. The
expose report here shows what is still missing; it does not expose anything.
The invalid-versus-undeclared wording needs the SDK build that carries
donkey-development-kit#1802.
