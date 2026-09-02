import tempfile
import unittest
from pathlib import Path

import numpy as np

from features import rr_intervals_from_times
from io_utils import iter_ecg_csv_chunks, load_ecg_time_range
from sampling import validate_regular_sampling


class StreamingInputTests(unittest.TestCase):
    def test_reads_ads1298_file_in_multiple_chunks(self):
        headers = "time;CH1;CH2;CH3;CH4;CH5;CH6;CH7;CH8\n"
        rows = [
            f"{index / 500:.3f};" + ";".join(str(index + channel) for channel in range(8))
            for index in range(8)
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecg.csv"
            path.write_text(headers + "\n".join(rows), encoding="utf-8")
            blocks = list(iter_ecg_csv_chunks(path, chunk_rows=3))

        self.assertGreater(len(blocks), 1)
        self.assertTrue(all(schema.input_mode == "ads1298_8_channel" for schema, _, _ in blocks))
        time = np.concatenate([time for _, time, _ in blocks])
        lead_ii = np.concatenate([signals["II"] for _, _, signals in blocks])
        np.testing.assert_allclose(time, np.arange(8) / 500)
        np.testing.assert_array_equal(lead_ii, np.arange(1, 9))

    def test_rr_uses_r_peak_timestamps(self):
        rr, hr = rr_intervals_from_times([10.0, 10.8, 11.6])

        np.testing.assert_allclose(rr, [0.8, 0.8])
        np.testing.assert_allclose(hr, [75.0, 75.0])

    def test_accepts_interval_exactly_on_jitter_limit(self):
        # Decimal timestamps can turn a 3 ms interval into a value just below
        # 3 ms after binary floating-point subtraction.
        time = np.array([223.884, 223.888, 223.891, 223.895])

        validate_regular_sampling(time, expected_interval=0.004)

    def test_rejects_a_real_sampling_gap(self):
        time = np.array([0.000, 0.004, 0.012])

        with self.assertRaisesRegex(ValueError, "luki"):
            validate_regular_sampling(time, expected_interval=0.004)

    def test_loads_all_leads_for_a_saved_context(self):
        headers = "time;CH1;CH2;CH3;CH4;CH5;CH6;CH7;CH8\n"
        rows = [
            f"{index / 10:.1f};" + ";".join(str(index + channel) for channel in range(8))
            for index in range(6)
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ecg.csv"
            path.write_text(headers + "\n".join(rows), encoding="utf-8")
            schema, time, signals = load_ecg_time_range(path, 0.2, 0.4, chunk_rows=2)

        self.assertEqual(schema.input_mode, "ads1298_8_channel")
        np.testing.assert_allclose(time, [0.2, 0.3, 0.4])
        self.assertEqual(set(signals), {"I", "II", "V1", "V2", "V3", "V4", "V5", "V6"})


if __name__ == "__main__":
    unittest.main()
