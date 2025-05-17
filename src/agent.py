from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent, ReActAgent
from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import AgentStream, ToolCallResult
from functions import search_perplexity, fft
from tracing import setup_tracing
from prompts import system_prompt
import os
import logging
import asyncio
from llama_index.core import PromptTemplate


# Passes all the API calls to the OpenTelemetry collector 
setup_tracing()

# If the logging level is set to DEBUG, it will print all logs
# which can be overwhelming but useful for seeing the actual
# HTTP calls
logging.basicConfig(level=logging.INFO)

# Note that tools are just functions, but their return values should have 
# a format which can be converted to a short-ish string (<10,000 characters, ideally)
# Examples of return types that would be good: dictionary, list, string, file paths
# Bad types: Numpy array, pandas dataframe (unless calling .to_csv() or .to_json() on them)
tools = [fft, search_perplexity]

async def main(query: str):

    # Set up the OpenAI API key
    # This key is used to authenticate requests to the OpenAI API
    # It should be kept secret and not shared publicly
    # Load the credentials from .env file
    # The .env file should NOT be committed to the repo since
    # it is sensitive and used for API calls
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY") # Won't work unless we call load_dotenv() first

    llm = OpenAI(model="gpt-4o", api_key=openai_api_key)
    agent = ReActAgent(tools=tools, llm=llm)
    agent.update_prompts({"react_header": PromptTemplate(system_prompt)})

    ctx = Context(agent)
        
    handler = agent.run(query, ctx=ctx)

    async for ev in handler.stream_events():
        if isinstance(ev, ToolCallResult):
            print(f"\n(TOOL CALL) Used tool `{ev.tool_name}` with {ev.tool_kwargs}\nReturned: {ev.tool_output}")
        if isinstance(ev, AgentStream):
            print(f"{ev.delta}", end="", flush=True) # Prints the token from the LLM without making a new line every time

    response = await handler
    
if __name__ == "__main__":
    query = "Characterize the signals in the audio file located at ./data/hamilton_ave.m4a by using the fft multiple times on iteratively smaller intervals and use Perplexity to look up possible causes of the signals. This is recording of ambient environmental noise, not music. I want you to try to isolate spectral peaks due to things like people speaking, construction noise, electrical circuits humming, etc. Run the fft multiple times on iteratively smaller intervals."
    asyncio.run(main(query))
