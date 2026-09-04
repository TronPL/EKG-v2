"""Beat morphology features for clinician-review prioritisation.

They are deliberately named as estimates: a waveform feature alone is not a
clinical rhythm diagnosis.
"""

import numpy as np


def _nearest_indexes(time, peak_times):
    indexes = np.searchsorted(time, peak_times)
    return np.clip(indexes, 0, len(time) - 1)


def extract_beat_features(time, cleaned_leads, peak_times, sampling_rate, primary_lead="II"):
    """Estimate QRS width/shape and pre-QRS P-wave prominence for each R peak."""
    time = np.asarray(time, dtype=float)
    peaks = np.asarray(peak_times, dtype=float)
    if not len(time) or not len(peaks) or primary_lead not in cleaned_leads:
        return {}
    signal = np.asarray(cleaned_leads[primary_lead], dtype=float)
    indexes = _nearest_indexes(time, peaks)
    before, after = round(0.08 * sampling_rate), round(0.16 * sampling_rate)
    templates, valid = [], []
    for index in indexes:
        if index - before >= 0 and index + after < len(signal):
            template = signal[index - before : index + after + 1]
            scale = np.std(template)
            if scale > np.finfo(float).eps:
                templates.append((template - np.mean(template)) / scale)
                valid.append(index)
    median_template = np.median(np.asarray(templates), axis=0) if templates else None

    features = {}
    baseline_start, baseline_end = round(0.25 * sampling_rate), round(0.12 * sampling_rate)
    p_start, p_end = round(0.24 * sampling_rate), round(0.08 * sampling_rate)
    template_by_index = {index: template for index, template in zip(valid, templates)}
    for peak_time, index in zip(peaks, indexes):
        baseline_slice = signal[max(0, index - baseline_start) : max(0, index - baseline_end)]
        baseline = float(np.median(baseline_slice)) if len(baseline_slice) else float(signal[index])
        amplitude = abs(float(signal[index] - baseline))
        threshold = max(amplitude * 0.25, np.finfo(float).eps)
        left = index
        while left > max(0, index - round(0.16 * sampling_rate)) and abs(signal[left] - baseline) > threshold:
            left -= 1
        right = index
        while right < min(len(signal) - 1, index + round(0.16 * sampling_rate)) and abs(signal[right] - baseline) > threshold:
            right += 1
        qrs_width = float((right - left) / sampling_rate)

        p_prominences = []
        for lead in ("II", "V1"):
            if lead not in cleaned_leads:
                continue
            values = np.asarray(cleaned_leads[lead], dtype=float)
            segment = values[max(0, index - p_start) : max(0, index - p_end)]
            local = values[max(0, index - baseline_start) : index]
            if len(segment) and len(local):
                p_prominences.append(float((np.max(segment) - np.min(segment)) / (np.ptp(local) + np.finfo(float).eps)))
        shape_similarity = None
        template = template_by_index.get(index)
        if template is not None and median_template is not None and np.std(median_template) > np.finfo(float).eps:
            correlation = float(np.corrcoef(template, median_template)[0, 1])
            shape_similarity = correlation if np.isfinite(correlation) else None
        features[round(float(peak_time), 6)] = {
            "qrs_width_seconds": qrs_width,
            "qrs_shape_similarity": shape_similarity,
            "p_wave_prominence": float(max(p_prominences)) if p_prominences else None,
        }
    return features


def classify_premature_beats(peak_times, feature_by_time):
    """Classify early beats only when morphology evidence supports a label."""
    peaks = np.asarray(peak_times, dtype=float)
    if len(peaks) < 4:
        return []
    rr = np.diff(peaks)
    events = []
    for index in range(1, len(peaks) - 1):
        reference = rr[max(0, index - 5) : min(len(rr), index + 5)]
        reference = reference[reference > 0]
        if not len(reference) or rr[index - 1] >= 0.80 * np.median(reference):
            continue
        feature = feature_by_time.get(round(float(peaks[index]), 6), {})
        width = feature.get("qrs_width_seconds")
        shape = feature.get("qrs_shape_similarity")
        prior_widths = [
            item.get("qrs_width_seconds") for key, item in feature_by_time.items()
            if abs(key - peaks[index]) <= 10 and item.get("qrs_width_seconds") is not None
        ]
        baseline_width = float(np.median(prior_widths)) if prior_widths else None
        wide_or_changed = bool(
            width is not None
            and (width >= 0.12 or (baseline_width and width > 1.25 * baseline_width) or (shape is not None and shape < 0.75))
        )
        p_wave_evidence = feature.get("p_wave_prominence")
        if wide_or_changed:
            name = "PVC candidate (QRS morphology)"
        elif width is not None and width < 0.12 and p_wave_evidence is not None and p_wave_evidence >= 0.15:
            name = "PAC/SVEB candidate (narrow QRS; pre-QRS feature)"
        elif width is not None and width < 0.12:
            name = "Premature beat candidate (narrow QRS; P-wave uncertain)"
        else:
            name = "Premature beat candidate (undetermined)"
        events.append((name, index - 1, feature))
    return events
