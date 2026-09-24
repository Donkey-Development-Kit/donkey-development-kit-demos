from langchain_openai import ChatOpenAI

# Needs OPENAI_API_KEY. No base_url — stock OpenAI, not the gateway.
#
# python "demos/human-made/langgraph/01 - basic-no-gw.py"

model = ChatOpenAI(model="gpt-4o", use_responses_api=True)
print(model.invoke("Say hello in exactly three words.").text)
