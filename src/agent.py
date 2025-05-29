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
import glob


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
    I want you to analyze an audio file and describe its spectral content. I want you to determine the likely sources of the audio based on its frequency characteristics and the context of the examples provided. I will walk you through some reasoning to help you do so. There are also tools at your disposal.

    Example Inputs and Outputs

    Example 1 Input:
    This audio shows dominant low-frequency peaks near 392 Hz, with narrow tonal stability over time. It resembles synthetic tones found in video game environments.

    Example 1 Output:
    {
        "summary": "This clip contains synthesized tones resembling video game sound effects. There are stable peaks near 392 Hz consistent with tonal, digital sources.",
        "structured": {
            "source_type": ["synthesized", "video game"]
        }
    }

    Example 2 Input:
    The signal includes periodic broadband bursts around 30 Hz and layered noise throughout. The waveform resembles crowd cheering in a stadium.

    Example 2 Output:
    {
        "summary": "This clip features crowd noise and cheering, consistent with a stadium environment. Energy appears in low and mid-band bursts.",
        "structured": {
            "source_type": ["cheering", "crowd"]
        }
    }

    Example 3 Input:
    This recording contains irregular bursts between 250–500 Hz and long ambient tonal noise near 60 Hz. Matches urban street conditions.

    Example 3 Output:
    {
        "summary": "This clip was recorded on a street with cars, honking, human voices, and mechanical beeps. Low-frequency ambient hum present.",
        "structured": {
            "source_type": ["street", "cars", "horns", "human", "beeping"]
        }
    }

    Example 4 Input:
    Sharp high-frequency tonal peaks repeating every second, plus short impulses typical of keystrokes. FFT stable at 2.5–3 kHz.

    Example 4 Output:
    {
        "summary": "This audio is dominated by keyboard typing. Consistent short pulses suggest machine-generated input.",
        "structured": {
            "source_type": ["keyboard", "typing", "machine"]
        }
    }

    Example 5 Input:
    Broadband continuous signal with distinct chirps and frequency sweeps around 1–4 kHz, consistent with bird calls.

    Example 5 Output:
    {
        "summary": "This clip contains nature sounds including bird songs and forest ambiance.",
        "structured": {
            "source_type": ["bird", "nature", "forest"]
        }
    }

    Example 6 Input:
    Repeating tonal bursts at 400–900 Hz, and background ambient tones with sudden transients typical of construction sites.

    Example 6 Output:
    {
        "summary": "This clip was recorded near a construction site with heavy machinery and motor noise.",
        "structured": {
            "source_type": ["construction", "machine", "heavy machinery"]
        }
    }

    Example 7 Input:
    Strong periodic signals below 100 Hz, subtle mid-band beeps, and noisy artifacts. Possibly an elevator environment.

    Example 7 Output:
    {
        "summary": "This clip was taken inside an elevator. It includes mechanical sounds and elevator beeping.",
        "structured": {
            "source_type": ["elevator", "machine", "motor", "beeping"]
        }
    }

    Example 8 Input:
    Tonal content includes piano harmonics and soft brass notes. Clear harmonic structure between 250–2,000 Hz.

    Example 8 Output:
    {
        "summary": "This clip contains classical music with piano and brass instruments.",
        "structured": {
            "source_type": ["music", "classical", "piano", "brass"]
        }
    }

    Example 9 Input:
    Consistent wideband noise at 400–600 Hz. Speech modulations suggest multiple humans talking in overlapping intervals.

    Example 9 Output:
    {
        "summary": "This clip was taken in a call center with overlapping human conversations.",
        "structured": {
            "source_type": ["human", "office"]
        }
    }

    Example 10 Input:
    High-energy bursts between 4–7 kHz and repetitive peaks. Matches fire crackling patterns.

    Example 10 Output:
    {
        "summary": "This audio was recorded near a fireplace with crackling wood sounds.",
        "structured": {
            "source_type": ["fireplace", "crackling", "wood"]
        }
    }

    Example 11 Input:
    Layered low-frequency rumble and intermittent tonal peaks from motors and warning beeps.

    Example 11 Output:
    {
        "summary": "Construction machinery and backup alarms dominate this audio.",
        "structured": {
            "source_type": ["machine", "construction", "beeping"]
        }
    }

    Example 12 Input:
    Intermittent tones from an elevator chime, mechanical vibration bursts, and echoey midtones.

    Example 12 Output:
    {
        "summary": "Elevator sounds with motor hum and floor change tones are heard.",
        "structured": {
            "source_type": ["elevator", "machine", "motor"]
        }
    }

    Example 13 Input:
    Midband sine waves forming a melody, repeating in fixed intervals. Matches synthesized audio patterns.

    Example 13 Output:
    {
        "summary": "Synthesized piano music with repeating tone structure and calm melody.",
        "structured": {
            "source_type": ["synthesized", "music"]
        }
    }

    Example 14 Input:
    Dense broadband bursts with regular gaps. Tonal content resembles energetic electronic music.

    Example 14 Output:
    {
        "summary": "This clip contains upbeat electronic dance music with synthesized beats.",
        "structured": {
            "source_type": ["electronic", "dance", "music", "synthesized"]
        }
    }

    Example 15 Input:
    Continuous low-frequency hum, broadband tonal fluctuations, overlapping speech patterns, and clicking.

    Example 15 Output:
    {
        "summary": "Recorded in a call center environment with phones ringing and people talking.",
        "structured": {
            "source_type": ["human", "office", "phone", "ringing"]
        }
    }

    Example 16 Input:
    High frequency chirps between 2–5 kHz and wave-like broad energy bands. Matches ocean wave and seagull profiles.

    Example 16 Output:
    {
        "summary": "Beach environment with seagulls squawking and waves crashing on shore.",
        "structured": {
            "source_type": ["beach", "waves", "seagulls"]
        }
    }

    Example 17 Input:
    Wideband audio with rumbling, frequent pops, and rising tonal ramps. Consistent with thunderstorm activity.

    Example 17 Output:
    {
        "summary": "This clip contains thunder rumbling, rainfall, and distant lightning strikes.",
        "structured": {
            "source_type": ["thunderstorm", "rain", "thunder", "lightning"]
        }
    }

    Example 18 Input:
    Vocal-like tone contours repeating in two turns, consistent harmonic spacing.

    Example 18 Output:
    {
        "summary": "This clip contains two artificial voices talking to each other.",
        "structured": {
            "source_type": ["synthesized", "artificial", "voices", "conversation"]
        }
    }
    Reasoning: I have been given an audio file to analyze. I will use the file_meta_data tool to extract relevant characteristics of the audio file. It seems that this audio file is 5 minutes in duration. I will now use the fft tool to do spectral analysis. Since the duration of this audio file is 5 minutes I should start with a broad analysis first. To go deeper, I’ll perform multiple FFTs at different resolutions. I'll vary the time and frequency bin sizes to capture both short, transient events and longer, sustained trends. I'll do shorter time windows that will help me catch brief, sharp peaks like clicks or speech fragments. I'll use longer windows to reveal slower or more continuous signals like machinery hums or background noise. I’ll pay close attention to how peaks and energy distributions change over time, which can tell me whether the source is static or dynamic. I will use as many combinations of these FFTs as I need to fully understand the audio file. By layering insights from metadata, multiscale FFTs, and time-frequency patterns, I can build a clear understanding of what’s happening in the audio and where each signal component might be coming from.

    Produce an output in the following format:
    {
        "summary": "...",
        "structured": {
            "source_type": ["..."]
        }
    }
    
    Now analyze: ./data/audio20.mp3. This audio file contains a keyboard typing. Describe the spectral content and determine likely sources. End by calling `save_agent_output` with your result.
    """


    asyncio.run(run_agent(query))