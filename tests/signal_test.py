import csv
import io
from functions import fft

# Test for FFT function
def test_fft():
    test_file = "data/audio1.mp3" # Known file
    csv_str = fft(test_file, cutoff_lo=0, cutoff_hi=2000, time_bins=5, freq_bins=3)

    csv_file = io.StringIO(csv_str)
    reader = csv.reader(csv_file)
    header = next(reader)

    # Check header structure
    assert header[0] == "Time"
    assert len(header) == 4  # Check 1 time column + 3 frequency bins
    assert all("Hz" in col for col in header[1:])

    # Check values in rows
    for row in reader:
        assert len(row) == 4
        for val in row[1:]:  # skip "Time"
            float_val = float(val)
            assert float_val >= 0
