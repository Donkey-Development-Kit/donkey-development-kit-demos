import asyncio

from donkey_kit import Donkey

# Needs donkey-kit[anthropic] and DONKEY_LLM_PROXY_* pointed at a proxy
# provisioned Format=Anthropic (e.g. ddk-anthropic-inbound). The default DDK
# proxies are Format=OpenAI and 404 on /v1/messages.
#
# python "demos/human-made/anthropic/01 - native-messages.py"

MODEL = "claude-haiku-4-5-20251001"


async def main() -> None:
    async with Donkey.from_env() as donkey:
        client = donkey.anthropic.client()   # native AsyncAnthropic, POST /v1/messages

        raw = await client.messages.with_raw_response.create(
            model=MODEL,
            max_tokens=32,
            messages=[{"role": "user", "content": "Say hello in exactly three words."}],
        )
        print(raw.parse().content[0].text)

        last = donkey.last_call
        print("served_provider", last.served_provider)
        print("served_model   ", last.served_model)
        print("input_tokens   ", last.input_tokens)
        print("output_tokens  ", last.output_tokens)
        # Anthropic's id is `request-id`, which last_call does not read yet.
        print("request-id     ", raw.headers.get("request-id"))
        print("request_id     ", last.request_id)


asyncio.run(main())
