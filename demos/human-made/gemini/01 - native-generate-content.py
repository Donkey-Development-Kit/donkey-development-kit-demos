import httpx
from donkey_kit import DonkeyConfig

# Needs DONKEY_LLM_PROXY_* pointed at a proxy provisioned Format=Gemini
# (e.g. ddk-gemini-inbound). No Gemini adapter ships, so this is plain httpx
# with the same client_id / client_secret pair.
#
# python "demos/human-made/gemini/01 - native-generate-content.py"

MODEL = "gemini-2.5-flash"

cfg = DonkeyConfig.from_env().validated(need="llm")
headers = {"client_id": cfg.llm_proxy_client_id, "client_secret": cfg.llm_proxy_client_secret}

ok = httpx.post(
    f"{cfg.llm_proxy_url}/models/{MODEL}:generateContent",
    headers=headers,
    json={"contents": [{"role": "user", "parts": [{"text": "Say hello in exactly three words."}]}]},
    timeout=60,
)
ok.raise_for_status()
body = ok.json()
print(body["candidates"][0]["content"]["parts"][0]["text"])
print("total tokens ", body["usageMetadata"]["totalTokenCount"])
print("routing      ", ok.headers.get("x-llm-proxy-model-based-routing-success"))
