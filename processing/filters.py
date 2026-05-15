import neurokit2 as nk

def bandpass_filter(signal, fs):
    return nk.ecg_clean(signal, sampling_rate=fs)