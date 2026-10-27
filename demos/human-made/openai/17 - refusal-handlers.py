"""Offline OpenAI reaction: a fabricated response cannot lift a gateway refusal."""

from donkey_kit import Donkey, DonkeyConfig, PIIDetected, PolicyViolation, classify


class DemoExportBlocked(PolicyViolation):
    """Synthetic custom policy, not a live-verified platform shape."""

    policy = "copyable_demo_export_block"
    remediation = "Keep this synthetic export local and ask its owner to review it."


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
        sink = []
        donkey.on(PIIDetected).escalate(to=sink.append)
        try:
            with donkey.simulate(PIIDetected), donkey.run(id="copyable-escalation"):
                client.responses.create(model="gpt-4o", input="synthetic input")
        except PIIDetected as exc:
            assert exc.correlation_id == "copyable-escalation"
            assert len(sink) == 1 and sink[0].call_id == exc.call_id
        else:
            raise AssertionError("escalation records but must still raise")
        print("ESCALATED: local sink received PIIDetected; caller still refused")

        registration = classify.register(
            match={"status": 403, "error_type": "copyable_demo_export_block"},
            raises=DemoExportBlocked,
        )
        try:
            # Classifier registrations are process-wide; on() handlers are per Donkey.
            donkey.on(DemoExportBlocked).call(lambda ctx: "pretend this succeeded")
            try:
                with donkey.simulate(DemoExportBlocked), donkey.run(id="copyable-custom"):
                    client.responses.create(model="gpt-4o", input="synthetic export")
            except DemoExportBlocked as exc:
                assert exc.remediation == DemoExportBlocked.remediation
            else:
                raise AssertionError("a handler return value cannot manufacture success")
            print("CUSTOM: synthetic policy typed; handler return did not grant permission")
        finally:
            assert classify.unregister(DemoExportBlocked) == (registration,)
        print("CLEANUP: process-wide custom registration removed")
        print("For bounded wait, resend and model fallback, run narrative demo 17.")


if __name__ == "__main__":
    main()
