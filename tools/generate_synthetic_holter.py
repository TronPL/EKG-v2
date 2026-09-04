"""Generate a deterministic ADS1298-style Holter fixture for regression tests.

This generator creates simulated waveforms, not physiological or clinical
reference data. Keep it separate from any validation dataset.
"""

import csv
import math
from array import array
from pathlib import Path


SAMPLING_RATE = 100
DURATION_SECONDS = 30 * 60
LEADS = ("I", "II", "V1", "V2", "V3", "V4", "V5", "V6")
LEAD_SCALES = {"I": 0.78, "II": 1.00, "V1": 0.58, "V2": 0.72, "V3": 0.88, "V4": 1.05, "V5": 0.96, "V6": 0.82}


def gaussian(value, centre, width):
    return math.exp(-0.5 * ((value - centre) / width) ** 2)


def add_regular(beats, start, end, rr, label="normal"):
    moment = start
    while moment < end:
        beats.append((moment, label))
        moment += rr


def make_beats():
    beats = []
    add_regular(beats, 0.0, 300.0, 0.80)
    add_regular(beats, 300.0, 480.0, 0.50, "tachy")
    add_regular(beats, 480.0, 780.0, 0.80)
    irregular_rr = (0.48, 0.92, 0.61, 1.08, 0.55, 0.78, 0.67, 1.00, 0.51, 0.86)
    moment, index = 780.0, 0
    while moment < 1020.0:
        beats.append((moment, "af_like"))
        moment += irregular_rr[index % len(irregular_rr)]
        index += 1
    add_regular(beats, 1020.0, 1140.0, 1.30, "brady")
    add_regular(beats, 1140.0, 1200.0, 0.80)
    # Earlier beats followed by a longer interval emulate ectopy and a
    # compensatory pause. The label controls the waveform morphology.
    moment, ectopic_index = 1200.0, 0
    while moment < 1290.0:
        beats.append((moment, "normal"))
        if ectopic_index % 2 == 0:
            moment += 0.52
            beats.append((moment, "pvc"))
        else:
            moment += 0.60
            beats.append((moment, "pac"))
        moment += 1.08
        ectopic_index += 1
    add_regular(beats, 1290.0, 1369.6, 0.80)
    beats.append((1369.6, "normal"))
    beats.append((1372.2, "pause_after"))
    add_regular(beats, 1373.0, 1500.0, 0.80)
    add_regular(beats, 1500.0, 1560.0, 0.35, "svt_like")
    add_regular(beats, 1560.0, DURATION_SECONDS, 0.80)
    return sorted(beats)


def beat_shape(relative_time, label):
    if label == "pvc":
        return (-0.10 * gaussian(relative_time, -0.06, 0.025) + 1.05 * gaussian(relative_time, 0.00, 0.045) - 0.28 * gaussian(relative_time, 0.08, 0.035) - 0.20 * gaussian(relative_time, 0.32, 0.085))
    p_scale = 1.7 if label == "pac" else 1.0
    return (0.12 * p_scale * gaussian(relative_time, -0.18, 0.026) - 0.13 * gaussian(relative_time, -0.030, 0.010) + 1.00 * gaussian(relative_time, 0.00, 0.012) - 0.25 * gaussian(relative_time, 0.040, 0.014) + 0.28 * gaussian(relative_time, 0.28, 0.070))


def generate(output_path):
    sample_count = DURATION_SECONDS * SAMPLING_RATE + 1
    signals = {lead: array("f", [0.0]) * sample_count for lead in LEADS}
    for index in range(sample_count):
        time = index / SAMPLING_RATE
        baseline = 0.025 * math.sin(2 * math.pi * 0.18 * time)
        for lead_index, lead in enumerate(LEADS):
            noise = 0.006 * math.sin(2 * math.pi * (17 + lead_index) * time + lead_index)
            signals[lead][index] = baseline + noise
    for beat_time, label in make_beats():
        first = max(0, int((beat_time - 0.40) * SAMPLING_RATE))
        last = min(sample_count - 1, int((beat_time + 0.60) * SAMPLING_RATE))
        for index in range(first, last + 1):
            shape = beat_shape(index / SAMPLING_RATE - beat_time, label)
            for lead in LEADS:
                signals[lead][index] += LEAD_SCALES[lead] * shape
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(("time", *LEADS))
        for index in range(sample_count):
            writer.writerow((f"{index / SAMPLING_RATE:.2f}", *(f"{signals[lead][index]:.6f}" for lead in LEADS)))


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "dane" / "holter_test_30min_100Hz_arytmie.csv"
    generate(target)
    print(target)
