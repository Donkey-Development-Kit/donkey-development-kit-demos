import asyncio

from donkey_kit import Donkey

# Needs donkey-kit[langgraph] and DONKEY_LLM_PROXY_*.
# Async only: the governed transport is ChatOpenAI's http_async_client.
#
# python "demos/human-made/langgraph/02 - basic-gw.py"


async def main() -> None:
    async with Donkey.from_env() as donkey:
        model = donkey.langgraph("gpt-4o")   # native ChatOpenAI on /responses

        reply = await model.ainvoke("Say hello in exactly three words.")

        print(reply.text)
        print("model_name ", reply.response_metadata.get("model_name"))
        print("usage      ", reply.usage_metadata)
        # LangChain calls the model in its own task, so last_call never reaches here.
        print("last_call  ", donkey.last_call.status.value)


asyncio.run(main())
