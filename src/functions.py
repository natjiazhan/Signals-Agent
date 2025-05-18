from openai import OpenAI
from dotenv import load_dotenv
import os
import subprocess
import pandas as pd
from pathlib import Path
from audio2numpy import open_audio
import numpy as np
import pyaudio
import wave
import uuid
import time

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
    
    This can also be used to compute the total energy of the audio file over time by setting freq_bins to 1.

    Args:
        file_path: Path to the input audio file (e.g., .m4a).
        cutoff_lo: Lower bound of the frequency range to analyze (in Hz).
        cutoff_hi: Upper bound of the frequency range to analyze (in Hz).
        start_sec: Start time of the audio segment to analyze (in seconds).
        end_sec: End time of the audio segment to analyze (in seconds).
        time_bins: Number of equal-width time segments between start and end (default: 10).
        freq_bins: Number of equal-width frequency bins (default: 20).

    Returns:
        - A CSV-formatted string where rows are time slices and columns are frequency bins. If freq_bins is 1, then the output is a single column of spectral energy. Otherwise, rows are normalized to sum to one, i.e. we normalize the spectral energy in each time slice to 1.

    Notes:
        - Stereo audio is automatically converted to mono.
        - Uses power spectrum magnitude (|FFT|²) as the measure of spectral energy.
    """

    # Load the audio file
    input_file_path = Path(file_path)
    
    # If the file is already WAV, skip conversion
    if input_file_path.suffix.lower() == '.wav':
        wav_file = input_file_path
    else:
        wav_file = input_file_path.with_suffix('.wav')
        # Convert to WAV format
        subprocess.run(['ffmpeg', '-y', '-i', str(input_file_path), str(wav_file)], 
                      #stdout=subprocess.DEVNULL, 
                      #stderr=subprocess.DEVNULL, 
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
        if freq_bins > 1:
            binned_power /= np.sum(binned_power) if np.sum(binned_power) > 0 else 1

        # Append time range label
        start_time = round(start_sec + w * ((end_sec - start_sec) / time_bins), 2)
        end_time = round(start_time + ((end_sec - start_sec) / time_bins), 2)
        time_label = f"{start_time:.2f}-{end_time:.2f}sec"
        spectrogram.append([time_label] + list(binned_power))

    # Create DataFrame and convert to CSV string
    df = pd.DataFrame(spectrogram, columns=["Time"] + bin_labels)
    return df.to_csv(index=False, float_format="%.3f")

def record_audio(duration=10, sample_rate=44100, channels=1, format=pyaudio.paInt16, chunk=1024):
    """
    Records audio from the microphone and saves it to a WAV file in the tmp directory.
    
    Args:
        duration: Recording duration in seconds (default: 10)
        sample_rate: Sample rate in Hz (default: 44100)
        channels: Number of audio channels (default: 1 for mono)
        format: Audio format (default: 16-bit PCM)
        chunk: Number of frames per buffer (default: 1024)
        
    Returns:
        Path to the recorded audio file
    """
    # Create a unique filename
    filename = f"recording_{uuid.uuid4().hex[0:6]}.wav"
    filepath = os.path.join("tmp", filename)
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    # Open stream
    stream = p.open(
        format=format,
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk
    )
    
    print(f"Recording for {duration} seconds...")
    
    # Record audio
    frames = []
    for i in range(0, int(sample_rate / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)
    
    print("Recording finished.")
    
    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Save the recorded audio to a WAV file
    wf = wave.open(filepath, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(format))
    wf.setframerate(sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    return filepath

if __name__ == "__main__":
    # Example usage
    csv_str = fft("data/audio1.mp3", cutoff_lo=0, cutoff_hi=2000, start_sec=0, end_sec=10, time_bins=60, freq_bins=1)
    print(csv_str)