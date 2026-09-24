import asyncio

from donkey_kit import Donkey
from strands import Agent
from strands.models.openai import OpenAIModel

# Needs strands-agents[openai] and DONKEY_LLM_PROXY_*. Calls /chat/completions,
# which is not live-verified on DDK proxies (/responses is).
# Not donkey.strands.model(): Strands opens and closes an OpenAI client per request
# from client_args, which closes the shared transport after the first call.
# A pre-built client= is reused and left open.
#
# python "demos/human-made/strands/01 - basic-gw.py"


async def main() -> None:
    async with Donkey.from_env() as donkey:
        model = OpenAIModel(client=donkey.openai(), model_id="gpt-4o")
        agent = Agent(model=model, callback_handler=None, system_prompt="Answer in one short sentence.")

        result = await agent.invoke_async("Say hello in exactly three words.")

        print(str(result).strip())
        print("usage       ", result.metrics.accumulated_usage)
        last = donkey.last_call
        print("status      ", last.status.value)
        print("served_model", last.served_model)


asyncio.run(main())
