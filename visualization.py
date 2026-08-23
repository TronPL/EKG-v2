from pathlib import Path
from collections.abc import Mapping

import matplotlib.pyplot as plt
import numpy as np

from leads import STANDARD_12_LEAD_ORDER


def plot_rr(time, r_peaks):
    drpeaks = np.diff(time[r_peaks])
    plt.plot(drpeaks)
    plt.show()


def plot_ecg(time, ecg, r_peaks=None, events=None, output_path="static/plots/ecg_plot.png", lead_name="II"):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(15, 5))
    ax.plot(time, ecg, label=f"Lead {lead_name}", linewidth=1)

    if r_peaks is not None:
        ax.scatter(time[r_peaks], ecg[r_peaks], color="red", s=20, label="R-peaks")

    if events:
        for event in events:
            if isinstance(event, Mapping):
                name = event["name"]
                event_time = event["start_time"]
                if time[0] <= event_time <= time[-1]:
                    ax.axvline(x=event_time, linestyle="--", alpha=0.5)
                    ax.text(
                        event_time,
                        np.max(ecg),
                        name,
                        rotation=90,
                        verticalalignment="bottom",
                        fontsize=8,
                    )
            elif isinstance(event, tuple) and len(event) == 2:
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

    ax.set_title(f"Lead {lead_name} with detected rhythm events")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_12_lead_ecg(time, leads, output_path, overview_seconds=10):
    """Save a conventional 3×4 overview of the first ECG segment.

    A 10-second overview stays interpretable even when the original file contains
    many hours of Holter data. It is a display view; rhythm detection still uses
    the full Lead II recording.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    end_time = time[0] + overview_seconds
    end_index = max(1, np.searchsorted(time, end_time, side="right"))
    displayed_time = time[:end_index] - time[0]

    layout = (
        ("I", "aVR", "V1", "V4"),
        ("II", "aVL", "V2", "V5"),
        ("III", "aVF", "V3", "V6"),
    )
    fig, axes = plt.subplots(3, 4, figsize=(16, 8), sharex=True)

    for row, row_leads in enumerate(layout):
        for column, lead_name in enumerate(row_leads):
            axis = axes[row, column]
            axis.plot(displayed_time, leads[lead_name][:end_index], linewidth=0.8, color="black")
            axis.set_title(lead_name, loc="left", fontweight="bold")
            axis.grid(axis="x", alpha=0.2)

    for axis in axes[-1, :]:
        axis.set_xlabel("Time (s)")
    for axis in axes[:, 0]:
        axis.set_ylabel("Amplitude")

    fig.suptitle(f"12-lead ECG overview — first {displayed_time[-1]:.1f} s", y=0.995)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
