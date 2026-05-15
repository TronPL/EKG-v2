import neurokit2 as nk

def get_rpeaks(ecg, fs):
    signals, info = nk.ecg_peaks(ecg, sampling_rate=fs)
    return info["ECG_R_Peaks"]