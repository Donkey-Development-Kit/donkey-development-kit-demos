import asyncio

from agent_framework import Agent
from agent_framework.exceptions import ChatClientException
from donkey_kit import Donkey, DonkeyConfig
from donkey_kit.core.errors import classify

# Needs donkey-kit[agent_framework] and DONKEY_LLM_PROXY_*.
# PIIDetected needs llm-pii-detection-policy with Email and action=Reject (see openai/04).
# Agent Framework wraps the openai error; the response rides on __cause__.
#
# python "demos/human-made/agent-framework/02 - typed-refusals-live.py"

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
    agent = Agent(client=donkey.agent_framework.chat_client(model), name="support")
    try:
        asyncio.run(agent.run(prompt))
        print(name, "NO REFUSAL")
    except ChatClientException as err:
        error = classify(err.__cause__.response)
        print(name, "->", type(error).__name__, getattr(error, "entities", None))
    donkey.close()
