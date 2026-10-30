"""Assert static registration contracts without importing code or publishing."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
SERVER = HERE / "server"


def cli(command: str, path: Path) -> tuple[int, dict, str]:
    """Run only scan or publish dry-run with no ambient SDK configuration."""
    assert command in ("scan", "publish")
    with TemporaryDirectory(prefix="ddk-offline-home-") as home:
        env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT") if key in os.environ}
        env.update(
            HOME=home,
            XDG_CONFIG_HOME=home,
            ANYPOINT_ORG_ID="demo-org-id-not-a-real-org",
            NO_COLOR="1",
        )
        args = [
            sys.executable,
            "-c",
            "from donkey_kit.cli import main; main()",
            command,
            str(path),
            "--json",
        ]
        if command == "publish":
            args.append("--dry-run")
        result = subprocess.run(args, cwd=home, env=env, text=True, capture_output=True)
        assert result.stdout, result.stderr
        return result.returncode, json.loads(result.stdout), result.stdout


def verify(report: Callable[[str], None] = print) -> None:
    """Fail loudly if scan, declaration validation or digest behavior regresses."""
    for command in ("scan", "publish"):
        code, data, text = cli(command, SERVER)
        other_code, other, other_text = cli(command, SERVER)
        assert code == other_code == 0, data
        assert data["issues"] == []
        assert data == other and text == other_text, "JSON must be deterministic"
        if command == "scan":
            assert [tool["name"] for tool in data["tools"]] == ["lookup_sku"]
        else:
            assert len(data["assets"]) == 1
            asset = data["assets"][0]
            assert asset["type"] == "mcp" and asset["tools"] == ["lookup_sku"]
            assert asset["version"] == "1.1.0"
            assert asset["name"] == "SKU Lookup MCP Server"
            assert asset["description"].startswith("Looks up a product by its SKU")
            assert asset["protocol_version"] == "2025-06-18"
            assert asset["provider"]["organization"] == "Donkey Development Kit"
            assert asset["documentation"] == "README.md"
            assert asset["endpoint"] == "https://sku-lookup.example.invalid/mcp"
            digest = asset["digest"]
            assert digest.startswith("sha256:") and len(digest) == 71
    report("PASS: deterministic scan and dry-run JSON; one MCP asset with its metadata")

    with TemporaryDirectory(prefix="ddk-registration-") as directory:
        copied = Path(directory) / "server"
        shutil.copytree(SERVER, copied)
        source = copied / "app.py"
        original = source.read_text(encoding="utf-8")
        source.write_text(
            original.replace(
                "from __future__ import annotations",
                "from __future__ import annotations\n"
                'raise RuntimeError("static scan must not execute this module")',
            ),
            encoding="utf-8",
        )
        code, scan, _ = cli("scan", copied)
        assert code == 0 and len(scan["tools"]) == 1, scan
        code, plan, _ = cli("publish", copied)
        assert code == 0 and plan["assets"][0]["digest"] == digest, plan
        source.write_text(
            original.replace("name, price and stock level", "name and price only"),
            encoding="utf-8",
        )
        code, changed, _ = cli("publish", copied)
        assert code == 0 and changed["assets"][0]["digest"] != digest, changed
        source.write_text(original, encoding="utf-8")
        declaration = copied / ".donkey-kit.toml"
        declaration.write_text(
            declaration.read_text(encoding="utf-8").replace('"1.1.0"', '"1.1.1"'),
            encoding="utf-8",
        )
        code, bumped, _ = cli("publish", copied)
        assert code == 0 and bumped["assets"][0]["digest"] == digest, bumped
        assert bumped["assets"][0]["version"] == "1.1.1"
        page = copied / "README.md"
        page.write_text(
            page.read_text(encoding="utf-8") + "\nOne more line.\n", encoding="utf-8"
        )
        code, documented, _ = cli("publish", copied)
        assert code == 0 and documented["assets"][0]["digest"] != digest, documented
    report(
        "PASS: no code execution; description and documentation change digest; version does not"
    )

    for sample, expected in (
        ("invalid_version.toml", "invalid-version"),
        ("unknown_service.toml", "unknown-service"),
        ("invalid_endpoint.toml", "invalid-endpoint"),
    ):
        with TemporaryDirectory(prefix="ddk-invalid-declaration-") as directory:
            copied = Path(directory) / "server"
            shutil.copytree(SERVER, copied)
            shutil.copyfile(HERE / "invalid" / sample, copied / ".donkey-kit.toml")
            code, plan, _ = cli("publish", copied)
            assert code == 1 and expected in {i["kind"] for i in plan["issues"]}, plan
        report(f"PASS: {sample} rejected with {expected}, exit 1")


if __name__ == "__main__":
    verify()
