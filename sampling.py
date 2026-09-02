"""Timestamp validation shared by the import and analysis layers."""

import numpy as np

from config import MAX_SAMPLING_JITTER_RATIO


def validate_regular_sampling(time, expected_interval):
    intervals = np.diff(time)
    if len(intervals) == 0:
        return
    # CSV timestamps are decimal values and their subtraction can introduce a
    # tiny binary floating-point error. Preserve the configured jitter limit,
    # while accepting an interval that lands exactly on that limit (for
    # example 3 ms next to a 4 ms nominal interval).
    jitter_limit = MAX_SAMPLING_JITTER_RATIO * expected_interval
    floating_point_tolerance = 16 * np.finfo(float).eps * max(1.0, np.max(np.abs(time)))
    if np.any(np.abs(intervals - expected_interval) > jitter_limit + floating_point_tolerance):
        raise ValueError(
            "Zapis ma luki lub nieregularne próbkowanie. "
            "Przed analizą należy go podzielić na ciągłe fragmenty albo resamplować."
        )
