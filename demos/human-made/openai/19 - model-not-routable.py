"""Offline OpenAI reaction: a bare model name on a multi-provider proxy is ModelNotRoutable.

The gateway answers 400 before calling any provider. It is a client config
mistake: not a PolicyViolation, not an UpstreamRequestError, and never retried.
Fix it by sending ``provider/model``.
"""

from donkey_kit import (
    Donkey,
    DonkeyConfig,
    ModelNotRoutable,
    PolicyViolation,
    UpstreamRequestError,
)


def main() -> None:
    config = DonkeyConfig(
        llm_proxy_url="https://demo.example.invalid/",
        llm_proxy_client_id="demo-client-id-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
        max_retries=0,
        telemetry=False,
    )
    with Donkey(config) as donkey:
        client = donkey.openai(sync=True)
        try:
            with donkey.simulate(ModelNotRoutable), donkey.run(id="copyable-routing"):
                client.responses.create(model="gpt-5-mini", input="synthetic input")
        except ModelNotRoutable as exc:
            assert not isinstance(exc, (PolicyViolation, UpstreamRequestError))
            assert exc.correlation_id == "copyable-routing"
            print(f"PASS: ModelNotRoutable for {exc.model!r}; send 'openai/{exc.model}'")
        else:
            raise AssertionError("the simulated 400 was not typed")


if __name__ == "__main__":
    main()
