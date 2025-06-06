# Tool Summary

This file documents the signal analysis tools used in the project (in `functions.py`) and what each one is intended to measure.

| Tool Name             | Purpose                                                         | Domain         |
|----------------------|------------------------------------------------------------------|----------------|
| `fft`                | Extracts frequency content and energy distribution over time     | Frequency      |
| `zero_crossing_rate` | Measures how frequently the waveform crosses zero                | Time           |
| `autocorrelation`    | Identifies repeating patterns and periodicity                    | Time           |
| `envelope_and_decay` | Measures loudness envelope and decay trends                      | Time-Amplitude |
| `spectral_flatness`  | Indicates whether the sound is tonal or noise-like               | Frequency      |
| `fractal_dimension`  | Quantifies complexity of the waveform structure                  | Time           |
| `shannon_entropy`    | Estimates signal randomness and unpredictability                 | Time-Statistical |
| `file_meta_data`     | Extracts duration, bitrate, and size from the file               | Metadata       |
| `record_audio`       | Utility function to capture microphone input                     | Utility        |
| `search_perplexity`  | Performs web search to infer likely sources of detected signals  | AI Integration |

## Usage

All tools are implemented in `functions.py`. Most accept a `file_path` to an audio file (e.g. `.m4a` or `.wav`) and return a CSV-formatted string.

## Notes

- Most tools preprocess stereo audio into mono
- Outputs can be combined for multi-feature analysis
- Tools are used by the agent during reasoning and Perplexity search