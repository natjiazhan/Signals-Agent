from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import FunctionAgent, ReActAgent
from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import AgentStream, ToolCallResult
from llama_index.core.tools.types import ToolOutput
from functions import (
    search_perplexity,
    fft,
    stereo_fft,
    overlay_stereo,
    file_meta_data,
    analyze_image,
    save_agent_output,
    zero_crossing_rate,
    autocorrelation,
    envelope_decay,
    spectral_flatness,
    fractal_dimension,
    shannon_entropy
)
from tracing import setup_tracing
from prompts import system_prompt, eval_prompt
import os
import logging
import asyncio
from llama_index.core import PromptTemplate
from rich.console import Console
from rich.panel import Panel
from format import format_fft_output_as_rich_table
import glob


# Passes all the API calls to the OpenTelemetry collector 
setup_tracing()

# Configure logging
logging.basicConfig(level=logging.WARNING)

# Available tools
tools = [
    fft,
    stereo_fft,
    overlay_stereo,
    search_perplexity,
    file_meta_data,
    analyze_image,
    save_agent_output,
    zero_crossing_rate,
    autocorrelation,
    envelope_decay,
    spectral_flatness,
    fractal_dimension,
    shannon_entropy
]

async def run_agent(query: str, console: Console = Console()):
    """Run the agent with the given query.
    
    Args:
        query (str): The query or instructions for the agent to process.
        
    Returns:
        The result of the agent's execution.
    """
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    llm = OpenAI(model="o3-mini", api_key=openai_api_key, temperature=1.2)
    agent = ReActAgent(tools=tools, llm=llm)
    agent.update_prompts({"react_header": PromptTemplate(eval_prompt)}) # change the prompt here for eval or running normally

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
    Now analyze: ./data/audio6.mp3
    Use the image to help give context to the audio file: ./data/audio6.png
    Analyze the audio file using combinations of stereo_fft, zero crossing rate, autocorrelation, envelope and decay analysis, spectral flatness, fractal dimension, and Shannon entropy. Begin with broad fft scans to identify dominant spectral features, then use targeted FFTs with varying time and frequency resolutions to isolate transient versus sustained signals. Use autocorrelation to detect periodicity or rhythmic structures, and zero_crossing_rate to assess noisiness or sharp temporal features.

    Next, run envelope_and_decay to analyze amplitude dynamics, and apply spectral_flatness to assess the tonality versus noisiness of the signal. Use fractal_dimension to measure waveform complexity and shannon_entropy to evaluate information density and randomness. Describe what each tool reveals about the nature of the signal. 
    
    Throughout your analysis, use insights from one tool to guide deeper investigation with others. Describe all spectral content and temporal structure you observe. Based on this evidence, determine the most likely sources of the signal. Stay curious and keep an open mind while exploring the data, continuously question yourself and use the tools however you see fit to uncover the most interesting aspects of the audio.
    End by calling save_agent_output with your result.
    """


    asyncio.run(run_agent(query))
