from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def plot_rr(time, r_peaks):
    drpeaks = np.diff(time[r_peaks])
    plt.plot(drpeaks)
    plt.show()


def plot_ecg(time, ecg, r_peaks=None, events=None, output_path="static/plots/ecg_plot.png"):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(15, 5))
    ax.plot(time, ecg, label="ECG", linewidth=1)

    if r_peaks is not None:
        ax.scatter(time[r_peaks], ecg[r_peaks], color="red", s=20, label="R-peaks")

    if events:
        for event in events:
            if isinstance(event, tuple) and len(event) == 2:
                name, idx = event
                # An RR interval at index i ends at the R-peak i + 1.
                peak_idx = idx + 1
                if r_peaks is not None and 0 <= peak_idx < len(r_peaks):
                    event_time = time[r_peaks[peak_idx]]
                    ax.axvline(x=event_time, linestyle="--", alpha=0.5)
                    ax.text(
                        event_time,
                        np.max(ecg),
                        name,
                        rotation=90,
                        verticalalignment="bottom",
                        fontsize=8,
                    )
            elif isinstance(event, str):
                ax.text(
                    time[len(time) // 2],
                    np.max(ecg),
                    event,
                    fontsize=12,
                    color="blue",
                )

    ax.set_title("ECG with detected arrhythmias")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
