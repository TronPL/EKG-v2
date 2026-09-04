import numpy as np

from arrhythmia.episodes import detect_rhythm_episodes
from arrhythmia.rhythm import detect_pause
from config import (
    ECG_CHUNK_ROWS,
    ECG_PEAK_CONTEXT_SECONDS,
    ECG_PREVIEW_SECONDS,
    ECG_REVIEW_CONTEXT_SECONDS,
)
from features import rr_intervals_from_times
from io_utils import iter_ecg_csv_chunks
from leads import RHYTHM_ANALYSIS_LEAD
from morphology import classify_premature_beats, extract_beat_features
from preprocessing import preprocess
from qrs_consensus import fuse_r_peak_times
from rpeaks import get_rpeaks
from sampling import validate_regular_sampling
from signal_quality import assess_signal_quality, summarise_signal_quality
from visualization import plot_ecg


def _sampling_rate_from_time(time):
    intervals = np.diff(time)
    if len(intervals) == 0 or np.any(intervals <= 0):
        raise ValueError("Nie można ustalić częstotliwości próbkowania.")
    interval = float(np.median(intervals))
    sampling_rate = 1 / interval
    if not np.isfinite(sampling_rate) or sampling_rate <= 0:
        raise ValueError("Nieprawidłowa częstotliwość próbkowania.")
    return sampling_rate, interval


def _validate_regular_sampling(time, expected_interval):
    return validate_regular_sampling(time, expected_interval)


def _append_preview(preview_time, preview_leads, time, signals, start_time):
    if preview_time and preview_time[-1] >= start_time + ECG_PREVIEW_SECONDS:
        return
    end = np.searchsorted(time, start_time + ECG_PREVIEW_SECONDS, side="right")
    if end == 0:
        return
    preview_time.extend(time[:end])
    for lead, values in signals.items():
        preview_leads.setdefault(lead, []).extend(values[:end])


def _detect_window_r_peaks(
    core_time,
    core_signals,
    sampling_rate,
    left_time,
    left_signals,
    right_time,
    right_signals,
    primary_lead,
):
    """Detect QRS complexes with per-lead quality gating and agreement.

    The returned morphology features are estimates for review support.  They
    are calculated on context-protected waveforms, then the caller retains
    only peaks belonging to the current core.
    """
    window_time = np.concatenate((left_time, core_time, right_time))
    quality = {lead: assess_signal_quality(values) for lead, values in core_signals.items()}
    usable_leads = [lead for lead, item in quality.items() if item["accepted"]]
    # Retain the rhythm lead as an explicit fallback when every channel is
    # poor; that condition is surfaced in the report rather than hidden.
    if not usable_leads and primary_lead in core_signals:
        usable_leads = [primary_lead]

    cleaned = {}
    peaks_by_lead = {}
    for lead in usable_leads:
        values = np.concatenate(
            (
                left_signals.get(lead, np.array([])),
                core_signals[lead],
                right_signals.get(lead, np.array([])),
            )
        )
        try:
            cleaned[lead] = preprocess(values, sampling_rate)
            peaks_by_lead[lead] = window_time[get_rpeaks(cleaned[lead], sampling_rate)]
        except (ValueError, IndexError, RuntimeError):
            # A failed channel must not prevent review of the other channels.
            continue

    peak_times, consensus = fuse_r_peak_times(peaks_by_lead, primary_lead)
    if primary_lead not in cleaned and primary_lead in core_signals:
        primary_values = np.concatenate(
            (
                left_signals.get(primary_lead, np.array([])),
                core_signals[primary_lead],
                right_signals.get(primary_lead, np.array([])),
            )
        )
        try:
            cleaned[primary_lead] = preprocess(primary_values, sampling_rate)
        except (ValueError, IndexError, RuntimeError):
            pass
    features = extract_beat_features(window_time, cleaned, peak_times, sampling_rate, primary_lead)
    return peak_times, quality, consensus, features


def _merge_adjacent_episodes(records, gap_tolerance):
    """Merge duplicate window-level labels without merging individual beats."""
    merged = []
    for record in sorted(records, key=lambda item: (item["name"], item["kind"], item["start_time"])):
        if (
            merged
            and record["kind"] == "episode"
            and merged[-1]["kind"] == "episode"
            and merged[-1]["name"] == record["name"]
            and record["start_time"] <= merged[-1]["end_time"] + gap_tolerance
        ):
            merged[-1]["end_time"] = max(merged[-1]["end_time"], record["end_time"])
        else:
            merged.append(dict(record))
    return sorted(merged, key=lambda item: (item["start_time"], item["name"]))


def _with_context_bounds(records, record_start, record_end):
    for record in records:
        record["context_start"] = max(record_start, record["start_time"] - ECG_REVIEW_CONTEXT_SECONDS)
        record["context_end"] = min(record_end, record["end_time"] + ECG_REVIEW_CONTEXT_SECONDS)
    return records


def _event_summary(events):
    counts = {}
    for event in events:
        counts[event["name"]] = counts.get(event["name"], 0) + 1
    return tuple(counts.items())


def _automatic_report(r_peak_times, rr, hr, events, duration_seconds, sample_count, signal_quality, consensus_modes):
    """Build a transparent summary of the current review-support analysis.

    The values are intended for triage and review.  They deliberately retain
    the word ``candidate`` because waveform features are not clinical
    confirmation.
    """
    event_counts = dict(_event_summary(events))
    episode_seconds = {}
    for event in events:
        if event["kind"] == "episode":
            name = event["name"]
            episode_seconds[name] = episode_seconds.get(name, 0.0) + max(
                0.0, event["end_time"] - event["start_time"]
            )

    pause_durations = [
        event["rr_interval_seconds"]
        for event in events
        if event["name"].startswith("Pause") and "rr_interval_seconds" in event
    ]
    beat_count = len(r_peak_times)
    candidate_burden_percent = {
        name: 100 * event_counts.get(name, 0) / beat_count
        for name in event_counts
        if "candidate" in name.lower() and any(event["name"] == name and event["kind"] == "beat" for event in events)
    }
    mean_heart_rate = None
    if len(r_peak_times) > 1 and r_peak_times[-1] > r_peak_times[0]:
        mean_heart_rate = float(60 * (len(r_peak_times) - 1) / (r_peak_times[-1] - r_peak_times[0]))

    return {
        "analysis_scope": "Automatyczne oznaczenia wymagające przeglądu; nie są rozpoznaniami klinicznymi.",
        "recording": {
            "duration_seconds": float(duration_seconds),
            "sample_count": int(sample_count),
            "regular_timestamps": True,
        },
        "heart_rate_bpm": {
            "minimum": float(np.min(hr)) if len(hr) else None,
            "mean": mean_heart_rate,
            "maximum": float(np.max(hr)) if len(hr) else None,
        },
        "r_peak_count": int(beat_count),
        "candidate_counts": event_counts,
        "candidate_burden_percent": candidate_burden_percent,
        "episode_seconds": episode_seconds,
        "longest_pause_seconds": float(max(pause_durations)) if pause_durations else None,
        "signal_quality": signal_quality,
        "qrs_detection": {
            "consensus_windows": int(consensus_modes.get("multi_lead_consensus", 0)),
            "fallback_windows": int(consensus_modes.get("primary_lead_fallback", 0)),
            "single_lead_windows": int(consensus_modes.get("single_lead", 0)),
        },
    }


def run(path, plot_path="static/plots/ecg_plot.png"):
    """Analyze a full ECG file in core windows with bilateral context.

    The source file remains untouched. Only a small rolling signal buffer,
    timestamped R peaks, and event references are retained in memory.
    """
    sampling_rate = expected_interval = None
    input_mode = analysis_lead = None
    recorded_leads = ()
    start_time = end_time = previous_time = None
    sample_count = 0
    r_peak_times = []
    preview_time = []
    preview_recorded_leads = {}
    left_time = np.array([])
    left_signals = {}
    beat_feature_by_time = {}
    quality_history = {}
    consensus_modes = {}

    chunk_iterator = iter(iter_ecg_csv_chunks(path, ECG_CHUNK_ROWS))
    current = next(chunk_iterator, None)
    next_chunk = next(chunk_iterator, None)

    while current is not None:
        schema, time, signals = current
        if sampling_rate is None:
            sampling_rate, expected_interval = _sampling_rate_from_time(time)
            input_mode = schema.input_mode
            recorded_leads = tuple(schema.lead_indexes)
            analysis_lead = RHYTHM_ANALYSIS_LEAD if input_mode == "ads1298_8_channel" else next(iter(recorded_leads))
            start_time = time[0]

        _validate_regular_sampling(time, expected_interval)
        if previous_time is not None:
            _validate_regular_sampling(np.array([previous_time, time[0]]), expected_interval)

        _append_preview(preview_time, preview_recorded_leads, time, signals, start_time)
        context_samples = max(1, round(ECG_PEAK_CONTEXT_SECONDS * sampling_rate))
        if next_chunk is None:
            right_time = np.array([])
            right_signals = {lead: np.array([]) for lead in signals}
        else:
            _next_schema, next_time, next_signals = next_chunk
            right_time = next_time[:context_samples]
            right_signals = {lead: values[:context_samples] for lead, values in next_signals.items()}

        peak_times, quality, consensus, features = _detect_window_r_peaks(
            time, signals, sampling_rate, left_time, left_signals, right_time, right_signals, analysis_lead
        )
        core_start, core_end = time[0], time[-1]
        core_peaks = peak_times[(peak_times >= core_start) & (peak_times <= core_end)]
        r_peak_times.extend(core_peaks)
        for peak_time in core_peaks:
            feature = features.get(round(float(peak_time), 6))
            if feature is not None:
                beat_feature_by_time[round(float(peak_time), 6)] = feature
        for lead, assessment in quality.items():
            quality_history.setdefault(lead, []).append(assessment)
        consensus_modes[consensus["mode"]] = consensus_modes.get(consensus["mode"], 0) + 1

        left_time = time[-context_samples:].copy()
        left_signals = {lead: values[-context_samples:].copy() for lead, values in signals.items()}
        end_time = time[-1]
        previous_time = time[-1]
        sample_count += len(time)
        current = next_chunk
        next_chunk = next(chunk_iterator, None)

    if sampling_rate is None or start_time is None or end_time is None:
        raise ValueError("Plik musi zawierać co najmniej dwie próbki EKG.")

    r_peak_times = np.unique(np.asarray(r_peak_times, dtype=float))
    rr, hr = rr_intervals_from_times(r_peak_times)
    warnings = []
    if len(r_peak_times) < 2:
        warnings.append("Za mało wiarygodnych załamków R do analizy rytmu.")

    window_records = []
    for name, rr_index, feature in classify_premature_beats(r_peak_times, beat_feature_by_time):
        peak_index = rr_index + 1
        window_records.append(
            {
                "name": name,
                "start_time": float(r_peak_times[peak_index]),
                "end_time": float(r_peak_times[peak_index]),
                "kind": "beat",
                "rr_interval_seconds": float(rr[rr_index]),
                "morphology": feature,
            }
        )
    for name, rr_index in detect_pause(rr):
        window_records.append(
            {
                "name": "Pause candidate",
                "start_time": float(r_peak_times[rr_index + 1]),
                "end_time": float(r_peak_times[rr_index + 1]),
                "kind": "beat",
                "rr_interval_seconds": float(rr[rr_index]),
            }
        )
    for name, episode_start, episode_end in detect_rhythm_episodes(r_peak_times):
        window_records.append({"name": name, "start_time": episode_start, "end_time": episode_end, "kind": "episode"})

    results = _merge_adjacent_episodes(window_records, expected_interval * 1.5)
    results = _with_context_bounds(results, start_time, end_time)
    signal_quality = summarise_signal_quality(quality_history)
    report = _automatic_report(
        r_peak_times, rr, hr, results, end_time - start_time, sample_count, signal_quality, consensus_modes
    )
    if signal_quality.get(analysis_lead, {}).get("usable_fraction", 0.0) < 0.90:
        warnings.append("Jakość odprowadzenia rytmu była niewystarczająca w części zapisu; oznaczenia wymagają szczególnej weryfikacji.")
    if consensus_modes.get("primary_lead_fallback", 0):
        warnings.append("W części zapisu nie uzyskano zgodności wielu odprowadzeń dla QRS; użyto oznaczonego trybu awaryjnego.")

    preview_time = np.asarray(preview_time, dtype=float)
    preview_recorded_leads = {
        lead: np.asarray(values, dtype=float) for lead, values in preview_recorded_leads.items()
    }
    is_twelve_lead = input_mode == "ads1298_8_channel"
    preview_ecg = preprocess(preview_recorded_leads[analysis_lead], sampling_rate)
    preview_r_peaks = get_rpeaks(preview_ecg, sampling_rate)

    if plot_path:
        preview_end = preview_time[-1]
        preview_events = [event for event in results if event["context_start"] <= preview_end and event["context_end"] >= start_time]
        plot_ecg(preview_time, preview_ecg, preview_r_peaks, preview_events, output_path=plot_path, lead_name=analysis_lead)
    return {
        "time": preview_time,
        "ecg": preview_ecg,
        "r_peaks": preview_r_peaks,
        "r_peak_times": r_peak_times,
        "r_peak_count": len(r_peak_times),
        "results": results,
        "event_summary": _event_summary(results),
        "event_contexts": results,
        "report": report,
        "warnings": warnings,
        "rr": rr,
        "hr": hr,
        "sampling_rate": sampling_rate,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": end_time - start_time,
        "sample_count": sample_count,
        "is_twelve_lead": is_twelve_lead,
        "analysis_lead": analysis_lead,
        "recorded_leads": tuple(recorded_leads),
        "leads": preview_recorded_leads,
    }


if __name__ == "__main__":
    result = run("uploads/ecg.csv")
    print("=== DETECTED EVENTS ===")
    for event in result["results"]:
        print(event)
