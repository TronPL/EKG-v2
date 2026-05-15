import numpy as np

def detect_arrhythmias(hr, hrv, r_peaks=None, fs=None):
    results = []

    mean_hr = np.mean(hr)

    rmssd = hrv["HRV_RMSSD"].values[0]
    sdnn = hrv["HRV_SDNN"].values[0]

    # klasyczne reguły
    if mean_hr > 100:
        results.append("Tachycardia")

    if mean_hr < 60:
        results.append("Bradycardia")

    if sdnn > 120:
        results.append("Irregular Rhythm")

    if rmssd > 0.1 and sdnn > 100:
        results.append("Possible AF")

    if not results:
        results.append("Normal Rhythm")

    # -----------------------------
    # EVENTY (do wykresu)
    # -----------------------------
    events = []

    if len(hr) > 10:
        rr = np.diff(r_peaks) / fs if r_peaks is not None else None

        if rr is not None:
            start = None

            for i in range(len(rr)):
                if rr[i] > 1.2 or rr[i] < 0.5:
                    if start is None:
                        start = r_peaks[i]
                else:
                    if start is not None:
                        events.append({
                            "type": "irregular",
                            "start": start,
                            "end": r_peaks[i]
                        })
                        start = None

    return results, events