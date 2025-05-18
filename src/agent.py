from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent, ReActAgent
from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import AgentStream, ToolCallResult
from functions import search_perplexity, fft, file_meta_data, load_audio_clip
from tracing import setup_tracing
from prompts import system_prompt
import os
import logging
import asyncio
from llama_index.core import PromptTemplate
from rich.console import Console
from rich.panel import Panel


# Passes all the API calls to the OpenTelemetry collector 
setup_tracing()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Available tools
tools = [fft, search_perplexity, file_meta_data, load_audio_clip]

async def run_agent(query: str, console: Console = Console()):
    """Run the agent with the given query.
    
    Args:
        query (str): The query or instructions for the agent to process.
        
    Returns:
        The result of the agent's execution.
    """
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    llm = OpenAI(model="o3-mini", api_key=openai_api_key)
    agent = ReActAgent(tools=tools, llm=llm)
    agent.update_prompts({"react_header": PromptTemplate(system_prompt)})

    ctx = Context(agent)
    handler = agent.run(query, ctx=ctx)
    
    # Buffer for accumulating agent stream text
    agent_buffer = ""

    async for ev in handler.stream_events():
        if isinstance(ev, ToolCallResult):
            # If we have accumulated agent text, print it in its own panel first
            if agent_buffer:
                console.print(Panel(
                    agent_buffer,
                    title="Agent Thoughts",
                    style="green",
                    expand=False,
                ))
                agent_buffer = ""  # Clear the buffer
                
            # Then print the tool call result
            console.print(Panel(
                f"Used tool `{ev.tool_name}` with {ev.tool_kwargs}\nReturned: {ev.tool_output}",
                title="Tool Result",
                style="dim",
                border_style="dim",
                expand=False,
            ))
        elif isinstance(ev, AgentStream):
            # Accumulate agent text instead of printing directly
            agent_buffer += ev.delta
    
    # Print any remaining agent text
    if agent_buffer:
        console.print(Panel(
            agent_buffer,
            title="Agent Thoughts",
            style="green",
            expand=False,
        ))

    response = await handler
    
if __name__ == "__main__":
    query = "Use load_audio_clip to get the clip with ID 'fold5_urbansound8k_133.wav' and write it to a file. Then run fft on that audio file using multiple decreasing time intervals to isolate frequency peaks. Use Perplexity to investigate what may cause peaks from audio sources."
    asyncio.run(run_agent(query))
