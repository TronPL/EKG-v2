import numpy as np


# =========================
# PAC / SVEB (przedwczesne pobudzenia nadkomorowe)
# =========================
def detect_pac(rr):
    """
    PAC: premature atrial contractions
    - podobne do PVC, ale zwykle mniej ekstremalne skrócenie RR
    """

    events = []

    if len(rr) < 3:
        return events

    mean_rr = np.mean(rr)

    for i in range(1, len(rr) - 1):

        # wcześniejszy beat, ale nie aż tak agresywny jak PVC
        if 0.7 * mean_rr > rr[i] > 0.4 * mean_rr:
            if rr[i] < rr[i - 1] and rr[i] < rr[i + 1]:
                events.append(("PAC", i))

    return events


# =========================
# SVEB (supraventricular ectopic beats)
# =========================
def detect_sveb(rr):
    """
    Szersza definicja niż PAC – pojedyncze ectopy nadkomorowe
    """

    events = []

    if len(rr) < 3:
        return events

    mean_rr = np.mean(rr)
    std_rr = np.std(rr)

    for i in range(1, len(rr) - 1):

        deviation = abs(rr[i] - mean_rr)

        # umiarkowane odchylenie + lokalne minimum
        if deviation > 0.6 * std_rr:
            if rr[i] < rr[i - 1] and rr[i] < rr[i + 1]:
                events.append(("SVEB", i))

    return events


# =========================
# SVT (supraventricular tachycardia)
# =========================
def detect_svt(hr, rr):
    """
    SVT:
    - wysoki HR
    - regularność (niska zmienność RR)
    """

    events = []

    if len(hr) == 0 or len(rr) < 5:
        return events

    mean_hr = np.mean(hr)
    rr_std = np.std(rr) / np.mean(rr)

    if mean_hr > 150 and rr_std < 0.1:
        events.append("SVT (possible supraventricular tachycardia)")

    return events


# =========================
# Atrial ectopy burden (bonus metric)
# =========================
def supraventricular_burden(rr):
    """
    procent beatów podejrzanych o SVEB/PAC
    """

    if len(rr) == 0:
        return 0

    mean_rr = np.mean(rr)

    ectopic = 0

    for r in rr:
        if abs(r - mean_rr) > 0.5 * np.std(rr):
            ectopic += 1

    return ectopic / len(rr)