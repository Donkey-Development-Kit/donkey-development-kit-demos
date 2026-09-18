import asyncio

import openai


async def main() -> None:
    # Needs OPENAI_API_KEY. No base_url — stock OpenAI, not the gateway.
    client = openai.AsyncOpenAI()

    response = await client.responses.create(
        model="gpt-4o",
        input="Say hello in exactly three words.",
    )

    print(response.output_text)
    await client.close()


asyncio.run(main())