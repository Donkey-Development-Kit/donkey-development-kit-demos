import openai
from donkey_kit import Donkey, DonkeyConfig
from donkey_kit.core.errors import classify

# Needs donkey-kit[llamaindex] and DONKEY_LLM_PROXY_*.
# PIIDetected needs llm-pii-detection-policy with Email and action=Reject (see openai/04).
# OpenAILike re-raises the openai error as is, so classify() can type it.
#
# python "demos/human-made/llamaindex/02 - typed-refusals-live.py"

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
        donkey.llamaindex.llm(model).complete(prompt)
        print(name, "NO REFUSAL")
    except openai.APIStatusError as err:
        error = classify(err.response)
        print(name, "->", type(error).__name__, getattr(error, "entities", None))
    donkey.close()
