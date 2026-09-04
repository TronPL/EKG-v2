"""Multi-lead QRS agreement utilities.

Only physically recorded leads are passed here; derived limb leads must never
be treated as independent evidence.
"""

import numpy as np

from config import QRS_CONSENSUS_TOLERANCE_SECONDS


def fuse_r_peak_times(peaks_by_lead, primary_lead, tolerance_seconds=QRS_CONSENSUS_TOLERANCE_SECONDS):
    """Fuse per-lead detections and return consensus times plus provenance.

    With two or more usable leads, a peak needs support from two distinct
    leads.  If that yields no peaks, the primary lead is retained as an
    explicitly marked fallback so poor lead agreement cannot silently erase a
    whole recording.
    """
    primary = np.asarray(peaks_by_lead.get(primary_lead, ()), dtype=float)
    points = sorted((float(time), lead) for lead, peaks in peaks_by_lead.items() for time in peaks)
    if not points:
        return np.array([]), {"mode": "no_peaks", "usable_leads": (), "agreement": 0.0}

    groups, group = [], [points[0]]
    for point in points[1:]:
        if point[0] - group[0][0] <= tolerance_seconds:
            group.append(point)
        else:
            groups.append(group)
            group = [point]
    groups.append(group)

    usable_leads = tuple(peaks_by_lead)
    required_support = 2 if len(usable_leads) >= 2 else 1
    accepted = [group for group in groups if len({lead for _, lead in group}) >= required_support]
    if accepted:
        times = np.asarray([np.median([time for time, _ in group]) for group in accepted], dtype=float)
        agreement = float(np.mean([len({lead for _, lead in group}) / len(usable_leads) for group in accepted]))
        return times, {"mode": "multi_lead_consensus" if required_support == 2 else "single_lead", "usable_leads": usable_leads, "agreement": agreement}

    return primary, {"mode": "primary_lead_fallback", "usable_leads": usable_leads, "agreement": 0.0}
