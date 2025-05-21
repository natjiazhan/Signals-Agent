from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent, ReActAgent
from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import AgentStream, ToolCallResult
from llama_index.core.tools.types import ToolOutput
from functions import search_perplexity, fft, file_meta_data, save_agent_output
from tracing import setup_tracing
from prompts import system_prompt
import os
import logging
import asyncio
from llama_index.core import PromptTemplate
from rich.console import Console
from rich.panel import Panel
from format import format_fft_output_as_rich_table


# Passes all the API calls to the OpenTelemetry collector 
setup_tracing()

# Configure logging
logging.basicConfig(level=logging.WARNING)

# Available tools
tools = [fft, search_perplexity, file_meta_data, save_agent_output]

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
            
            if ev.tool_name == 'fft' and isinstance(ev.tool_output, ToolOutput) and isinstance(ev.tool_output.content, str):
                format_fft_output_as_rich_table(
                    csv_string=ev.tool_output.content,
                    console=console,
                    tool_name=ev.tool_name,
                    tool_kwargs=ev.tool_kwargs
                )
            else:
                # Original way to print tool call result
                output_to_display = ev.tool_output
                if isinstance(ev.tool_output, ToolOutput):
                    output_to_display = ev.tool_output.content

                console.print(Panel(
                    f"Used tool `{ev.tool_name}` with {ev.tool_kwargs}\nReturned: {output_to_display}",
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
    query = """
    Instruction: At the end of your analysis, call the `save_agent_output` function with the following format:

    {
        "summary": "...",
        "structured": {
            "source_type": ["human", "synthesized"]
        }
    }

    Use only these source_type categories: ["human", "synthesized", "machine", "nature", "video game"]. Do not invent your own.

    Example Input:
    This audio shows dominant low-frequency peaks near 392 Hz, with narrow tonal stability over time. It resembles synthetic tones found in video game environments.

    Example Output:
    {
        "summary": "This clip contains synthesized tones resembling video game sound effects. There are stable peaks near 392 Hz consistent with tonal, digital sources.",
        "structured": {
            "source_type": ["synthesized", "video game"]
        }
    }


    Now analyze: ./data/audio1.mp3 using fft (20x20 bins) and Perplexity. Describe the spectral content and determine likely sources. End by calling `save_agent_output` with your result.
    """

    asyncio.run(run_agent(query))
