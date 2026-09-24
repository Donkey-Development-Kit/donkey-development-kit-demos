import openai
from donkey_kit import Donkey
from donkey_kit.core.errors import classify

# Needs DONKEY_LLM_PROXY_* pointed at a proxy with Amazon Bedrock Guardrails
# applied (e.g. ddk-bedrock-guardrails). Same class as Azure in 13.
# Same "NO REFUSAL" path as 04 if the policy is not applied.
#
# python "demos/human-made/openai/16 - bedrock-guardrails.py"

MODEL = "gpt-4o"
PROMPT = "I hate those people and I want to hurt them."

donkey = Donkey.from_env()
client = donkey.openai(sync=True)

print("\n=== ContentSafetyBlocked  (Bedrock)")
with donkey.run(id="live-bedrock-guardrails"):
    try:
        client.responses.create(model=MODEL, input=PROMPT)
        print("NO REFUSAL")
    except openai.APIStatusError as err:
        error = classify(err.response)
        print(type(error).__name__, getattr(error, "policy", None), getattr(error, "categories", None))
        print("message       ", error)
        # Bedrock's own id rides x-amzn-requestid, not x-request-id.
        print("x-request-id  ", err.response.headers.get("x-request-id"))
        print("request_id    ", error.request_id)
    except openai.APIConnectionError as err:
        print("UNREACHABLE", type(err.__cause__ or err).__name__)

donkey.close()
