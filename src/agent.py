from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import AgentStream, ToolCallResult
from llama_index.core.agent.react.formatter import ReActChatFormatter
from functions import search_perplexity
from prompts import system_prompt

import os
import logging

# If the logging level is set to DEBUG, it will print all logs
# which can be overwhelming but useful for seeing the actual
# HTTP calls
logging.basicConfig(level=logging.DEBUG)

# Define tools here; these are just placeholders
def multiply(a: int, b: int) -> int:
    """Multiply two integers and returns the result integer"""
    return a * b

def add(a: int, b: int) -> int:
    """Add two integers and returns the result integer"""
    return a + b

# Note that tools are just functions, but their return values should have 
# a format which can be converted to a short-ish string (<10,000 characters, ideally)
# Examples of return types that would be good: dictionary, list, string, file paths
# Bad types: Numpy array, pandas dataframe (unless calling .to_csv() or .to_json() on them)
tools = [multiply, add, search_perplexity]

async def main():

    # Set up the OpenAI API key
    # This key is used to authenticate requests to the OpenAI API
    # It should be kept secret and not shared publicly
    # Load the credentials from .env file
    # The .env file should NOT be committed to the repo since
    # it is sensitive and used for API calls
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY") # Won't work unless we call load_dotenv() first

    llm = OpenAI(model="gpt-4o", api_key=openai_api_key)
    formatter = ReActChatFormatter.from_defaults()
    formatter.system_header = system_prompt
    agent = ReActAgent(tools=tools, llm=llm, formatter=formatter)

    # Create a context to store the conversation history/session state
    ctx = Context(agent)
    
    query = "Find the product of Earth's population with the number of atoms in an apple"
    
    handler = agent.run(query, ctx=ctx)

    async for ev in handler.stream_events():
        if isinstance(ev, ToolCallResult):
            print(f"\n(TOOL CALL) Used tool `{ev.tool_name}` with {ev.tool_kwargs}\nReturned: {ev.tool_output}")
        if isinstance(ev, AgentStream):
            print(f"{ev.delta}", end="", flush=True) # Prints the token from the LLM without making a new line every time

    response = await handler
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
