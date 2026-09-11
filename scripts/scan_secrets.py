#!/usr/bin/env python3
"""Fail the repo if anything that looks like a real credential, gateway URL or
piece of infrastructure identity is about to be committed.

`.gitignore` is the first gate and it only catches files people name predictably.
This is the second gate, and it reads content: a real value pasted into a tracked
demo, a live capture dropped into a fixtures folder, an `.env.example` whose
placeholder was helpfully filled in.

    python scripts/scan_secrets.py             # working tree (tracked files)
    python scripts/scan_secrets.py --staged    # what `git commit` would record
    python scripts/scan_secrets.py --all       # every file git knows about

Exit status is 0 when clean and 1 when anything is found, so it works as a
pre-commit hook (`make hooks` installs it) and as a CI step.

Findings are reported by file, line number and rule, with the matched text
itself masked — this script must never become the thing that prints the secret.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Values that are deliberately fake. A match containing any of these is fine.
PLACEHOLDERS = (
    "REPLACE-ME",
    "example.invalid",
    "example.com",
    "<ingress",
    "<instance",
    "<consumer",
    "<your",
    "your-",
    "changeme",
    "placeholder",
    "dummy",
    "not-a-real",
    "xxx",
    "…",
    "...",
    # Loopback: the local simulator. Documenting how to point at it is not a leak,
    # and the address is the same on every machine.
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
    # Literals the docs use to make the point that the simulator ignores auth.
    "anything",
    "unused",
)

# Hosts a demo repo legitimately mentions.
HOST_ALLOWLIST = (
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
    "github.com",
    "donkey-development-kit.github.io",
    "opentelemetry.io",
    "pypi.org",
    "docs.python.org",
    "www.apache.org",
    "example.invalid",
    "example.com",
    "schemas.mulesoft.com",
)


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    why: str


RULES: tuple[Rule, ...] = (
    Rule(
        "llm-proxy-credential",
        re.compile(
            r"(DONKEY_LLM_PROXY_(?:URL|CLIENT_ID|CLIENT_SECRET|KEY))"
            r"\s*[=:]\s*[\"']?([^\s\"'#]+)",
            re.IGNORECASE,
        ),
        "a governed-proxy credential assigned a concrete value",
    ),
    Rule(
        "anypoint-credential",
        re.compile(
            r"(ANYPOINT_(?:CLIENT_ID|CLIENT_SECRET|ORG_ID|BASE_URL))"
            r"\s*[=:]\s*[\"']?([^\s\"'#]+)",
            re.IGNORECASE,
        ),
        "an Anypoint control-plane credential assigned a concrete value",
    ),
    Rule(
        "toml-credential",
        re.compile(
            r"^\s*(llm_proxy_url|llm_proxy_client_id|llm_proxy_client_secret|"
            r"llm_proxy_key|client_secret|org_id)\s*=\s*[\"']([^\"']+)[\"']",
            re.IGNORECASE | re.MULTILINE,
        ),
        "an .donkey-kit.toml credential key with a concrete value",
    ),
    Rule(
        "anypoint-instance-id",
        re.compile(r"api-instance-\d{4,}", re.IGNORECASE),
        "an Anypoint API instance identifier from a live capture",
    ),
    Rule(
        "envoy-decorator",
        re.compile(r"x-envoy-decorator-operation\s*:", re.IGNORECASE),
        "an Envoy decorator header, which embeds the instance and environment id",
    ),
    Rule(
        "openai-org-project",
        re.compile(
            r"(openai-organization|openai-project)\s*:\s*\S+|proj_[A-Za-z0-9]{16,}",
            re.IGNORECASE,
        ),
        "an OpenAI organization or project identifier from a live capture",
    ),
    Rule(
        "bearer-token",
        re.compile(
            r"(authorization\s*:\s*bearer\s+\S+|sk-[A-Za-z0-9_\-]{20,}|"
            r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.)",
            re.IGNORECASE,
        ),
        "a bearer token, OpenAI-style key, or JWT",
    ),
    Rule(
        "uuid",
        re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            re.IGNORECASE,
        ),
        "a UUID — org, environment and correlation identifiers all take this form",
    ),
    Rule(
        "external-https-host",
        re.compile(r"https://([A-Za-z0-9._\-]+\.[A-Za-z]{2,})"),
        "an external hostname that is not on the allowlist",
    ),
)

# Files where a rule is expected to fire and is not a finding.
EXEMPT: dict[str, tuple[str, ...]] = {
    # This scanner necessarily contains every pattern it looks for.
    "scripts/scan_secrets.py": tuple(r.name for r in RULES),
    # The redaction helper names the headers it masks.
    "_harness/redact.py": ("envoy-decorator", "openai-org-project", "anypoint-instance-id"),
    # Apache-2.0 text links to apache.org.
    "LICENSE": ("external-https-host",),
}

SKIP_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov", ".webm", ".cast", ".pdf")


def _git(*args: str) -> list[str]:
    out = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def _files(mode: str) -> list[str]:
    if mode == "staged":
        return _git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    # Tracked files plus anything untracked that `.gitignore` does not already
    # exclude — i.e. everything a `git add -A` would pick up. Scanning only
    # tracked files would miss a new demo before it is first staged, which is
    # exactly when someone is most likely to have pasted a real value into it.
    tracked = _git("ls-files")
    untracked = _git("ls-files", "--others", "--exclude-standard")
    return sorted(set(tracked) | set(untracked))


def _mask(text: str) -> str:
    """Show enough to locate the finding, never enough to use it."""
    text = text.strip()
    if len(text) <= 12:
        return text[:2] + "*" * max(0, len(text) - 2)
    return f"{text[:6]}…{text[-4:]} ({len(text)} chars)"


def _is_placeholder(text: str) -> bool:
    low = text.lower()
    return any(p.lower() in low for p in PLACEHOLDERS)


def _host_allowed(host: str) -> bool:
    low = host.lower()
    return any(low == h or low.endswith("." + h) for h in HOST_ALLOWLIST)


def scan_file(rel: str) -> list[tuple[int, Rule, str]]:
    path = REPO / rel
    if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    exempt = EXEMPT.get(rel, ())
    findings: list[tuple[int, Rule, str]] = []

    for rule in RULES:
        if rule.name in exempt:
            continue
        for match in rule.pattern.finditer(text):
            hit = match.group(0)
            # Rules that capture a key/value pair judge the value, not the key.
            value = match.group(2) if match.re.groups >= 2 and match.group(2) else hit
            if _is_placeholder(value) or _is_placeholder(hit):
                continue
            if rule.name == "external-https-host" and _host_allowed(match.group(1)):
                continue
            line = text.count("\n", 0, match.start()) + 1
            findings.append((line, rule, _mask(value)))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--staged", action="store_true", help="scan what is staged for commit"
    )
    parser.add_argument("--all", action="store_true", help="scan every tracked file")
    args = parser.parse_args()
    mode = "staged" if args.staged else ("all" if args.all else "tracked")

    total = 0
    for rel in _files(mode):
        for line, rule, masked in scan_file(rel):
            if total == 0:
                print("Potential secrets found — nothing was committed.\n")
            total += 1
            print(f"  {rel}:{line}")
            print(f"    rule   {rule.name} — {rule.why}")
            print(f"    value  {masked}\n")

    if total:
        print(f"{total} finding(s).\n")
        print("If a finding is a false positive, add the file+rule to EXEMPT in")
        print("scripts/scan_secrets.py with a comment saying why it is safe.")
        return 1

    scanned = len(_files(mode))
    print(f"No secrets found in {scanned} {mode} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
