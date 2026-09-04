"""Transparent signal-quality gates for ECG review support.

These metrics identify unsuitable fragments; they do not certify an ECG
trace as diagnostically adequate.  Their thresholds must be clinically
validated for a particular recorder and electrode configuration.
"""

import numpy as np

from config import SIGNAL_QUALITY_MIN_SCORE


def assess_signal_quality(signal):
    """Return simple, serialisable quality metrics for one physical lead."""
    values = np.asarray(signal, dtype=float)
    if values.ndim != 1 or len(values) < 3 or not np.all(np.isfinite(values)):
        return {"score": 0.0, "accepted": False, "reason": "invalid", "amplitude": 0.0}

    low, high = np.percentile(values, [5, 95])
    amplitude = float(high - low)
    spread = float(np.std(values))
    if amplitude <= np.finfo(float).eps or spread <= np.finfo(float).eps:
        return {"score": 0.0, "accepted": False, "reason": "flatline", "amplitude": amplitude}

    # Large sample-to-sample changes are a recorder/electrode-motion proxy.
    noise_ratio = float(np.median(np.abs(np.diff(values))) / amplitude)
    min_value, max_value = float(np.min(values)), float(np.max(values))
    resolution = max(np.finfo(float).eps, amplitude * 1e-6)
    clipped_fraction = float(
        np.mean(np.isclose(values, min_value, atol=resolution) | np.isclose(values, max_value, atol=resolution))
    )
    noise_score = float(np.clip(1.0 - noise_ratio / 0.40, 0.0, 1.0))
    clipping_score = float(np.clip(1.0 - clipped_fraction / 0.20, 0.0, 1.0))
    score = 0.70 * noise_score + 0.30 * clipping_score
    accepted = bool(score >= SIGNAL_QUALITY_MIN_SCORE and clipped_fraction < 0.20)
    return {
        "score": float(score),
        "accepted": accepted,
        "reason": "accepted" if accepted else "noise_or_clipping",
        "amplitude": amplitude,
        "noise_ratio": noise_ratio,
        "clipped_fraction": clipped_fraction,
    }


def summarise_signal_quality(history):
    """Aggregate chunk assessments without retaining raw ECG in memory."""
    result = {}
    for lead, assessments in history.items():
        if not assessments:
            continue
        result[lead] = {
            "mean_score": float(np.mean([item["score"] for item in assessments])),
            "usable_fraction": float(np.mean([item["accepted"] for item in assessments])),
            "chunks": len(assessments),
        }
    return result
