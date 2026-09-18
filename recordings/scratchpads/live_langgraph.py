"""A governed LangChain model in two lines, no asyncio and no Donkey context.

`chat_model()` returns a real `langchain_openai.ChatOpenAI`, so typing `model.`
gives you LangChain's entire surface — invoke, stream, bind_tools — already
pointed at the governed proxy.

Live only: ChatOpenAI talks to /chat/completions, which the local simulator does
not serve.
"""

from donkey_kit.integrations.langgraph import chat_model

import _harness  # noqa: F401  — loads .env.local

model = chat_model("gpt-4o")
print(model.invoke("Say hi in three words").content)
