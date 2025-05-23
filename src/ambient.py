import numpy as np
import time
from functions import record_audio, fft
from agent import run_agent
from openai import OpenAI
from rich.console import Console
import io
import csv
import os
import asyncio

console = Console()

# Check to see if audio is interesting
def compute_avg_energy(fft_csv):
    reader = csv.reader(io.StringIO(fft_csv))
    header = next(reader)
    rows = list(reader)

    if not rows:
        return 0

    energy_vals = []
    for row in rows:
        try:
            values = [float(x) for x in row[1:]]
            energy_vals.append(sum(values))
        except:
            pass

    return np.mean(energy_vals)

# First pass using GPT-4o to check if the audio is interesting
def prelim_gpt4o(clip_path, summary_text):
    openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"""Does the following audio description indicate anything unusual, human, synthesized, or structured worth analyzing?

    Description: {summary_text}

    Answer only YES or NO.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",  # GPT-4o-mini
        messages=[{"role": "user", "content": prompt}]
    )
    return "yes" in response.choices[0].message.content.lower()

async def ambient_loop(
    threshold=1.2, # % of baseline to trigger event
    monitor_duration=10, # short clip to determine if interesting (sec)
    analysis_duration=300, # if interesting, long clip to analyze (sec)
    freq_range=(0, 2000), # frequency range for analysis
    check_interval=10, # seconds between checks
):
    console.print("[bold blue] Entering Ambient Monitoring Mode... (Escape using Ctrl+C)[/bold blue]")
    history = []

    while True:
        # Step 1: Short recording
        clip_path = record_audio(duration=monitor_duration)
        fft_csv = fft(
            file_path=clip_path,
            cutoff_lo=freq_range[0],
            cutoff_hi=freq_range[1],
            time_bins=4,
            freq_bins=1
        )

        # Step 2: Rolling average change detection
        energy = compute_avg_energy(fft_csv)
        history.append(energy)
        if len(history) > 5:
            history.pop(0)

        avg_prev = np.mean(history[:-1]) if len(history) > 1 else 0
        ratio = energy / avg_prev if avg_prev else 1

        console.print(f"[dim]Rolling energy ratio: {ratio:.2f}[/dim]")

        if ratio > threshold:
            console.print("[bold yellow] Intensity spike detected. Recording longer clip...")
            # Step 3: Longer clip
            clip_path = record_audio(duration=analysis_duration)

            # Step 4: Quick summary check (bypass full agent)
            summary_csv = fft(
                file_path=clip_path,
                cutoff_lo=freq_range[0],
                cutoff_hi=freq_range[1],
                time_bins=6,
                freq_bins=20
            )

            # Wrap for GPT-4o analysis
            short_summary = f"The signal summary from this 5-min segment: \n{summary_csv[:300]}..."
            interesting = prelim_gpt4o(clip_path, short_summary)

            if interesting:
                console.print("[bold green] Triggering full spectral analysis...")
                try:
                    await run_agent(
                        query=f"Analyze the audio file at {clip_path} and identify key spectral features. Use FFT and Perplexity.",
                        console=console
                    )
                except asyncio.CancelledError:
                    console.print("\n[!] Agent analysis cancelled by user.", style="bold red")
                    return
            else:
                console.print("[bold dim]No significant patterns. Returning to monitoring...")

        time.sleep(check_interval)  # wait before next round

if __name__ == "__main__":
        try:
            asyncio.run(ambient_loop())
        except KeyboardInterrupt:
            print("\n[!] Ambient monitoring stopped by user.")
