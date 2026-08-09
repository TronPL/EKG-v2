"""CSV input helpers for legacy one-channel and ADS1298 12-lead ECG files."""

import re

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
