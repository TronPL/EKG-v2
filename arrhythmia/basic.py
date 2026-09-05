import numpy as np
from config import TACHY_HR, BRADY_HR, AF_CV_THRESHOLD

def detect_tachy_brady(hr):
    out = []

    mean_hr = np.mean(hr) if len(hr) else 0

    if mean_hr > TACHY_HR:
        out.append("Tachycardia")

    if mean_hr < BRADY_HR:
        out.append("Bradycardia")

    return out


def detect_af(rr):
    if len(rr) == 0:
        return []

    cv = np.std(rr) / np.mean(rr)

    if cv > AF_CV_THRESHOLD:
        return ["Possible AF"]

    return []
