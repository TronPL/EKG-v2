import unittest

import numpy as np

from leads import ADS1298_DIRECT_LEADS, STANDARD_12_LEAD_ORDER, build_standard_12_leads


class StandardLeadDerivationTests(unittest.TestCase):
    def setUp(self):
        self.recorded = {
            "I": np.array([1.0, 2.0, 3.0]),
            "II": np.array([4.0, 6.0, 8.0]),
            "V1": np.array([10.0, 11.0, 12.0]),
            "V2": np.array([20.0, 21.0, 22.0]),
            "V3": np.array([30.0, 31.0, 32.0]),
            "V4": np.array([40.0, 41.0, 42.0]),
            "V5": np.array([50.0, 51.0, 52.0]),
            "V6": np.array([60.0, 61.0, 62.0]),
        }

    def test_calculates_four_derived_limb_leads(self):
        leads = build_standard_12_leads(self.recorded)

        np.testing.assert_allclose(leads["III"], [3.0, 4.0, 5.0])
        np.testing.assert_allclose(leads["aVR"], [-2.5, -4.0, -5.5])
        np.testing.assert_allclose(leads["aVL"], [-1.0, -1.0, -1.0])
        np.testing.assert_allclose(leads["aVF"], [3.5, 5.0, 6.5])

    def test_preserves_direct_chest_leads_and_standard_order(self):
        leads = build_standard_12_leads(self.recorded)

        self.assertEqual(tuple(leads), STANDARD_12_LEAD_ORDER)
        for lead in ADS1298_DIRECT_LEADS:
            np.testing.assert_array_equal(leads[lead], self.recorded[lead])

    def test_rejects_missing_direct_lead(self):
        incomplete = dict(self.recorded)
        incomplete.pop("V6")

        with self.assertRaisesRegex(ValueError, "V6"):
            build_standard_12_leads(incomplete)


if __name__ == "__main__":
    unittest.main()
