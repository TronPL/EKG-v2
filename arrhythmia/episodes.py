"""Short-window rhythm candidates, retained as episodes for clinical review."""

import numpy as np

from config import AF_CV_THRESHOLD, BRADY_HR, RHYTHM_WINDOW_SECONDS, RHYTHM_WINDOW_STEP_SECONDS, TACHY_HR


def detect_rhythm_episodes(peak_times, window_seconds=RHYTHM_WINDOW_SECONDS, step_seconds=RHYTHM_WINDOW_STEP_SECONDS):
    peaks = np.asarray(peak_times, dtype=float)
    if len(peaks) < 3:
        return []
    records = []
    start = float(peaks[0])
    final = float(peaks[-1])
    while start < final:
        end = min(final, start + window_seconds)
        local = peaks[(peaks >= start) & (peaks <= end)]
        rr = np.diff(local)
        if len(rr) < 3:
            start += step_seconds
            continue
        mean_hr = float(60 / np.mean(rr))
        duration = float(local[-1] - local[0])
        if mean_hr > TACHY_HR and duration >= 10:
            records.append(("Tachycardia candidate", start, end))
        if mean_hr < BRADY_HR and duration >= 10:
            records.append(("Bradycardia candidate", start, end))
        cv = float(np.std(rr) / np.mean(rr))
        if len(rr) >= 8 and cv > AF_CV_THRESHOLD:
            records.append(("Possible AF", start, end))
        if len(rr) >= 4 and mean_hr >= 150 and cv < 0.10 and duration >= 3:
            records.append(("SVT candidate (regular tachycardia)", start, end))
        start += step_seconds
    return records
