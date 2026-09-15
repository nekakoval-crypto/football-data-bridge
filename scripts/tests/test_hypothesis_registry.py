import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_hypothesis_registry import validate_registry  # noqa: E402


class HypothesisRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ROOT / "config" / "pbk_hypothesis_registry.json").read_text(encoding="utf-8"))
        cls.scope = json.loads((ROOT / "config" / "pbk_competition_scope.json").read_text(encoding="utf-8"))

    def test_current_registry_is_valid(self):
        self.assertEqual(validate_registry(self.registry, self.scope), [])

    def test_r1_definition_drift_is_rejected(self):
        mutated = copy.deepcopy(self.registry)
        row = next(item for item in mutated["hypotheses"] if item["id"] == "R1")
        row["definition"] = "Serie A away favourite, any odds."
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
        row = next(item for item in mutated["hypotheses"] if item["id"] == "HIST_H2H_HOME_AWAY")
        row["definition"] = "Look at prior meetings."
        row["guardrails"] = ["Context only."]
        errors = validate_registry(mutated, self.scope)
        self.assertTrue(any("sample size" in error for error in errors))
        self.assertTrue(any("recency" in error for error in errors))
        self.assertTrue(any("baseline" in error for error in errors))

    def test_locked_16_league_scope_is_required(self):
        scope = copy.deepcopy(self.scope)
        scope["total_leagues"] = 17
        errors = validate_registry(self.registry, scope)
        self.assertTrue(any("exactly 16 leagues" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
