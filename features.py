import numpy as np

def rr_intervals(r_peaks, fs):
    rr = np.diff(r_peaks) / fs
    hr = 60 / rr if len(rr) > 0 else []

    return rr, hr


def rr_intervals_from_times(r_peak_times):
    """Calculate RR and instantaneous HR from timestamped R peaks."""
    peak_times = np.asarray(r_peak_times, dtype=float)
    rr = np.diff(peak_times)
    if len(rr) and np.any(rr <= 0):
        raise ValueError("Czasy załamków R muszą być rosnące.")
    hr = 60 / rr if len(rr) else np.array([])
    return rr, hr


def basic_stats(rr, hr):
    return {
        "mean_rr": np.mean(rr) if len(rr) else 0,
        "std_rr": np.std(rr) if len(rr) else 0,
        "mean_hr": np.mean(hr) if len(hr) else 0
    }
