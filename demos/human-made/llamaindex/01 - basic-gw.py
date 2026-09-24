from donkey_kit import Donkey
from llama_index.core.llms import ChatMessage

# Needs donkey-kit[llamaindex] and DONKEY_LLM_PROXY_*. Calls /chat/completions,
# which is not live-verified on DDK proxies (/responses is).
# The adapter sets is_chat_model=True; OpenAILike's default False hits /completions.
# Only default_headers are handed over: no run id and no last_call.
#
# python "demos/human-made/llamaindex/01 - basic-gw.py"

donkey = Donkey.from_env()
llm = donkey.llamaindex.llm("gpt-4o")

print(llm.complete("Say hello in exactly three words.").text)

reply = llm.chat([ChatMessage(role="user", content="Say goodbye in exactly three words.")])
print(reply.message.content)
print("total tokens", reply.raw.usage.total_tokens)
print("last_call   ", donkey.last_call.status.value, donkey.last_call.surface)

donkey.close()
