import os

os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

import openai  # noqa: E402
from donkey_kit import Donkey, DonkeyConfig  # noqa: E402
from donkey_kit.core.errors import classify  # noqa: E402

# Needs donkey-kit[crewai] and DONKEY_LLM_PROXY_*.
# PIIDetected needs llm-pii-detection-policy with Email and action=Reject (see openai/04).
# CrewAI 1.x sends openai/ models through its native OpenAI provider, so the
# openai error keeps its response and classify() can type it.
#
# python "demos/human-made/crewai/02 - typed-refusals-live.py"

PII_PROMPT = "Summarise this contact record in one line: John Doe, john.doe@example.com, +1 415 555 0132."
cfg = DonkeyConfig.from_env()
bad_cfg = cfg.with_overrides(llm_proxy_client_id="not-a-real-client-id", llm_proxy_client_secret="not-a-real-secret")
CASES = (
    ("PIIDetected", cfg, "gpt-4o", PII_PROMPT),
    ("UpstreamRequestError", cfg, "definitely-not-a-real-model", "Say hello."),
    ("AuthError", bad_cfg, "gpt-4o", "Say hello."),
)

for name, case_cfg, model, prompt in CASES:
    donkey = Donkey(case_cfg)
    try:
        donkey.crewai.llm(model).call(prompt)
        print(name, "NO REFUSAL")
    except openai.APIStatusError as err:
        error = classify(err.response)
        print(name, "->", type(error).__name__, getattr(error, "entities", None))
    donkey.close()
