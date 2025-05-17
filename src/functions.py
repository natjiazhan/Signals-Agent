from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

pplx_system_prompt = "You are a helpful assistant."

def search_perplexity(
    query: str,
    model: str = "sonar-pro"
) -> str:
    """
    Queries Perplexity API for LLM-powerered web search. This is generally useful
    for a range of tasks.
    
    Args:
        query: User question/prompt
        system_prompt: System role definition (default: helpful assistant)
        model: Perplexity model. Options are `sonar`, `sonar-pro`, and `sonar-deep-research`.
        Use sonar-pro for most tasks, sonar for simple tasks, and sonar-deep-research
        for deep research tasks.
    Returns:
        Formatted answer string with inline citations and source URLs
    """
    client = OpenAI(
        api_key=os.getenv("PPLX_API_KEY"),
        base_url="https://api.perplexity.ai"
    )
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": pplx_system_prompt},
            {"role": "user", "content": query}
        ]
    )
    
    content = response.choices[0].message.content
    citations = getattr(response, 'citations', [])
    
    # Add source URLs if citations exist
    if citations:
        sources = "\n".join([f"[{i+1}] {c}" for i, c in enumerate(citations)])
        return f"{content}\n\nSources:\n{sources}"
    
    return content

if __name__ == "__main__":
    # Example usage
    query = "Who won the 2024 Men's Olympic soccer finals match"
    answer = get_perplexity_answer(query)
    print(answer)


import subprocess
import pandas as pd
from pathlib import Path
from audio2numpy import open_audio
import numpy as np

# Load the audio file
input_file = Path("Hamilton Ave.m4a")
wav_file = input_file.with_suffix('.wav')

#Convert to WAV format
subprocess.run(['ffmpeg', '-i', str(input_file), str(wav_file)], check=True)

signal, sample_rate = open_audio(str(wav_file))

# Convert to mono if stereo
if signal.ndim == 2:
    signal = np.mean(signal, axis=1)

#define the fft function
def fft(signal, sample_rate, cutoff_lo, cutoff_hi, bins=20):
    fft_result = np.fft.fft(signal)
    freqency = np.fft.fftfreq(len(signal), d=1/sample_rate)
    power = np.abs(fft_result)**2

    #only keep the frequencies within the cutoff range
    mask = (freqency >= cutoff_lo) & (freqency <= cutoff_hi)
    freqency = freqency[mask]
    power = power[mask]

    #bin the frequencies and power
    bin_edges = np.linspace(cutoff_lo, cutoff_hi, bins + 1)
    bin_labels = [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}Hz" for i in range(bins)]
    binned_power = np.zeros(bins)

    #Bin the power
    indices = np.digitize(freqency, bin_edges) - 1
    for i in range(len(freqency)):
        if 0 <= indices[i] < bins:
            binned_power[indices[i]] += power[i]

    #Normalize the binned power
    binned_power /= np.sum(binned_power)

    #output datafram string fromatted as a CSV
    df = pd.DataFrame({
        'Frequency bin': bin_labels,
        'Spectral Power': binned_power
    })
    return df.to_csv(index=False, float_format="%.3f")
#Test for FFT function
##if __name__ == "__main__":
    ##cutoff_lo = 0
    ##cutoff_hi = 2000
    ##bins = 20
    ##df = fft(signal, sample_rate, cutoff_lo, cutoff_hi, bins)
    ##print(df)

#Test for raw audio to signal conversion
##if __name__ == "__main__":
    #Extract name from file path
    ##file_name = os.path.splitext(os.path.basename(input_file))[0]

    #Create output file name
    ##output_file = f"signal_{file_name}.csv"

    #Output the signal to a CSV file
    ##np.savetxt(output_file, signal, delimiter=",", header=f"SampleRate: {sample_rate}", comments='')