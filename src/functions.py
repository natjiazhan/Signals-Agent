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
import json
from scipy.signal import hilbert
from PIL import Image, ImageDraw, ImageFont
import base64

load_dotenv()

pplx_system_prompt = "You are a helpful assistant. All answers should be in English regardless of the language of the question. " \

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

def analyze_image(
    image_path: str,
    prompt: str = "Describe what is going on in this scene, and list all objects that you detect and where they are.",
    temperature: float = 1.2
) -> str:
    """
    Uses OpenAI GPT-4 Vision to analyze an image and return a description.

    Args:
        image_path (str): Local path to the image file (e.g., .jpg, .png)
        prompt (str): Instruction for GPT-4 to guide the captioning
        temperature (float): Controls randomness of model output (0 = deterministic, 1 = creative)

    Returns:
        Description generated by GPT-4 Vision model
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }
            ],
            temperature=temperature,
            max_tokens=300
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Image analysis failed] {e}"

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
def fft(file_path, cutoff_lo, cutoff_hi, start_sec=0, end_sec=None, time_bins=5, freq_bins=15, verbose=False):
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
        if not verbose:
            stdout = subprocess.DEVNULL
            stderr = subprocess.DEVNULL
        else:
            stdout = None
            stderr = None
            
        # Convert to WAV format
        subprocess.run(['ffmpeg', '-y', '-i', str(input_file_path), str(wav_file)], 
                      stdout=stdout,
                      stderr=stderr,
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

def stereo_fft(file_path, cutoff_lo, cutoff_hi, start_sec=0, end_sec=None, time_bins=5, freq_bins=15, verbose=False):
    """
    Computes stereo time-frequency spectrograms as a CSV-formatted string for both left and right channels.
    Each row contains spectral energy for left and right channels across frequency bins and time windows.

    Args:
        file_path: Path to the stereo audio file (e.g., .wav, .mp3).
        cutoff_lo: Lower frequency bound in Hz.
        cutoff_hi: Upper frequency bound in Hz.
        start_sec: Start time in seconds.
        end_sec: End time in seconds (None = full duration).
        time_bins: Number of time segments.
        freq_bins: Number of frequency bins.

    Returns:
        CSV string with columns: Time, L:bin1, ..., L:binN, R:bin1, ..., R:binN
    """
    input_file_path = Path(file_path)

    # Convert to .wav if needed
    if input_file_path.suffix.lower() != '.wav':
        wav_file = input_file_path.with_suffix('.wav')
        stdout = subprocess.DEVNULL if not verbose else None
        stderr = subprocess.DEVNULL if not verbose else None
        subprocess.run(['ffmpeg', '-y', '-i', str(input_file_path), str(wav_file)],
                       stdout=stdout, stderr=stderr, check=True)
    else:
        wav_file = input_file_path

    signal, sample_rate = open_audio(str(wav_file))

    if signal.ndim != 2:
        raise ValueError("Input file must be stereo (2 channels).")

    # Extract channels
    left = signal[:, 0]
    right = signal[:, 1]

    # Trim both to the selected segment
    start_sample = int(start_sec * sample_rate)
    if not end_sec:
        end_sec = len(left) / sample_rate
    end_sample = int(end_sec * sample_rate)

    left = left[start_sample:end_sample]
    right = right[start_sample:end_sample]

    # Time segmentation
    total_samples = len(left)
    window_size = int(total_samples / time_bins)

    # Frequency bins
    bin_edges = np.linspace(cutoff_lo, cutoff_hi, freq_bins + 1)
    bin_labels = [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}Hz" for i in range(freq_bins)]

    spectrogram = []

    for w in range(time_bins):
        start = w * window_size
        end = start + window_size

        # Left and Right segments
        seg_l = left[start:end]
        seg_r = right[start:end]

        # FFT
        fft_l = np.fft.fft(seg_l)
        fft_r = np.fft.fft(seg_r)
        freq = np.fft.fftfreq(len(seg_l), d=1/sample_rate)

        power_l = np.abs(fft_l)**2
        power_r = np.abs(fft_r)**2

        # Mask frequencies within cutoff
        mask = (freq >= cutoff_lo) & (freq <= cutoff_hi)
        freq = freq[mask]
        power_l = power_l[mask]
        power_r = power_r[mask]

        # Bin
        indices = np.digitize(freq, bin_edges) - 1
        binned_l = np.zeros(freq_bins)
        binned_r = np.zeros(freq_bins)

        for i in range(len(freq)):
            if 0 <= indices[i] < freq_bins:
                binned_l[indices[i]] += power_l[i]
                binned_r[indices[i]] += power_r[i]

        # Normalize
        if np.sum(binned_l) > 0:
            binned_l /= np.sum(binned_l)
        if np.sum(binned_r) > 0:
            binned_r /= np.sum(binned_r)

        # Time label
        start_time = round(start_sec + w * ((end_sec - start_sec) / time_bins), 2)
        end_time = round(start_time + ((end_sec - start_sec) / time_bins), 2)
        time_label = f"{start_time:.2f}-{end_time:.2f}sec"

        # Append both channels
        spectrogram.append([time_label] + list(binned_l) + list(binned_r))

    # Build final DataFrame
    df = pd.DataFrame(spectrogram, columns=["Time"] + [f"L:{b}" for b in bin_labels] + [f"R:{b}" for b in bin_labels])
    return df.to_csv(index=False, float_format="%.3f")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def zero_crossing_rate(file_path: str) -> str:
    """
    Computes the zero-crossing rate (ZCR) of a mono audio signal.
    
    Args:
        file_path: Path to the input audio file (e.g., .m4a or .mp3).
    
    Returns:
        CSV string with 'Time Window' and 'ZCR' columns for each time segment.
    """

    input_file_path = Path(file_path)

    # Convert to WAV if necessary
    if input_file_path.suffix.lower() != ".wav":
        wav_path = input_file_path.with_suffix(".wav")
        subprocess.run(
            ['ffmpeg', '-y', '-i', str(input_file_path), str(wav_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    else:
        wav_path = input_file_path

    signal, sample_rate = open_audio(str(wav_path))

    if signal.ndim == 2:
        signal = signal.mean(axis=1)

    # Divide into 10 time windows
    segments = np.array_split(signal, 30)
    zcrs = []
    for i, segment in enumerate(segments):
        zero_crossings = np.sum(np.diff(np.sign(segment)) != 0)
        zcr = zero_crossings / len(segment)
        zcrs.append((f"Window {i+1}", zcr))

    df = pd.DataFrame(zcrs, columns=["Time Window", "ZCR"])
    return df.to_csv(index=False, float_format="%.5f")

def autocorrelation(file_path: str, top_n: int = 5, segments: int = 10) -> str:
    """
    Computes normalized autocorrelation on segmented audio to identify repeating patterns.

    Args:
        file_path: Path to the input audio file (.mp3/.m4a/.wav)
        top_n: Number of top peaks to return per segment
        segments: Number of segments to divide the signal into

    Returns:
        CSV string: segment label, top lag (samples), strength
    """

    input_file_path = Path(file_path)

    # Convert to WAV if needed
    if input_file_path.suffix.lower() != ".wav":
        wav_path = input_file_path.with_suffix(".wav")
        subprocess.run(
            ['ffmpeg', '-y', '-i', str(input_file_path), str(wav_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    else:
        wav_path = input_file_path

    signal, _ = open_audio(str(wav_path))
    if signal.ndim == 2:
        signal = signal.mean(axis=1)

    signal -= np.mean(signal)
    parts = np.array_split(signal, segments)

    results = []
    for i, part in enumerate(parts):
        corr = np.correlate(part, part, mode='full')
        mid = len(corr) // 2
        norm_corr = corr[mid:] / np.max(corr)

        lags = np.arange(1, len(norm_corr))
        strengths = norm_corr[1:]

        # Find top N peaks beyond lag=0
        top_indices = np.argpartition(strengths, -top_n)[-top_n:]
        top_lags = lags[top_indices]
        top_strengths = strengths[top_indices]

        sorted_indices = np.argsort(top_lags)
        top_lags = top_lags[sorted_indices]
        top_strengths = top_strengths[sorted_indices]

        for lag, strength in zip(top_lags, top_strengths):
            results.append((f"Segment {i+1}", lag, strength))

    df = pd.DataFrame(results, columns=["Segment", "Lag (samples)", "Autocorrelation"])
    return df.to_csv(index=False, float_format="%.5f")

def envelope_decay(file_path: str) -> str:
    """
    Computes the amplitude envelope and decay rate of a mono audio signal using the Hilbert transform.

    Args:
        file_path: Path to the input audio file (e.g., .m4a or .mp3).

    Returns:
        CSV string with envelope peak values in 10 segments and the overall decay rate.
    """

    input_file_path = Path(file_path)

    # Convert to WAV if needed
    if input_file_path.suffix.lower() != ".wav":
        wav_path = input_file_path.with_suffix(".wav")
        subprocess.run(
            ['ffmpeg', '-y', '-i', str(input_file_path), str(wav_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    else:
        wav_path = input_file_path

    signal, sample_rate = open_audio(str(wav_path))

    if signal.ndim == 2:
        signal = signal.mean(axis=1)

    # Compute analytic signal and envelope
    analytic_signal = hilbert(signal)
    envelope = np.abs(analytic_signal)

    # Break envelope into 10 windows, calculate mean amplitude per window
    segments = np.array_split(envelope, 30)
    segment_means = [np.mean(seg) for seg in segments]

    # Estimate decay rate: (start - end) / num_samples
    decay_rate = (segment_means[0] - segment_means[-1]) / len(signal)

    df = pd.DataFrame({
        "Segment": [f"Window {i+1}" for i in range(30)],
        "Mean Amplitude": segment_means
    })

    df.loc[len(df.index)] = ["Decay Rate", decay_rate]

    return df.to_csv(index=False, float_format="%.5f")

def spectral_flatness(file_path: str) -> str:
    """
    Computes the spectral flatness of the audio signal across multiple time windows.

    Spectral flatness values close to 0 indicate a tonal signal, and values near 1 indicate noise-like signals.

    Args:
        file_path: Path to the input audio file (e.g., .m4a or .mp3).

    Returns:
        CSV string with one row per time segment, containing flatness values.
    """

    input_file_path = Path(file_path)

    # Convert to WAV if needed
    if input_file_path.suffix.lower() != ".wav":
        wav_path = input_file_path.with_suffix(".wav")
        subprocess.run(
            ['ffmpeg', '-y', '-i', str(input_file_path), str(wav_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    else:
        wav_path = input_file_path

    signal, sample_rate = open_audio(str(wav_path))

    if signal.ndim == 2:
        signal = signal.mean(axis=1)

    # Split into 10 segments
    segments = np.array_split(signal, 30)
    flatness_scores = []

    for i, segment in enumerate(segments):
        spectrum = np.fft.fft(segment)
        power = np.abs(spectrum) ** 2 + 1e-12  # avoid log(0)
        geom_mean = np.exp(np.mean(np.log(power)))
        arith_mean = np.mean(power)
        flatness = geom_mean / arith_mean
        flatness_scores.append((f"Window {i+1}", flatness))

    df = pd.DataFrame(flatness_scores, columns=["Segment", "Spectral Flatness"])
    return df.to_csv(index=False, float_format="%.5f")

def fractal_dimension(file_path: str) -> str:
    """
    Estimates the fractal dimension of an audio waveform using the Higuchi method.

    Args:
        file_path: Path to the input audio file (e.g., .m4a or .mp3)

    Returns:
        CSV string with estimated fractal dimension for the full waveform and for each of 10 windows.
    """

    def higuchi_fd(x, kmax):
        L = []
        x = np.asarray(x)
        N = len(x)

        for k in range(1, kmax+1):
            Lk = []
            for m in range(k):
                idxs = np.arange(1, int(np.floor((N - m) / k)), dtype=int)
                Lmk = np.sum(np.abs(x[m + idxs * k] - x[m + (idxs - 1) * k]))
                Lmk *= (N - 1) / (len(idxs) * k)
                Lk.append(Lmk)
            L.append(np.mean(Lk))

        lnL = np.log(L)
        lnk = np.log(1.0 / np.arange(1, kmax+1))
        coeffs = np.polyfit(lnk, lnL, 1)
        return coeffs[0]  # slope = fractal dimension estimate

    input_file_path = Path(file_path)

    # Convert to WAV if needed
    if input_file_path.suffix.lower() != ".wav":
        wav_path = input_file_path.with_suffix(".wav")
        subprocess.run(
            ['ffmpeg', '-y', '-i', str(input_file_path), str(wav_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    else:
        wav_path = input_file_path

    signal, _ = open_audio(str(wav_path))
    if signal.ndim == 2:
        signal = signal.mean(axis=1)

    segments = np.array_split(signal, 30)
    dimensions = [higuchi_fd(seg, kmax=10) for seg in segments]
    overall = higuchi_fd(signal, kmax=30)

    df = pd.DataFrame({
        "Segment": [f"Window {i+1}" for i in range(30)] + ["Overall"], 
        "Fractal Dimension": dimensions + [overall]
    })

    return df.to_csv(index=False, float_format="%.5f")

def shannon_entropy(file_path: str) -> str:
    """
    Computes Shannon entropy of the audio waveform over 10 segments.

    Args:
        file_path: Path to the input audio file (e.g., .m4a or .mp3)

    Returns:
        CSV string with Shannon entropy per segment and overall.
    """

    def compute_entropy(segment, bins=64):
        hist, _ = np.histogram(segment, bins=bins, density=True)
        hist = hist[hist > 0]  # Remove zero entries to avoid log(0)
        return -np.sum(hist * np.log2(hist))

    input_file_path = Path(file_path)

    if input_file_path.suffix.lower() != ".wav":
        wav_path = input_file_path.with_suffix(".wav")
        subprocess.run(
            ['ffmpeg', '-y', '-i', str(input_file_path), str(wav_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
    else:
        wav_path = input_file_path

    signal, _ = open_audio(str(wav_path))
    if signal.ndim == 2:
        signal = signal.mean(axis=1)

    segments = np.array_split(signal, 30)
    entropies = [compute_entropy(seg) for seg in segments]
    overall = compute_entropy(signal)

    df = pd.DataFrame({
        "Segment": [f"Window {i+1}" for i in range(30)] + ["Overall"],
        "Shannon Entropy": entropies + [overall]
    })

    return df.to_csv(index=False, float_format="%.5f")


def save_agent_output(file_name, source_types):
    """
    Save agent output in the required JSON format for evaluation.

    Args:
        file_name (str): Path to the input audio file (e.g. data/audio1.mp3)
        source_types (list[str]): List of source type labels

    Returns: output_path (str)

    """
    output = {
        "structured": {
            "source_type": source_types
        }
    }

    os.makedirs("outputs", exist_ok=True)

    base_name = os.path.basename(file_name).replace(".m4a", ".json").replace(".mp3", ".json")
    out_path = os.path.join("outputs", base_name)

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved prediction to: {out_path}")
    return out_path

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
    csv_str = fft("data/hamilton_ave.m4a", cutoff_lo=0, cutoff_hi=2000, start_sec=0, end_sec=20, time_bins=10, freq_bins=20)
    print(csv_str)