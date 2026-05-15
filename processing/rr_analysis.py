import neurokit2 as nk
import numpy as np

def compute_hr(r_peaks, fs):
    rr = np.diff(r_peaks) / fs
    hr = 60 / rr
    return hr


def compute_hrv(r_peaks, fs):
    hrv = nk.hrv_time(r_peaks, sampling_rate=fs)

    return hrv