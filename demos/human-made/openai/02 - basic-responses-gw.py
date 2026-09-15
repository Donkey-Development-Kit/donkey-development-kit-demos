import asyncio

from donkey_kit import Donkey, DonkeyConfig
# Needs DONKEY_LLM_PROXY_URL, DONKEY_LLM_PROXY_CLIENT_ID and DONKEY_LLM_PROXY_CLIENT_SECRET

async def main() -> None:
    async with Donkey.from_env() as donkey:
        client = donkey.openai()   # THIS is returning the native openai
        
        response = await client.responses.create(
            model="gpt-4o",
            input="Say hello in exactly three words.",
        )


        print(response.output_text)


asyncio.run(main())
