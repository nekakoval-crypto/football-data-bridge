import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_hypothesis_registry import EXPECTED_LIFECYCLE, validate_registry  # noqa: E402


class HypothesisRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ROOT / "config" / "pbk_hypothesis_registry.json").read_text(encoding="utf-8"))
        cls.scope = json.loads((ROOT / "config" / "pbk_competition_scope.json").read_text(encoding="utf-8"))

    def row(self, registry, row_id):
        return next(item for item in registry["hypotheses"] if item["id"] == row_id)

    def test_current_registry_is_valid(self):
        self.assertEqual(validate_registry(self.registry, self.scope), [])

    def test_v2_lifecycle_is_exact_and_data_ready_is_not_status(self):
        self.assertEqual(self.registry["status_lifecycle"], EXPECTED_LIFECYCLE)
        self.assertNotIn("DATA_READY", self.registry["status_lifecycle"])
        self.assertTrue(all(row["status"] != "DATA_READY" for row in self.registry["hypotheses"]))

    def test_every_row_has_explicit_inventory_columns(self):
        required = {
            "id", "idea", "market_scope", "selection_scope", "competition_scope",
            "filters", "data_dependencies", "evidence_stage", "status", "data_readiness",
        }
        for row in self.registry["hypotheses"]:
            self.assertTrue(required.issubset(row), row["id"])
            self.assertEqual(set(row["evidence_stage"]), {"hist", "train", "test", "forward"}, row["id"])

    def test_r1_definition_drift_is_rejected(self):
        mutated = copy.deepcopy(self.registry)
        self.row(mutated, "R1")["definition"] = "Serie A away favourite, any odds."
        errors = validate_registry(mutated, self.scope)
        self.assertTrue(any("R1: locked definition drifted" in error for error in errors))

    def test_duplicate_id_is_rejected(self):
        mutated = copy.deepcopy(self.registry)
        mutated["hypotheses"].append(copy.deepcopy(mutated["hypotheses"][0]))
        errors = validate_registry(mutated, self.scope)
        self.assertIn("hypothesis ids must be unique", errors)

    def test_auto_promotion_is_rejected(self):
        mutated = copy.deepcopy(self.registry)
        mutated["auto_promotion"] = True
        errors = validate_registry(mutated, self.scope)
        self.assertIn("auto_promotion must remain false", errors)

    def test_h2h_requires_recency_sample_and_baseline_controls(self):
        mutated = copy.deepcopy(self.registry)
        row = self.row(mutated, "HIST_H2H_HOME_AWAY")
        row["definition"] = "Look at prior meetings."
        row["guardrails"] = ["Context only."]
        errors = validate_registry(mutated, self.scope)
        self.assertTrue(any("sample size" in error for error in errors))
        self.assertTrue(any("recency" in error for error in errors))
        self.assertTrue(any("baseline" in error for error in errors))

    def test_generic_1x2_remains_pooled_historical_and_per_league_forward(self):
        row = self.row(self.registry, "GENERIC_1X2_PROBABILITY_V1")
        self.assertEqual(row["status"], "FORWARD")
        self.assertEqual(row["authority"], "RESEARCH")
        self.assertEqual(row["validation_scope"], "PER_LEAGUE_FORWARD_ONLY")
        self.assertEqual(row["evidence_stage"]["test"], "PASSED_POOLED_BIG5_OOS_ONLY")
        self.assertEqual(row["evidence_stage"]["forward"], "COLLECTING_PER_LEAGUE")

    def test_generic_1x2_cannot_be_silently_promoted(self):
        mutated = copy.deepcopy(self.registry)
        row = self.row(mutated, "GENERIC_1X2_PROBABILITY_V1")
        row["status"] = "CANONICAL"
        row["authority"] = "CANONICAL"
        errors = validate_registry(mutated, self.scope)
        self.assertTrue(any("must remain FORWARD/RESEARCH" in error for error in errors))

    def test_market_inventory_contains_user_required_sides(self):
        self.assertEqual(self.row(self.registry, "MARKET_1X2_HOME_FAVOURITE")["selection_scope"], ["P1"])
        self.assertEqual(self.row(self.registry, "MARKET_1X2_AWAY_FAVOURITE")["selection_scope"], ["P2"])
        self.assertEqual(self.row(self.registry, "MARKET_1X2_DRAW")["selection_scope"], ["X"])
        self.assertEqual(
            set(self.row(self.registry, "MARKET_TEAM_TOTALS")["selection_scope"]),
            {"ITB1", "ITM1", "ITB2", "ITM2"},
        )
        self.assertEqual(
            set(self.row(self.registry, "MARKET_DOUBLE_CHANCE")["selection_scope"]),
            {"1X", "X2", "12"},
        )
        for row_id in ("MARKET_DNB", "MARKET_EUROPEAN_HANDICAP", "MARKET_ASIAN_HANDICAP", "MARKET_HALF_HANDICAPS"):
            self.assertIn(row_id, {row["id"] for row in self.registry["hypotheses"]})

    def test_absence_and_return_are_separate_work_items(self):
        combined = self.row(self.registry, "ABSENCE_RETURN_IMPACT")
        self.assertEqual(combined["status"], "PAUSED")
        self.assertEqual(set(combined["deprecated_by"]), {"ABSENCE_IMPACT", "RETURN_IMPACT"})
        self.row(self.registry, "ABSENCE_IMPACT")
        self.row(self.registry, "RETURN_IMPACT")

    def test_probability_cannot_transfer_between_markets(self):
        mutated = copy.deepcopy(self.registry)
        row = self.row(mutated, "PROBABILITY_VALUE_ALL_MARKETS")
        row["guardrails"] = [guard for guard in row["guardrails"] if "transfer probability" not in guard]
        errors = validate_registry(mutated, self.scope)
        self.assertTrue(any("forbid probability transfer" in error for error in errors))

    def test_locked_16_league_scope_is_required(self):
        scope = copy.deepcopy(self.scope)
        scope["total_leagues"] = 17
        errors = validate_registry(self.registry, scope)
        self.assertTrue(any("exactly 16 leagues" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
