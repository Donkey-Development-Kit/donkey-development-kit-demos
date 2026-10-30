"""Serve a deterministic local agent through the real blocking Donkey launcher.

No dotenv, resolved config, authentication, downstream calls or telemetry.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util


def main() -> None:
    """Bind only loopback and block until Ctrl-C requests graceful shutdown."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    for module in ("a2a", "starlette", "uvicorn"):
        if importlib.util.find_spec(module) is None:
            print('Missing prerequisites: pip install "donkey-kit[a2a]"')
            return

    from donkey_kit import A2AResult, A2ATask, Donkey, PIIDetected
    from donkey_kit.core.config import DonkeyConfig

    donkey = Donkey(DonkeyConfig(telemetry=False))

    @donkey.agent(name="localhost-helper", skills=["local-result"])
    async def helper(task: A2ATask) -> A2AResult:
        """Return a deterministic local result or a synthetic typed refusal."""
        if task.input == "refuse":
            # This is a direct synthetic handler refusal, not a gateway response.
            raise PIIDetected("synthetic-handler-detail-not-for-the-caller")
        return A2AResult(
            text="completed locally", data={"correlation_id": task.correlation_id}
        )

    print(
        "LOCAL ONLY: real Donkey.serve listener on 127.0.0.1; no auth or model calls",
        flush=True,
    )
    try:
        donkey.serve(helper, host="127.0.0.1", port=args.port, version="1.0.0")
    except KeyboardInterrupt:
        # uvicorn drains lifespan before re-raising the captured SIGINT.
        pass
    finally:
        asyncio.run(donkey.aclose())
    print("PASS: blocking donkey.serve returned; Donkey transports closed", flush=True)


if __name__ == "__main__":
    main()
