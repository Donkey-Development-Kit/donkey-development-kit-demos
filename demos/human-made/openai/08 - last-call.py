from donkey_kit import Donkey, ModelSubstituted

# Needs DONKEY_LLM_PROXY_URL, DONKEY_LLM_PROXY_CLIENT_ID, DONKEY_LLM_PROXY_CLIENT_SECRET
#
# python "demos/human-made/openai/08 - last-call.py"

donkey = Donkey.from_env()
client = donkey.openai(sync=True)

print("before any call ", donkey.last_call.status.value)

reply = client.responses.create(model="gpt-4o", input="Say hello in exactly three words.")
print(reply.output_text)

last = donkey.last_call
print("status          ", last.status.value)
print("request_id      ", last.request_id)
print("requested_model ", last.requested_model)
print("served_model    ", last.served_model)
print("served_provider ", last.served_provider)
print("routing_type    ", last.routing_type)
print("fallback        ", last.fallback)
print("substituted     ", last.substituted)
print("total_tokens    ", last.total_tokens)
print("cached_tokens   ", last.cached_tokens)
print("reasoning_tokens", last.reasoning_tokens)

donkey.close()

print("\n=== on_model_substitution='raise'")
strict = Donkey.from_env(on_model_substitution="raise")
strict_client = strict.openai(sync=True)
try:
    strict_client.responses.create(model="gpt-4o", input="Say hello in exactly three words.")
    print("NO RAISE  substituted", strict.last_call.substituted)
except Exception as err:
    hit = err if isinstance(err, ModelSubstituted) else err.__cause__
    if not isinstance(hit, ModelSubstituted):
        raise
    print("RAISED            ", type(err).__name__)
    print("cause             ", type(hit).__name__)
    print("requested_model   ", hit.requested_model)
    print("served_model      ", hit.served_model)
    print("last_call.substituted", strict.last_call.substituted)

strict.close()
