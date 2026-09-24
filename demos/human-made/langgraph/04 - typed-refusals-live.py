import asyncio

from donkey_kit import Donkey, DonkeyConfig, DonkeyError
from langchain.agents import create_agent

# Needs donkey-kit[langgraph] and DONKEY_LLM_PROXY_*.
# PIIDetected needs llm-pii-detection-policy with Email and action=Reject (see openai/04).
# UpstreamRequestError and AuthError need nothing extra.
#
# python "demos/human-made/langgraph/04 - typed-refusals-live.py"

MODEL = "gpt-4o"
PII_PROMPT = "Summarise this contact record in one line: John Doe, john.doe@example.com, +1 415 555 0132."
cfg = DonkeyConfig.from_env()
bad_cfg = cfg.with_overrides(llm_proxy_client_id="not-a-real-client-id", llm_proxy_client_secret="not-a-real-secret")
CASES = (
    ("PIIDetected", cfg, MODEL, PII_PROMPT),
    ("UpstreamRequestError", cfg, "definitely-not-a-real-model", "Say hello."),
    ("AuthError", bad_cfg, MODEL, "Say hello."),
)


async def main() -> None:
    for name, case_cfg, model, prompt in CASES:
        async with Donkey(case_cfg) as donkey:
            agent = create_agent(donkey.langgraph(model), tools=[])
            async with donkey.run(id=f"lg-live-{name}"):
                try:
                    with donkey.langgraph.typed_refusals():
                        await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})
                    print(name, "NO REFUSAL")
                except DonkeyError as error:
                    print(name, "->", type(error).__name__, getattr(error, "policy", None), getattr(error, "entities", None))


asyncio.run(main())
