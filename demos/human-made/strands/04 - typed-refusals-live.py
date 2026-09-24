import asyncio

import openai
from donkey_kit import Donkey, DonkeyConfig
from donkey_kit.core.errors import classify
from strands import Agent
from strands.models.openai import OpenAIModel

# Needs strands-agents[openai] and DONKEY_LLM_PROXY_*.
# PIIDetected needs llm-pii-detection-policy with Email and action=Reject (see openai/04).
#
# python "demos/human-made/strands/04 - typed-refusals-live.py"

PII_PROMPT = "Summarise this contact record in one line: John Doe, john.doe@example.com, +1 415 555 0132."
cfg = DonkeyConfig.from_env()
bad_cfg = cfg.with_overrides(llm_proxy_client_id="not-a-real-client-id", llm_proxy_client_secret="not-a-real-secret")
CASES = (
    ("PIIDetected", cfg, "gpt-4o", PII_PROMPT),
    ("UpstreamRequestError", cfg, "definitely-not-a-real-model", "Say hello."),
    ("AuthError", bad_cfg, "gpt-4o", "Say hello."),
)


async def main() -> None:
    for name, case_cfg, model_id, prompt in CASES:
        async with Donkey(case_cfg) as donkey:
            agent = Agent(model=OpenAIModel(client=donkey.openai(), model_id=model_id), callback_handler=None)
            async with donkey.run(id=f"strands-live-{name}"):
                try:
                    await agent.invoke_async(prompt)
                    print(name, "NO REFUSAL")
                except openai.APIStatusError as err:
                    error = classify(err.response)
                    print(name, "->", type(error).__name__, getattr(error, "entities", None))


asyncio.run(main())
