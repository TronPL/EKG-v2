import numpy as np
import pandas as pd


def load_csv(path):
    """Load time and voltage from the first two numeric columns of a CSV file."""
    try:
        # sep=None detects common delimiters such as ';' and ','. A header row,
        # when present, is discarded below because it is not numeric.
        data = pd.read_csv(path, header=None, sep=None, engine="python", comment="#")
    except (OSError, pd.errors.ParserError) as exc:
        raise ValueError("Nie można odczytać pliku CSV.") from exc

    if data.shape[1] < 2:
        raise ValueError("Plik musi zawierać co najmniej dwie kolumny: czas i amplitudę EKG.")

    numeric_data = data.iloc[:, :2].apply(pd.to_numeric, errors="coerce").dropna()
    if len(numeric_data) < 3:
        raise ValueError("Plik musi zawierać co najmniej trzy poprawne, numeryczne próbki EKG.")

    time = numeric_data.iloc[:, 0].to_numpy(dtype=float)
    voltage = numeric_data.iloc[:, 1].to_numpy(dtype=float)

    if not np.all(np.isfinite(time)) or not np.all(np.isfinite(voltage)):
        raise ValueError("Czas i amplituda EKG muszą być skończonymi wartościami liczbowymi.")

    if np.any(np.diff(time) <= 0):
        raise ValueError("Kolumna czasu musi rosnąć w kolejnych wierszach.")

    return time, voltage


def infer_sampling_rate(time, fallback_fs):
    """Infer Hz from the time column, falling back when it is not usable."""
    intervals = np.diff(time)
    positive_intervals = intervals[intervals > 0]

    if len(positive_intervals) == 0:
        return fallback_fs

    inferred_fs = 1 / np.median(positive_intervals)
    return float(inferred_fs) if np.isfinite(inferred_fs) and inferred_fs > 0 else fallback_fs
