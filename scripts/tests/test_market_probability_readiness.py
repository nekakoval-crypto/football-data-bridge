import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_market_probability_readiness as target

ROOT = Path(__file__).resolve().parents[2]
CFG = json.loads((ROOT / "config/pbk_market_probability_readiness.json").read_text(encoding="utf-8"))
CORE = json.loads((ROOT / "config/pbk_core_market_registry.json").read_text(encoding="utf-8"))


class MarketProbabilityReadinessTests(unittest.TestCase):
    def test_current_contract_is_valid(self):
        self.assertEqual(target.validate(CFG, CORE), [])

    def test_all_core_eight_are_present(self):
        self.assertEqual(len(CFG["markets"]), 8)
        self.assertEqual(
            {row["id"] for row in CFG["markets"]},
            {row["id"] for row in CORE["markets"]},
        )

    def test_no_model_cannot_claim_value(self):
        cfg = copy.deepcopy(CFG)
        row = next(x for x in cfg["markets"] if x["id"] == "BTTS")
        row["value_allowed"] = "YES"
        errors = target.validate(cfg, CORE)
        self.assertTrue(any("value must be forbidden" in e for e in errors))

    def test_no_model_cannot_claim_validated_context(self):
        cfg = copy.deepcopy(CFG)
        row = next(x for x in cfg["markets"] if x["id"] == "TEAM_TOTAL")
        row["validated_contexts"] = ["HOME_OVER_1_5"]
        errors = target.validate(cfg, CORE)
        self.assertTrue(any("cannot have validated_contexts" in e for e in errors))

    def test_generic_1x2_is_not_silently_promoted(self):
        cfg = copy.deepcopy(CFG)
        row = next(x for x in cfg["markets"] if x["id"] == "MATCH_RESULT_1X2")
        row["pbk_probability_status"] = "VALIDATED"
        errors = target.validate(cfg, CORE)
        self.assertTrue(any("PARTIAL_VALIDATED" in e for e in errors))

    def test_r1_r2_r3_contexts_cannot_disappear(self):
        cfg = copy.deepcopy(CFG)
        row = next(x for x in cfg["markets"] if x["id"] == "MATCH_RESULT_1X2")
        row["validated_contexts"] = ["R1_AWAY_WIN"]
        errors = target.validate(cfg, CORE)
        self.assertTrue(any("R1/R2/R3" in e for e in errors))

    def test_market_no_vig_must_not_be_called_pbk_probability(self):
        cfg = copy.deepcopy(CFG)
        cfg["guardrails"]["market_no_vig_is_not_pbk_probability"] = False
        errors = target.validate(cfg, CORE)
        self.assertTrue(any("market_no_vig_is_not_pbk_probability" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
