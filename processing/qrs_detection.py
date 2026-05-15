import neurokit2 as nk

def detect_r_peaks(signal, fs):
    _, info = nk.ecg_peaks(signal, sampling_rate=fs)
    return info["ECG_R_Peaks"]