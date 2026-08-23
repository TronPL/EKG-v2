import numpy as np

from arrhythmia.basic import detect_af, detect_tachy_brady
from arrhythmia.rhythm import detect_pause
from arrhythmia.supraventricular import detect_pac, detect_sveb, detect_svt
from arrhythmia.ventricular import detect_bigeminy_trigeminy, detect_pvc
from config import (
    ECG_CHUNK_ROWS,
    ECG_PEAK_CONTEXT_SECONDS,
    ECG_PREVIEW_SECONDS,
    ECG_REVIEW_CONTEXT_SECONDS,
    MAX_SAMPLING_JITTER_RATIO,
    TWELVE_LEAD_OVERVIEW_SECONDS,
)
from features import rr_intervals_from_times
from io_utils import iter_ecg_csv_chunks
from leads import RHYTHM_ANALYSIS_LEAD, build_standard_12_leads
from preprocessing import preprocess
from rpeaks import get_rpeaks
from visualization import plot_12_lead_ecg, plot_ecg


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
    intervals = np.diff(time)
    if len(intervals) == 0:
        return
    relative_error = np.abs(intervals - expected_interval) / expected_interval
    if np.any(relative_error > MAX_SAMPLING_JITTER_RATIO):
        raise ValueError(
            "Zapis ma luki lub nieregularne próbkowanie. "
            "Przed analizą należy go podzielić na ciągłe fragmenty albo resamplować."
        )


def _append_preview(preview_time, preview_leads, time, signals, start_time):
    if preview_time and preview_time[-1] >= start_time + ECG_PREVIEW_SECONDS:
        return
    end = np.searchsorted(time, start_time + ECG_PREVIEW_SECONDS, side="right")
    if end == 0:
        return
    preview_time.extend(time[:end])
    for lead, values in signals.items():
        preview_leads.setdefault(lead, []).extend(values[:end])


def _detect_window_r_peaks(core_time, core_ecg, sampling_rate, left_time, left_ecg, right_time, right_ecg):
    """Detect R peaks in one core with left and right signal context."""
    window_time = np.concatenate((left_time, core_time, right_time))
    window_ecg = np.concatenate((left_ecg, core_ecg, right_ecg))
    cleaned = preprocess(window_ecg, sampling_rate)
    return window_time[get_rpeaks(cleaned, sampling_rate)]


def _window_event_records(peak_times, core_start, core_end):
    """Classify a context window and retain only events owned by its core."""
    if len(peak_times) < 2:
        return []

    rr, hr = rr_intervals_from_times(peak_times)
    candidates = []
    candidates += detect_tachy_brady(hr)
    candidates += detect_af(rr)
    candidates += detect_pvc(rr)
    candidates += detect_bigeminy_trigeminy(rr)
    candidates += detect_pac(rr)
    candidates += detect_sveb(rr)
    candidates += detect_svt(hr, rr)
    candidates += detect_pause(rr)

    records = []
    for candidate in candidates:
        if isinstance(candidate, tuple):
            name, rr_index = candidate
            peak_index = rr_index + 1
            if not 0 <= peak_index < len(peak_times):
                continue
            event_time = float(peak_times[peak_index])
            if core_start <= event_time <= core_end:
                records.append({"name": name, "start_time": event_time, "end_time": event_time, "kind": "beat"})
        else:
            # Window-wide rules become episodes. Adjacent cores are merged later.
            records.append(
                {"name": candidate, "start_time": float(core_start), "end_time": float(core_end), "kind": "episode"}
            )
    return records


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


def run(path, plot_path="static/plots/ecg_plot.png", twelve_lead_plot_path=None):
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
    core_windows = []
    preview_time = []
    preview_recorded_leads = {}
    left_time = np.array([])
    left_ecg = np.array([])

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
        core_ecg = signals[analysis_lead]
        context_samples = max(1, round(ECG_PEAK_CONTEXT_SECONDS * sampling_rate))
        if next_chunk is None:
            right_time = np.array([])
            right_ecg = np.array([])
        else:
            _next_schema, next_time, next_signals = next_chunk
            right_time = next_time[:context_samples]
            right_ecg = next_signals[analysis_lead][:context_samples]

        peak_times = _detect_window_r_peaks(
            time, core_ecg, sampling_rate, left_time, left_ecg, right_time, right_ecg
        )
        core_start, core_end = time[0], time[-1]
        r_peak_times.extend(peak_times[(peak_times >= core_start) & (peak_times <= core_end)])
        core_windows.append((core_start, core_end))

        left_time = time[-context_samples:].copy()
        left_ecg = core_ecg[-context_samples:].copy()
        end_time = time[-1]
        previous_time = time[-1]
        sample_count += len(time)
        current = next_chunk
        next_chunk = next(chunk_iterator, None)

    if sampling_rate is None or start_time is None or end_time is None:
        raise ValueError("Plik musi zawierać co najmniej dwie próbki EKG.")

    r_peak_times = np.asarray(r_peak_times, dtype=float)
    rr, hr = rr_intervals_from_times(r_peak_times)
    warnings = []
    if len(r_peak_times) < 2:
        warnings.append("Za mało wiarygodnych załamków R do analizy rytmu.")

    window_records = []
    for core_start, core_end in core_windows:
        # Use peaks from the whole recording, not a finite raw-signal overlap.
        # Three beats on each side are enough for local RR rules; crucially, the
        # preceding beat is retained even when a pause crosses a core boundary.
        first_peak = max(0, np.searchsorted(r_peak_times, core_start, side="left") - 3)
        last_peak = min(len(r_peak_times), np.searchsorted(r_peak_times, core_end, side="right") + 3)
        window_records.extend(_window_event_records(r_peak_times[first_peak:last_peak], core_start, core_end))

    results = _merge_adjacent_episodes(window_records, expected_interval * 1.5)
    results = _with_context_bounds(results, start_time, end_time)

    preview_time = np.asarray(preview_time, dtype=float)
    preview_recorded_leads = {
        lead: np.asarray(values, dtype=float) for lead, values in preview_recorded_leads.items()
    }
    is_twelve_lead = input_mode == "ads1298_8_channel"
    preview_leads = build_standard_12_leads(preview_recorded_leads) if is_twelve_lead else preview_recorded_leads
    preview_ecg = preprocess(preview_leads[analysis_lead], sampling_rate)
    preview_r_peaks = get_rpeaks(preview_ecg, sampling_rate)

    if plot_path:
        preview_end = preview_time[-1]
        preview_events = [event for event in results if event["context_start"] <= preview_end and event["context_end"] >= start_time]
        plot_ecg(preview_time, preview_ecg, preview_r_peaks, preview_events, output_path=plot_path, lead_name=analysis_lead)
    if is_twelve_lead and twelve_lead_plot_path:
        plot_12_lead_ecg(
            preview_time,
            preview_leads,
            output_path=twelve_lead_plot_path,
            overview_seconds=TWELVE_LEAD_OVERVIEW_SECONDS,
        )

    return {
        "time": preview_time,
        "ecg": preview_ecg,
        "r_peaks": preview_r_peaks,
        "r_peak_times": r_peak_times,
        "r_peak_count": len(r_peak_times),
        "results": results,
        "event_summary": _event_summary(results),
        "event_contexts": results,
        "warnings": warnings,
        "rr": rr,
        "hr": hr,
        "sampling_rate": sampling_rate,
        "duration_seconds": end_time - start_time,
        "sample_count": sample_count,
        "is_twelve_lead": is_twelve_lead,
        "analysis_lead": analysis_lead,
        "recorded_leads": tuple(recorded_leads),
        "leads": preview_leads,
    }


if __name__ == "__main__":
    result = run("uploads/ecg.csv")
    print("=== DETECTED EVENTS ===")
    for event in result["results"]:
        print(event)
