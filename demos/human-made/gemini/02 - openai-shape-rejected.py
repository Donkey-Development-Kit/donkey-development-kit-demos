import httpx
from donkey_kit import DonkeyConfig
from donkey_kit.core.errors import classify

# Needs DONKEY_LLM_PROXY_* pointed at a proxy provisioned Format=Gemini.
# An OpenAI-shaped request comes back as Gemini's list envelope; classify()
# types it UpstreamRequestError (0.1.0.dev9+), not a policy refusal.
#
# python "demos/human-made/gemini/02 - openai-shape-rejected.py"

cfg = DonkeyConfig.from_env().validated(need="llm")
headers = {"client_id": cfg.llm_proxy_client_id, "client_secret": cfg.llm_proxy_client_secret}

bad = httpx.post(
    f"{cfg.llm_proxy_url}/chat/completions",
    headers=headers,
    json={"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "hello"}]},
    timeout=60,
)
error = classify(bad)
print(type(error).__name__, bad.status_code, getattr(error, "code", None), getattr(error, "error_type", None))
print(error)
