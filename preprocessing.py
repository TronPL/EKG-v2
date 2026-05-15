import neurokit2 as nk

def preprocess(ecg_signal, fs):
    cleaned = nk.ecg_clean(ecg_signal, sampling_rate=fs)
    return cleaned