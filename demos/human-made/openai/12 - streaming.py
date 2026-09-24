from donkey_kit import Donkey

# Needs DONKEY_LLM_PROXY_URL, DONKEY_LLM_PROXY_CLIENT_ID, DONKEY_LLM_PROXY_CLIENT_SECRET
# Live only — mock streaming is truncated SSE, so last_call usage would be a lie.
#
# python "demos/human-made/openai/12 - streaming.py"

donkey = Donkey.from_env()
client = donkey.openai(sync=True)

stream = client.responses.create(
    model="gpt-4o",
    input="Say hello in exactly three words.",
    stream=True,
)
pieces = []
for event in stream:
    if getattr(event, "type", None) == "response.output_text.delta":
        pieces.append(event.delta)

print("".join(pieces))
last = donkey.last_call
print("last_call.status      ", last.status.value)
print("last_call.served_model", last.served_model)
print("last_call.total_tokens", last.total_tokens)

donkey.close()
