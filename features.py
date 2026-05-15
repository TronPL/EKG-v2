import numpy as np

def rr_intervals(r_peaks, fs):
    rr = np.diff(r_peaks) / fs
    hr = 60 / rr if len(rr) > 0 else []

    return rr, hr


def basic_stats(rr, hr):
    return {
        "mean_rr": np.mean(rr) if len(rr) else 0,
        "std_rr": np.std(rr) if len(rr) else 0,
        "mean_hr": np.mean(hr) if len(hr) else 0
    }