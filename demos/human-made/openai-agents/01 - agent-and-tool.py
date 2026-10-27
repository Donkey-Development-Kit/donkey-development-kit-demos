import asyncio

from agents import Agent, OpenAIResponsesModel, Runner, function_tool, set_tracing_disabled
from donkey_kit import Donkey

# Needs donkey-kit[openai-agents] and DONKEY_LLM_PROXY_*.
# OpenAIResponsesModel keeps the agent on the verified /responses route;
# donkey.openai_agents.model() builds a chat-completions model instead.
#
# python "demos/human-made/openai-agents/01 - agent-and-tool.py"

set_tracing_disabled(True)   # no export to api.openai.com


@function_tool
def get_weather(city: str) -> str:
    """Return the weather for a city."""
    return f"Sunny and 21C in {city}."


async def main() -> None:
    async with Donkey.from_env() as donkey:
        model = OpenAIResponsesModel(model="gpt-4o", **donkey.openai_agents.connection_kwargs())
        agent = Agent(
            name="weather",
            instructions="Answer in one short sentence. Use the tool for weather.",
            model=model,
            tools=[get_weather],
        )

        async with donkey.run(id="agents-sdk-weather"):
            result = await Runner.run(agent, "What is the weather in Paris?")

        print(result.final_output)
        print("model calls ", result.context_wrapper.usage.requests)
        print("total_tokens", result.context_wrapper.usage.total_tokens)
        # First turns and streamed runs use Runner's task; later non-streamed
        # turns can be visible here. Use on_llm_end for first-turn observation
        # (see 05 - governed-observations.py), not blanket caller visibility.
        print("last_call   ", donkey.last_call.status.value)


asyncio.run(main())
