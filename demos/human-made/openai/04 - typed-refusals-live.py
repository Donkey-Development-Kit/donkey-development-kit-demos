
import openai
from donkey_kit import Donkey, DonkeyConfig
from donkey_kit.core.errors import classify

MODEL = "gpt-4-turbo-2024-04-09"
PII_PROMPT = (
    "Summarise this contact record in one line: "
    "John Doe, john.doe@example.com, +1 415 555 0132."
)

cfg = DonkeyConfig.from_env()
donkey = Donkey(cfg)
client = donkey.openai(sync=True)


# 1. UpstreamRequestError — needs nothing: the provider rejects the unknown
#    model and the gateway passes its error straight through.
print("\n=== UpstreamRequestError")
with donkey.run(id="live-refusals-UpstreamRequestError"):
    try:
        raw = client.responses.with_raw_response.create(
            model="definitely-not-a-real-model",
            input="Say hello in exactly three words.",
        )
    except openai.APIStatusError as err:
        error = classify(err.response)
        print(f"  REFUSED        {type(error).__name__} (HTTP {err.response.status_code})")
        print(f"  message        {error}")
        print(f"  policy         {getattr(error, 'policy', None)}")
        print(f"  entities       {getattr(error, 'entities', None)}")
        print(f"  retry_after    {getattr(error, 'retry_after', None)}")
        print(f"  correlation_id {getattr(error, 'correlation_id', None)}")
        print(f"  call_id        {getattr(error, 'call_id', None)}")
    except openai.APIConnectionError as err:
        # Never reached the gateway. OpenAI wraps the transport error; the
        # cause is GatewayUnavailable when the origin is down (see 11).
        print(f"  UNREACHABLE    {type(err.__cause__ or err).__name__}: {err.__cause__ or err}")
    else:
        print(f"  NO REFUSAL     (HTTP {raw.status_code})")
        print(f"  served model   {raw.headers.get('x-llm-proxy-llm-model')}")


# 2. PIIDetected — needs llm-pii-detection-policy 1.0.0 applied, with Email
#    among its entities and action=Reject (the default action, Log, lets it past).
print("\n=== PIIDetected")
with donkey.run(id="live-refusals-PIIDetected"):
    try:
        raw = client.responses.with_raw_response.create(model=MODEL, input=PII_PROMPT)
    except openai.APIStatusError as err:
        error = classify(err.response)
        print(f"  REFUSED        {type(error).__name__} (HTTP {err.response.status_code})")
        print(f"  message        {error}")
        print(f"  policy         {getattr(error, 'policy', None)}")
        print(f"  entities       {getattr(error, 'entities', None)}")
        print(f"  remediation    {getattr(error, 'remediation', None)}")
        print(f"  correlation_id {getattr(error, 'correlation_id', None)}")
        print(f"  call_id        {getattr(error, 'call_id', None)}")
    except openai.APIConnectionError as err:
        print(f"  UNREACHABLE    {type(err.__cause__ or err).__name__}: {err.__cause__ or err}")
    else:
        print(f"  NO REFUSAL     (HTTP {raw.status_code})")
        print(f"  served model   {raw.headers.get('x-llm-proxy-llm-model')}")


# 3. TokenBudgetExceeded — needs llm-token-rate-limit 1.0.2 applied with a tiny
#    maximumTokens. At 10000 tokens/60s this prompt will NOT trip it.
print("\n=== TokenBudgetExceeded")
with donkey.run(id="live-refusals-TokenBudgetExceeded"):
    try:
        raw = client.responses.with_raw_response.create(
            model=MODEL,
            input="Write a detailed three paragraph summary of the water cycle.",
        )
    except openai.APIStatusError as err:
        error = classify(err.response)
        print(f"  REFUSED        {type(error).__name__} (HTTP {err.response.status_code})")
        print(f"  message        {error}")
        print(f"  retry_after    {getattr(error, 'retry_after', None)}")
        print(f"  correlation_id {getattr(error, 'correlation_id', None)}")
        print(f"  call_id        {getattr(error, 'call_id', None)}")
    except openai.APIConnectionError as err:
        print(f"  UNREACHABLE    {type(err.__cause__ or err).__name__}: {err.__cause__ or err}")
    else:
        print(f"  NO REFUSAL     (HTTP {raw.status_code})")
        print(f"  budget window  {raw.headers.get('x-llm-proxy-ratelimit')}")

donkey.close()


# 4. AuthError — needs nothing: client-id-enforcement is always applied, so
#    deliberately wrong consumer credentials are enough to provoke it.
bad_donkey = Donkey(
    cfg.with_overrides(
        llm_proxy_client_id="not-a-real-client-id",
        llm_proxy_client_secret="not-a-real-secret",
    )
)
bad_client = bad_donkey.openai(sync=True)

print("\n=== AuthError")
with bad_donkey.run(id="live-refusals-AuthError"):
    try:
        raw = bad_client.responses.with_raw_response.create(
            model=MODEL,
            input="Say hello in exactly three words.",
        )
    except openai.APIStatusError as err:
        error = classify(err.response)
        print(f"  REFUSED        {type(error).__name__} (HTTP {err.response.status_code})")
        print(f"  message        {error}")
        print(f"  correlation_id {getattr(error, 'correlation_id', None)}")
        print(f"  call_id        {getattr(error, 'call_id', None)}")
    except openai.APIConnectionError as err:
        print(f"  UNREACHABLE    {type(err.__cause__ or err).__name__}: {err.__cause__ or err}")
    else:
        print(f"  NO REFUSAL     (HTTP {raw.status_code})")

bad_donkey.close()