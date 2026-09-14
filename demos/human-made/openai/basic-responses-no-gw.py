import asyncio

import openai


async def main() -> None:
    # Needs OPENAI_API_KEY in the environment. No base_url, so the SDK's
    client = openai.AsyncOpenAI()

    response = await client.responses.create(
        model="gpt-4o",
        input="Say hello in exactly three words.",
    )

    print(response.output_text)
    await client.close()


asyncio.run(main())