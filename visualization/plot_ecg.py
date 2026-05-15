import matplotlib.pyplot as plt
import numpy as np

def plot_ecg(signal, r_peaks, fs, events=None):
    t = np.arange(len(signal)) / fs

    plt.figure(figsize=(12, 5))
    plt.plot(t, signal, label="ECG")

    # R-peaks
    plt.scatter(t[r_peaks], signal[r_peaks], color="red", s=10, label="R-peaks")

    # EVENTS
    if events:
        for ev in events:
            plt.axvspan(
                ev["start"] / fs,
                ev["end"] / fs,
                alpha=0.3,
                label=ev["type"]
            )

    plt.legend()
    plt.title("ECG with detections")
    plt.show()