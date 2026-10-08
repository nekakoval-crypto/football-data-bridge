from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import factor_registry as m


class FactorRegistryTests(unittest.TestCase):
    def test_registry_declares_all_required_layers_without_scoring(self):
        payload = {
            "lineup_context": {"available": True},
            "player_grade": {"available": False},
            "style_matchup": {"available": True},
        }
        registry = m.build_factor_registry(payload)

        self.assertEqual(
            tuple(x["factor_id"] for x in registry["factors"]),
            m.EXPECTED_FACTORS,
        )
        self.assertTrue(registry["all_expected_factors_declared"])
        self.assertEqual(registry["connected_factor_count"], 3)
        self.assertEqual(registry["available_factor_count"], 2)
        self.assertEqual(registry["not_connected_factor_count"], 6)
        self.assertIsNone(registry["aggregate_factor_score"])
        self.assertFalse(registry["aggregate_score_authorized"])
        self.assertTrue(registry["double_counting_guard"])
        self.assertFalse(registry["probability_mutation"])
        self.assertFalse(registry["eligibility_mutation"])
        self.assertFalse(registry["stake_changes"])

    def test_schedule_load_layers_share_double_counting_group(self):
        registry = m.build_factor_registry({})
        by_id = {x["factor_id"]: x for x in registry["factors"]}
        self.assertEqual(
            by_id["CONGESTION"]["double_counting_group"],
            by_id["INTERNATIONAL_LOAD"]["double_counting_group"],
        )
        self.assertEqual(
            by_id["MOTIVATION"]["status"],
            "NOT_CONNECTED_TO_MATCH_PASSPORT",
        )


if __name__ == "__main__":
    unittest.main()
