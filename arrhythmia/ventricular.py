import numpy as np
from config import PVC_THRESHOLD

def detect_pvc(rr):
    events = []

    if len(rr) < 3:
        return events

    mean_rr = np.mean(rr)

    for i in range(1, len(rr) - 1):
        if rr[i] < PVC_THRESHOLD * mean_rr:
            if rr[i] < rr[i - 1] and rr[i] < rr[i + 1]:
                events.append(("PVC", i))

    return events


def detect_bigeminy_trigeminy(rr):
    labels = []
    mean_rr = np.mean(rr)

    for i in range(2, len(rr)):
        if rr[i-1] < 0.7 * mean_rr and rr[i] > 1.2 * mean_rr:
            labels.append(("Bigeminy", i))

        if i >= 3:
            if (rr[i-2] < 0.7 * mean_rr and
                rr[i-1] > 1.2 * mean_rr and
                rr[i] > 1.2 * mean_rr):
                labels.append(("Trigeminy", i))

    return labels