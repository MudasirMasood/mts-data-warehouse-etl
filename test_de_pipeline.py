import unittest
from de_etl_lab import make_lead_hash, normalize_code


class TestMTSDataPipeline(unittest.TestCase):
    def test_normalize_code_handles_messy_inputs(self):
        self.assertEqual(normalize_code("ot2"), "OT-02")
        self.assertEqual(normalize_code("  icu-2 "), "ICU-02")
        self.assertEqual(normalize_code("RAD12"), "RAD-12")
        self.assertEqual(normalize_code("OT-01"), "OT-01")

    def test_lead_hash_is_deterministic_and_case_insensitive(self):
        h1 = make_lead_hash("Begam Jan Hospital", "ot-02")
        h2 = make_lead_hash("  begam jan hospital  ", "OT-02")
        h3 = make_lead_hash("Begam Jan Hospital", "ICU-02")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)
        self.assertEqual(len(h1), 16)


if __name__ == "__main__":
    unittest.main(verbosity=2)
