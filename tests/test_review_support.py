import unittest

import numpy as np

from arrhythmia.episodes import detect_rhythm_episodes
from morphology import classify_premature_beats
from qrs_consensus import fuse_r_peak_times
from signal_quality import assess_signal_quality, summarise_signal_quality


class ReviewSupportTests(unittest.TestCase):
    def test_rejects_a_flatline_channel(self):
        quality = assess_signal_quality(np.zeros(500))

        self.assertFalse(quality["accepted"])
        self.assertEqual(quality["reason"], "flatline")

    def test_summarises_per_chunk_quality(self):
        good = assess_signal_quality(np.sin(np.linspace(0, 20, 1000)))
        flat = assess_signal_quality(np.zeros(1000))

        summary = summarise_signal_quality({"II": [good, flat]})

        self.assertEqual(summary["II"]["chunks"], 2)
        self.assertAlmostEqual(summary["II"]["usable_fraction"], 0.5)

    def test_fuses_qrs_supported_by_two_physical_leads(self):
        peaks, provenance = fuse_r_peak_times(
            {"II": [1.000, 2.000], "V1": [1.030, 2.020], "V2": [1.400]}, "II"
        )

        np.testing.assert_allclose(peaks, [1.015, 2.010])
        self.assertEqual(provenance["mode"], "multi_lead_consensus")

    def test_marks_primary_lead_fallback_when_leads_do_not_agree(self):
        peaks, provenance = fuse_r_peak_times({"II": [1.0, 2.0], "V1": [1.2, 2.2]}, "II")

        np.testing.assert_allclose(peaks, [1.0, 2.0])
        self.assertEqual(provenance["mode"], "primary_lead_fallback")

    def test_labels_early_wide_qrs_as_pvc_candidate(self):
        peaks = np.array([0.0, 1.0, 1.5, 2.5, 3.5])
        features = {
            round(time, 6): {"qrs_width_seconds": 0.14, "qrs_shape_similarity": 0.6}
            for time in peaks
        }

        events = classify_premature_beats(peaks, features)

        self.assertEqual(events[0][0], "PVC candidate (QRS morphology)")
        self.assertEqual(events[0][1], 1)

    def test_detects_short_window_tachycardia_candidate(self):
        peaks = np.arange(0.0, 31.0, 0.5)
        episodes = detect_rhythm_episodes(peaks)

        self.assertTrue(any(name == "Tachycardia candidate" for name, _, _ in episodes))


if __name__ == "__main__":
    unittest.main()
