import copy
import csv
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import research_generic_1x2_probability_v1 as target

CFG = json.loads((ROOT / "config/pbk_generic_1x2_probability_v1.json").read_text(encoding="utf-8"))


class Generic1X2ProbabilityV1Tests(unittest.TestCase):
    def test_contract_is_research_only_and_data_required(self):
        self.assertEqual(CFG["status"], "PREREGISTERED_DATA_REQUIRED")
        self.assertEqual(CFG["authority"], "RESEARCH")
        self.assertTrue(CFG["governance"]["r1_r2_r3_unchanged"])
        self.assertTrue(CFG["governance"]["no_betting_signal_generation"])
        self.assertTrue(CFG["governance"]["no_value_until_gate_passes"])

    def test_split_is_locked_and_disjoint(self):
        train = set(CFG["split"]["train_seasons"])
        test = set(CFG["split"]["test_seasons"])
        self.assertFalse(train & test)
        self.assertEqual(train, {"2019/20", "2020/21", "2021/22", "2022/23"})
        self.assertEqual(test, {"2023/24", "2024/25", "2025/26"})
        self.assertTrue(CFG["split"]["test_never_used_for_fit_or_model_selection"])

    def test_canonical_schema_uses_lowercase_season(self):
        self.assertIn("season", CFG["dataset"]["required_columns"])
        self.assertNotIn("Season", CFG["dataset"]["required_columns"])

    def test_load_rows_assigns_lowercase_season_to_locked_split(self):
        fields = ["Div", "season", "FTR", "B365H", "B365D", "B365A"]
        rows = [
            {"Div": "E0", "season": "2019/20", "FTR": "H", "B365H": "2.0", "B365D": "3.0", "B365A": "4.0"},
            {"Div": "E0", "season": "2023/24", "FTR": "D", "B365H": "2.1", "B365D": "3.1", "B365A": "3.9"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8", delete=False) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
            source = Path(handle.name)
        try:
            train, test, rejected = target.load_rows(source, CFG)
        finally:
            os.unlink(source)
        self.assertEqual([outcome for _, outcome in train], ["H"])
        self.assertEqual([outcome for _, outcome in test], ["D"])
        self.assertEqual(rejected, {})

    def test_market_no_vig_sums_to_one(self):
        p = target.market_probabilities({"B365H": "2.00", "B365D": "3.50", "B365A": "4.00"})
        self.assertAlmostEqual(sum(p), 1.0, places=12)
        self.assertTrue(all(0 < x < 1 for x in p))

    def test_multiclass_shift_always_sums_to_one(self):
        p = (0.45, 0.28, 0.27)
        q = target.shifted_probabilities(p, 0.23, -0.14)
        self.assertAlmostEqual(sum(q), 1.0, places=12)
        self.assertTrue(all(0 < x < 1 for x in q))

    def test_fit_uses_two_offsets_with_draw_fixed_zero(self):
        train = []
        base = (1 / 3, 1 / 3, 1 / 3)
        train += [(base, "H")] * 60
        train += [(base, "D")] * 25
        train += [(base, "A")] * 15
        fit = target.fit_train(train, CFG)
        self.assertEqual(fit["alpha_d"], 0.0)
        self.assertGreater(fit["alpha_h"], 0.0)
        self.assertLess(fit["alpha_a"], 0.0)

    def test_synthetic_holdout_can_pass_only_through_locked_gate(self):
        cfg = copy.deepcopy(CFG)
        cfg["test_gate"]["minimum_test_rows"] = 100
        cfg["test_gate"]["minimum_test_outcomes_per_class"] = 10
        cfg["test_gate"]["maximum_absolute_class_calibration_error"] = 0.04
        base = (1 / 3, 1 / 3, 1 / 3)
        train = [(base, "H")] * 60 + [(base, "D")] * 25 + [(base, "A")] * 15
        test = [(base, "H")] * 60 + [(base, "D")] * 25 + [(base, "A")] * 15
        result = target.evaluate(train, test, cfg)
        self.assertEqual(result["status"], "PASS_HISTORICAL_PROBABILITY_GATE")
        self.assertLess(result["test"]["m1_logloss"], result["test"]["m0_logloss"])
        self.assertLess(result["test"]["m1_multiclass_brier"], result["test"]["m0_multiclass_brier"])
        self.assertFalse(result["canonical_rules_changed"])
        self.assertFalse(result["value_authorized"])

    def test_failed_gate_cannot_authorize_value(self):
        cfg = copy.deepcopy(CFG)
        cfg["test_gate"]["minimum_test_rows"] = 1000
        base = (0.5, 0.25, 0.25)
        train = [(base, "H")] * 5 + [(base, "D")] * 3 + [(base, "A")] * 2
        test = list(train)
        result = target.evaluate(train, test, cfg)
        self.assertEqual(result["status"], "FAIL_HISTORICAL_PROBABILITY_GATE")
        self.assertFalse(result["value_authorized"])
        self.assertFalse(result["stake_changes_authorized"])


if __name__ == "__main__":
    unittest.main()

