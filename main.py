from config import FS

from utils.csv_loader import load_ecg_csv

from processing.filters import bandpass_filter
from processing.qrs_detection import detect_r_peaks
from processing.rr_analysis import compute_hr, compute_hrv
from processing.arrhythmia_detection import detect_arrhythmias

from visualization.plot_ecg import plot_ecg


# LOAD
time, voltage = load_ecg_csv("data/ecg (2).csv")

# FILTER
filtered = bandpass_filter(voltage, FS)

# R-PEAKS
r_peaks = detect_r_peaks(filtered, FS)

# HR / HRV
hr = compute_hr(r_peaks, FS)
hrv = compute_hrv(r_peaks, FS)

# ANALYSIS + EVENTS
results, events = detect_arrhythmias(hr, hrv, r_peaks, FS)

# OUTPUT
print("\n===== ECG ANALYSIS =====")
print(f"Detected beats: {len(r_peaks)}")
print(f"Mean HR: {hr.mean():.2f} BPM")

print("\nDetected Conditions:")
for r in results:
    print("-", r)

# PLOT
plot_ecg(filtered, r_peaks, FS, events)