import numpy as np
import matplotlib.pyplot as plt

def plot_rr(time,r_peaks):
    
    drpeaks = np.diff(time[r_peaks])
    plt.plot(drpeaks)
    plt.show()
    
    
def plot_ecg(time, ecg, r_peaks=None, events=None, output_path="static/plots/ecg_plot.png"):
    plt.figure(figsize=(15, 5))
    plt.plot(time, ecg, label="ECG", linewidth=1)

    # =========================
    # R-peaks
    # =========================
    if r_peaks is not None:
        plt.scatter(time[r_peaks], ecg[r_peaks],
                    color="red", s=20, label="R-peaks")

    # =========================
    # EVENTS (PVC, pause etc.)
    # events format: ("PVC", index)
    # =========================
    if events:
        for event in events:
            if len(event) == 2:
                name, idx = event

                if idx < len(time):
                    plt.axvline(x=time[r_peaks[idx-1]], linestyle="--", alpha=0.5)

                    plt.text(
                        time[r_peaks[idx-1]],
                        np.max(ecg),
                        name,
                        rotation=90,
                        verticalalignment="bottom",
                        fontsize=8
                    )

            # simple labels like "Tachycardia"
            elif isinstance(event, str):
                plt.text(
                    time[len(time)//2],
                    np.max(ecg),
                    event,
                    fontsize=12,
                    color="blue"
                )

    plt.title("ECG with detected arrhythmias")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.savefig(output_path)
    plt.legend()
    plt.tight_layout()
    # plt.show()