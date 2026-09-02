"""CSV input helpers for legacy one-channel and ADS1298 12-lead ECG files."""

import re
from dataclasses import dataclass
from itertools import chain

import numpy as np
import pandas as pd

from leads import ADS1298_DIRECT_LEADS


_TIME_HEADERS = {"TIME", "CZAS", "TIMESTAMP", "SECONDS", "SECOND", "SEC", "T"}
_LEAD_HEADERS = {
    "I": {"I", "LEADI", "ECGI", "CH1", "CHANNEL1", "ADC1"},
    "II": {"II", "LEADII", "ECGII", "CH2", "CHANNEL2", "ADC2"},
    "V1": {"V1", "LEADV1", "ECGV1", "CH3", "CHANNEL3", "ADC3"},
    "V2": {"V2", "LEADV2", "ECGV2", "CH4", "CHANNEL4", "ADC4"},
    "V3": {"V3", "LEADV3", "ECGV3", "CH5", "CHANNEL5", "ADC5"},
    "V4": {"V4", "LEADV4", "ECGV4", "CH6", "CHANNEL6", "ADC6"},
    "V5": {"V5", "LEADV5", "ECGV5", "CH7", "CHANNEL7", "ADC7"},
    "V6": {"V6", "LEADV6", "ECGV6", "CH8", "CHANNEL8", "ADC8"},
}


@dataclass(frozen=True)
class ECGInputSchema:
    """Column layout detected in an ECG CSV file."""

    time_index: int
    lead_indexes: dict[str, int]
    input_mode: str


def _normalise_header(value):
    return re.sub(r"[^A-Z0-9]", "", str(value).replace("\ufeff", "").upper())


def _read_raw_csv(path):
    try:
        return pd.read_csv(path, header=None, sep=None, engine="python", comment="#")
    except (OSError, pd.errors.ParserError) as exc:
        raise ValueError("Nie można odczytać pliku CSV.") from exc


def _has_header(data):
    if data.empty:
        return False
    return pd.to_numeric(data.iloc[0, :2], errors="coerce").isna().any()


def _column_indexes_from_header(headers):
    time_index = next((index for index, name in enumerate(headers) if name in _TIME_HEADERS), None)
    lead_indexes = {}

    for lead, aliases in _LEAD_HEADERS.items():
        index = next((index for index, name in enumerate(headers) if name in aliases), None)
        if index is not None:
            lead_indexes[lead] = index

    return time_index, lead_indexes


def _numeric_signals(data, time_index, lead_indexes):
    selected_indexes = [time_index, *lead_indexes.values()]
    numeric_data = data.iloc[:, selected_indexes].apply(pd.to_numeric, errors="coerce").dropna()

    if len(numeric_data) < 3:
        raise ValueError("Plik musi zawierać co najmniej trzy poprawne, numeryczne próbki EKG.")

    time = numeric_data.iloc[:, 0].to_numpy(dtype=float)
    signals = {
        lead: numeric_data.iloc[:, position + 1].to_numpy(dtype=float)
        for position, lead in enumerate(lead_indexes)
    }

    if not np.all(np.isfinite(time)) or any(not np.all(np.isfinite(values)) for values in signals.values()):
        raise ValueError("Czas i amplitudy EKG muszą być skończonymi wartościami liczbowymi.")
    if np.any(np.diff(time) <= 0):
        raise ValueError("Kolumna czasu musi rosnąć w kolejnych wierszach.")

    return time, signals


def _schema_from_first_row(data):
    """Determine the ECG layout without loading the full recording."""
    if data.empty or data.shape[1] < 2:
        raise ValueError("Plik musi zawierać co najmniej dwie kolumny: czas i amplitudę EKG.")

    if _has_header(data):
        headers = [_normalise_header(value) for value in data.iloc[0]]
        time_index, lead_indexes = _column_indexes_from_header(headers)

        if len(lead_indexes) == len(ADS1298_DIRECT_LEADS):
            if time_index is None:
                raise ValueError("Dla pliku ADS1298 kolumna czasu musi mieć nagłówek time, czas lub timestamp.")
            return ECGInputSchema(time_index, lead_indexes, "ads1298_8_channel"), True

        if data.shape[1] >= 9:
            missing = [lead for lead in ADS1298_DIRECT_LEADS if lead not in lead_indexes]
            raise ValueError(
                "Niekompletny plik ADS1298. Wymagane są nagłówki I, II, V1–V6 "
                "albo CH1–CH8. Brakuje: " + ", ".join(missing) + "."
            )

        return ECGInputSchema(0, {"II": 1}, "single_channel"), True

    if data.shape[1] >= 9:
        lead_indexes = {lead: position + 1 for position, lead in enumerate(ADS1298_DIRECT_LEADS)}
        return ECGInputSchema(0, lead_indexes, "ads1298_8_channel"), False

    return ECGInputSchema(0, {"II": 1}, "single_channel"), False


def inspect_ecg_csv(path):
    """Return a CSV schema after reading only its first record."""
    try:
        first_row = pd.read_csv(path, header=None, sep=None, engine="python", comment="#", nrows=1)
    except (OSError, pd.errors.ParserError) as exc:
        raise ValueError("Nie można odczytać pliku CSV.") from exc


def _separator_from_file(path):
    """Determine one of the two documented separators for fast chunk parsing."""
    try:
        with open(path, encoding="utf-8-sig") as file:
            for line in file:
                candidate = line.strip()
                if candidate and not candidate.startswith("#"):
                    return ";" if candidate.count(";") >= candidate.count(",") else ","
    except OSError as exc:
        raise ValueError("Nie można odczytać pliku CSV.") from exc
    raise ValueError("Plik EKG jest pusty.")

    schema, _has_header_row = _schema_from_first_row(first_row)
    return schema


def _numeric_chunk(data, schema):
    """Convert one input block while refusing silent sample removal.

    Dropping malformed rows would make a regular recording look continuous and
    corrupt RR timing.  Empty trailing lines are harmless; every other invalid
    row is therefore reported to the caller.
    """
    selected_indexes = [schema.time_index, *schema.lead_indexes.values()]
    selected = data.iloc[:, selected_indexes]
    numeric_data = selected.apply(pd.to_numeric, errors="coerce")
    nonempty_rows = selected.notna().any(axis=1)
    invalid_rows = nonempty_rows & numeric_data.isna().any(axis=1)
    if invalid_rows.any():
        raise ValueError("Plik zawiera brakującą lub nienumeryczną próbkę EKG.")

    numeric_data = numeric_data.loc[nonempty_rows]
    time = numeric_data.iloc[:, 0].to_numpy(dtype=float)
    signals = {
        lead: numeric_data.iloc[:, position + 1].to_numpy(dtype=float)
        for position, lead in enumerate(schema.lead_indexes)
    }

    if not np.all(np.isfinite(time)) or any(not np.all(np.isfinite(values)) for values in signals.values()):
        raise ValueError("Czas i amplitudy EKG muszą być skończonymi wartościami liczbowymi.")
    return time, signals


def iter_ecg_csv_chunks(path, chunk_rows):
    """Yield validated ECG blocks without materialising a whole Holter file.

    The first yielded value is ``(schema, time, signals)``.  Timestamps are
    checked across block boundaries, so callers can safely use them for RR
    calculation instead of reconstructing time from sample indexes.
    """
    try:
        separator = _separator_from_file(path)
        chunks = pd.read_csv(path, header=None, sep=separator, comment="#", chunksize=chunk_rows)
        first_chunk = next(chunks, None)
    except (OSError, pd.errors.ParserError) as exc:
        raise ValueError("Nie można odczytać pliku CSV.") from exc

    if first_chunk is None:
        raise ValueError("Plik EKG jest pusty.")

    schema, has_header = _schema_from_first_row(first_chunk)
    last_time = None

    try:
        for chunk_number, raw_chunk in enumerate(chain((first_chunk,), chunks)):
            data = raw_chunk.iloc[1:] if chunk_number == 0 and has_header else raw_chunk
            if data.empty:
                continue

            time, signals = _numeric_chunk(data, schema)
            if len(time) == 0:
                continue
            if np.any(np.diff(time) <= 0) or (last_time is not None and time[0] <= last_time):
                raise ValueError("Kolumna czasu musi rosnąć w kolejnych wierszach.")
            last_time = time[-1]
            yield schema, time, signals
    finally:
        chunks.close()


def load_ecg_time_range(path, start_time, end_time, chunk_rows):
    """Load an all-lead context interval from a persisted source recording.

    This deliberately re-reads the immutable source file instead of keeping a
    full 24-hour waveform in memory. Callers use the time bounds saved in an
    analysis manifest to retrieve a clinician-reviewable 12-lead snippet.
    """
    if end_time < start_time:
        raise ValueError("Koniec kontekstu EKG nie może być wcześniejszy niż początek.")

    schema = None
    time_parts = []
    signal_parts = {}
    for schema, time, signals in iter_ecg_csv_chunks(path, chunk_rows):
        if time[0] > end_time:
            break
        selected = (time >= start_time) & (time <= end_time)
        if not selected.any():
            continue
        time_parts.append(time[selected])
        for lead, values in signals.items():
            signal_parts.setdefault(lead, []).append(values[selected])

    if schema is None or not time_parts:
        raise ValueError("Nie znaleziono próbek EKG w żądanym kontekście.")
    return (
        schema,
        np.concatenate(time_parts),
        {lead: np.concatenate(parts) for lead, parts in signal_parts.items()},
    )


def load_ecg_csv(path):
    """Load a legacy one-channel file or an eight-channel ADS1298 CSV file.

    ADS1298 mode expects time + CH1..CH8 (or I, II, V1..V6) in the column
    order described in README. A legacy file uses the first two columns only.
    """
    data = _read_raw_csv(path)
    if data.shape[1] < 2:
        raise ValueError("Plik musi zawierać co najmniej dwie kolumny: czas i amplitudę EKG.")

    if _has_header(data):
        headers = [_normalise_header(value) for value in data.iloc[0]]
        payload = data.iloc[1:].reset_index(drop=True)
        time_index, lead_indexes = _column_indexes_from_header(headers)

        if len(lead_indexes) == len(ADS1298_DIRECT_LEADS):
            if time_index is None:
                raise ValueError("Dla pliku ADS1298 kolumna czasu musi mieć nagłówek time, czas lub timestamp.")
            return (*_numeric_signals(payload, time_index, lead_indexes), "ads1298_8_channel")

        if data.shape[1] >= 9:
            missing = [lead for lead in ADS1298_DIRECT_LEADS if lead not in lead_indexes]
            raise ValueError(
                "Niekompletny plik ADS1298. Wymagane są nagłówki I, II, V1–V6 "
                "albo CH1–CH8. Brakuje: " + ", ".join(missing) + "."
            )

        # A labelled but non-ADS1298 file stays compatible with the original two-column upload format.
        return (*_numeric_signals(payload, 0, {"II": 1}), "single_channel")

    if data.shape[1] >= 9:
        lead_indexes = {lead: position + 1 for position, lead in enumerate(ADS1298_DIRECT_LEADS)}
        return (*_numeric_signals(data, 0, lead_indexes), "ads1298_8_channel")

    return (*_numeric_signals(data, 0, {"II": 1}), "single_channel")


def load_csv(path):
    """Backward-compatible single-channel loader used by older code."""
    time, signals, _mode = load_ecg_csv(path)
    return time, signals["II"]


def infer_sampling_rate(time, fallback_fs):
    """Infer Hz from the time column, falling back when it is not usable."""
    intervals = np.diff(time)
    positive_intervals = intervals[intervals > 0]

    if len(positive_intervals) == 0:
        return fallback_fs

    inferred_fs = 1 / np.median(positive_intervals)
    return float(inferred_fs) if np.isfinite(inferred_fs) and inferred_fs > 0 else fallback_fs
