"""Ordinary pytest complement: assert server-log observation and port cleanup."""

import asyncio
import os
import socket
from urllib.parse import urlsplit

import pytest
from agent import build
from donkey_kit import Donkey, DonkeyConfig, PIIDetected
from donkey_kit.conformance.gateway import start_gateway
from donkey_kit.conformance.harness import run_conformance


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    """Never let the SDK resolve a real user or project configuration."""
    for key in os.environ:
        if key.startswith(("DONKEY_", "ANYPOINT_", "OTEL_")):
            monkeypatch.delenv(key)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize("mode", ["in-process", "server"])
def test_agent_conforms(mode):
    """The corrected agent passes all four scenarios in each mode."""
    results = asyncio.run(run_conformance(build, mode=mode))
    assert len(results) == 4
    assert all(row.status == "pass" for row in results), results


def test_server_log_and_cleanup():
    """One terminal refusal makes one real HTTP request; closing releases the port."""
    gateway = start_gateway()
    address = urlsplit(gateway.url)
    assert address.hostname == "127.0.0.1" and address.port

    async def probe():
        async with Donkey(
            DonkeyConfig(
                llm_proxy_url=gateway.url,
                llm_proxy_client_id="unused",
                llm_proxy_client_secret="unused",
                telemetry=False,
            )
        ) as donkey:
            gateway.set_scenarios("pii_block:every=1")
            with pytest.raises(PIIDetected):
                await build(donkey).run("offline probe")
            assert gateway.requests_received == 1

    try:
        asyncio.run(probe())
    finally:
        gateway.close()
    with socket.socket() as connection:
        connection.settimeout(1)
        assert connection.connect_ex((address.hostname, address.port)) != 0
