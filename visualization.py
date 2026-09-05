from pathlib import Path
from collections.abc import Mapping

import matplotlib

# Flask/Waitress serves requests from worker threads. A non-interactive
# backend writes image files directly and never creates Tkinter GUI objects.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from leads import STANDARD_12_LEAD_ORDER


def _short_event_label(name):
    """Keep rhythm-strip annotations readable when many events share one plot."""
    labels = (
        ("PAC/SVEB", "PAC/SVEB"),
        ("PVC", "PVC"),
        ("SVT", "SVT"),
        ("Tachycardia", "Tachy"),
        ("Bradycardia", "Brady"),
        ("Pause", "Pauza"),
        ("Premature beat", "Pob. przedwcz."),
    )
    for prefix, short_label in labels:
        if name.startswith(prefix):
            return short_label
    return name


def plot_rr(time, r_peaks):
    """Return RR intervals for callers that want to render them themselves."""
    return np.diff(time[r_peaks])


def plot_ecg(
    time,
    ecg,
    r_peaks=None,
    events=None,
    output_path="static/plots/ecg_plot.png",
    lead_name="II",
    amplitude_limit=None,
):
    if not hasattr(output_path, "write"):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(15, 5))
    ax.plot(time, ecg, label=f"Lead {lead_name}", linewidth=1)
    if amplitude_limit is not None and np.isfinite(amplitude_limit) and amplitude_limit > 0:
        ax.set_ylim(-amplitude_limit, amplitude_limit)
    ax.set_axisbelow(True)
    ax.grid(which="major", color="#d1d5db", linewidth=0.5, alpha=0.55)

    if r_peaks is not None:
        ax.scatter(time[r_peaks], ecg[r_peaks], color="red", s=20, label="R-peaks")

    if events:
        for event in events:
            if isinstance(event, Mapping):
                name = event["name"]
                label = _short_event_label(name)
                event_time = event["start_time"]
                if time[0] <= event_time <= time[-1]:
                    ax.axvline(x=event_time, linestyle="--", alpha=0.5)
                    ax.text(
                        event_time,
                        np.max(ecg),
                        label,
                        rotation=90,
                        verticalalignment="bottom",
                        fontsize=8,
                    )
            elif isinstance(event, tuple) and len(event) == 2:
                name, idx = event
                label = _short_event_label(name)
                # An RR interval at index i ends at the R-peak i + 1.
                peak_idx = idx + 1
                if r_peaks is not None and 0 <= peak_idx < len(r_peaks):
                    event_time = time[r_peaks[peak_idx]]
                    ax.axvline(x=event_time, linestyle="--", alpha=0.5)
                    ax.text(
                        event_time,
                        np.max(ecg),
                        label,
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


def plot_event_review(time, raw_ecg, cleaned_ecg, r_peaks, event, output_path, lead_name):
    """Save an event-review strip with both source and filtered rhythm lead."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(15, 7), sharex=True)
    relative_time = time - time[0]
    event_start = event["start_time"] - time[0]
    event_end = event["end_time"] - time[0]

    for axis, signal, title in (
        (axes[0], raw_ecg, "Sygnał źródłowy"),
        (axes[1], cleaned_ecg, "Sygnał po filtracji"),
    ):
        axis.plot(relative_time, signal, color="black", linewidth=0.8)
        if event_end > event_start:
            axis.axvspan(event_start, event_end, color="#f59e0b", alpha=0.2, label=event["name"])
        else:
            axis.axvline(event_start, color="#d97706", linestyle="--", label=event["name"])
        axis.set_ylabel("Amplituda")
        axis.set_title(title, loc="left")
        axis.legend(loc="upper right")
        axis.grid(axis="x", alpha=0.2)

    if r_peaks is not None and len(r_peaks):
        axes[1].scatter(relative_time[r_peaks], cleaned_ecg[r_peaks], color="#dc2626", s=16, label="R")
        axes[1].legend(loc="upper right")
    axes[1].set_xlabel("Czas od początku fragmentu (s)")
    fig.suptitle(f"Przegląd zdarzenia: {event['name']} — odprowadzenie {lead_name}")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_12_lead_ecg(time, leads, output_path, overview_seconds=10, event_time=None, event_label="Zdarzenie"):
    """Save a conventional 3×4 overview of the first ECG segment.

    A 10-second overview stays interpretable even when the original file contains
    many hours of Holter data. It is a display view; rhythm detection still uses
    the full Lead II recording.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    end_time = time[0] + overview_seconds
    end_index = max(1, np.searchsorted(time, end_time, side="right"))
    displayed_time = time[:end_index] - time[0]
    marker_time = None
    if event_time is not None and time[0] <= event_time <= time[end_index - 1]:
        marker_time = event_time - time[0]

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
            if marker_time is not None:
                axis.axvline(marker_time, color="#d97706", linestyle="--", linewidth=1.2)
            axis.set_title(lead_name, loc="left", fontweight="bold")
            axis.grid(axis="x", alpha=0.2)

    for axis in axes[-1, :]:
        axis.set_xlabel("Time (s)")
    for axis in axes[:, 0]:
        axis.set_ylabel("Amplitude")

    title = f"12 odprowadzeń — kontekst {displayed_time[-1]:.1f} s"
    if marker_time is not None:
        title += f"; znacznik: {event_label} ({marker_time:.3f} s)"
    fig.suptitle(title, y=0.995)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
