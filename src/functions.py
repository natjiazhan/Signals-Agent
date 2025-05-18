from openai import OpenAI
from dotenv import load_dotenv
import os
import subprocess
import pandas as pd
from pathlib import Path
from audio2numpy import open_audio
import numpy as np

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


# Define the file meta data tool
def file_meta_data(file_path: str) -> str:
    """
    Extracts metadata from an audio file using ffprobe. Use this at the beginning of analysis
    to characterize the audio file and understand its properties.
    
    Args:
        file_path: Path to the input audio file (e.g., .m4a).
    
    Returns:
        A CSV-formatted string containing:
        - 'Property': Metadata property name
        - 'Value': Corresponding value of the property
    """
    # Use ffprobe to extract metadata
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,bit_rate,size', '-of', 'default=noprint_wrappers=1:nokey=1', file_path], capture_output=True, text=True)
    
    # Parse the output
    lines = result.stdout.strip().split('\n')
    properties = ['Duration (seconds)', 'Bit Rate (kbps)', 'Size (bytes)']
    
    # Create a DataFrame and return as CSV
    df = pd.DataFrame({
        'Property': properties,
        'Value': lines
    })
    
    return df.to_csv(index=False)

# Test for file_meta_data function
##if __name__ == "__main__":
    ##file_path = "hamilton_ave.m4a"
    ##df = file_meta_data(file_path)
    ##print(df)


# Define the fft tool
def fft(file_path, cutoff_lo, cutoff_hi, start_sec=0, end_sec=None, time_bins=5, freq_bins=15):
    file_path: str
    cutoff_hi: float
    cutoff_lo: float
    start_sec: float
    end_sec: float
    time_bins: int
    freq_bins: int
    """
    Computes a time-frequency spectrogram as a CSV-formatted string.

    This function converts an input audio file to WAV, extracts a segment between start_sec and end_sec,
    computes the FFT for each time window, bins the spectral power into frequency bins, and returns
    a CSV-formatted string representing time-frequency energy.

    Args:
        file_path: Path to the input audio file (e.g., .m4a).
        cutoff_lo: Lower bound of the frequency range to analyze (in Hz).
        cutoff_hi: Upper bound of the frequency range to analyze (in Hz).
        start_sec: Start time of the audio segment to analyze (in seconds).
        end_sec: End time of the audio segment to analyze (in seconds).
        time_bins: Number of equal-width time segments between start and end (default: 10).
        freq_bins: Number of equal-width frequency bins (default: 20).

    Returns:
        - A CSV-formatted string where rows are time slices and columns are frequency bins. Rows are normalized to sum to one, i.e. we normalize the spectral energy in each time slice to 1.

    Notes:
        - Stereo audio is automatically converted to mono.
        - Uses power spectrum magnitude (|FFT|²) as the measure of spectral energy.
    """

    # Load the audio file
    input_file_path = Path(file_path)
    wav_file = input_file_path.with_suffix('.wav')

    #Convert to WAV format
    subprocess.run(['ffmpeg', '-y', '-i', str(input_file_path), str(wav_file)], 
                  stdout=subprocess.DEVNULL, 
                  stderr=subprocess.DEVNULL, 
                  check=True)

    signal, sample_rate = open_audio(str(wav_file))

    # Convert to mono if stereo
    if signal.ndim == 2:
        signal = np.mean(signal, axis=1)

    # Trim the signal to the specified time range
    start_sample = int(start_sec * sample_rate)
    
    if not end_sec:
        end_sec = len(signal) / sample_rate
        
    end_sample = int(end_sec * sample_rate)
    signal = signal[start_sample:end_sample]

    #Time binning setup
    total_samples = len(signal)
    window_size = int(total_samples / time_bins)

    #Frequency bin setup
    bin_edges = np.linspace(cutoff_lo, cutoff_hi, freq_bins + 1)
    bin_labels = [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}Hz" for i in range(freq_bins)]

    spectrogram = []

    #Slide window over signal
    for w in range(time_bins):
        start = w * window_size
        end = start + window_size
        windowed_signal = signal[start:end]

        # Perform FFT on the windowed signal
        fft_result = np.fft.fft(windowed_signal)
        frequency = np.fft.fftfreq(len(windowed_signal), d=1/sample_rate)
        power = np.abs(fft_result)**2

        #only keep the frequencies within the cutoff range
        mask = (frequency >= cutoff_lo) & (frequency <= cutoff_hi)
        frequency = frequency[mask]
        power = power[mask]

        #bin the frequencies and power
        indices = np.digitize(frequency, bin_edges) - 1
        binned_power = np.zeros(freq_bins)

        for i in range(len(frequency)):
            if 0 <= indices[i] < freq_bins:
                binned_power[indices[i]] += power[i]

        #Normalize the binned power
        binned_power /= np.sum(binned_power) if np.sum(binned_power) > 0 else 1

        # Append time-stamped row
        time_stamp = round(start_sec + w * ((end_sec - start_sec) / time_bins), 2)
        spectrogram.append([f"{time_stamp:.2f}s"] + list(binned_power))

    # Create DataFrame and convert to CSV string
    df = pd.DataFrame(spectrogram, columns=["Time"] + bin_labels)
    return df.to_csv(index=False, float_format="%.3f")

if __name__ == "__main__":
    # Example usage
    #csv_str = fft("hamilton_ave.m4a", cutoff_lo=0, cutoff_hi=2000, start_sec=0, end_sec=10, time_bins=10, freq_bins=20)
    #print(csv_str)
    print(file_meta_data("./data/hamilton_ave.m4a"))

##if __name__ == "__main__":
    # Example usage
    ##query = "Who won the 2024 Men's Olympic soccer finals match"
    ##answer = search_perplexity(query)
    ##print(answer)


#Test for spectrogram function
##if __name__ == "__main__":
    ##csv_str = fft("Hamilton Ave.m4a", cutoff_lo=0, cutoff_hi=2000, start_sec=0, end_sec=10, bins=20)
    ##print(csv_str)

#Test for raw audio to signal conversion
##if __name__ == "__main__":
    #Extract name from file path
    ##file_name = os.path.splitext(os.path.basename(input_file))[0]

    #Create output file name
    ##output_file = f"signal_{file_name}.csv"

    #Output the signal to a CSV file
    ##np.savetxt(output_file, signal, delimiter=",", header=f"SampleRate: {sample_rate}", comments='')
