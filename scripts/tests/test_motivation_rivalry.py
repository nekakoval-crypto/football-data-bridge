import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import motivation_rivalry


class MotivationRivalryTests(unittest.TestCase):
    def test_madrid_derby_is_verified_in_both_directions(self):
        first = motivation_rivalry.lookup_rivalry(
            "Atletico Madrid",
            "Real Madrid",
        )
        second = motivation_rivalry.lookup_rivalry(
            "Real Madrid",
            "Atlético de Madrid",
        )
        for payload in (first, second):
            self.assertEqual(payload["status"], "VERIFIED")
            self.assertTrue(payload["derby"])
            self.assertTrue(payload["principled_rivalry"])
            self.assertTrue(payload["independent_of_table_pressure"])
            self.assertEqual(payload["rivalry_id"], "MADRID_DERBY_REAL_ATLETICO")

    def test_unknown_pair_stays_unknown(self):
        payload = motivation_rivalry.lookup_rivalry("Alpha", "Beta")
        self.assertEqual(payload["status"], "UNKNOWN")
        self.assertFalse(payload["derby"])
        self.assertIsNone(payload["rivalry_id"])

    def test_no_fuzzy_match(self):
        payload = motivation_rivalry.lookup_rivalry(
            "Real Madrd",
            "Atletico Madrid",
        )
        self.assertEqual(payload["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
