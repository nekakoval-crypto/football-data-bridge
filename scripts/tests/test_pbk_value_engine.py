import json
import tempfile
import unittest
from pathlib import Path

from scripts import pbk_value_engine as ve


CFG_PATH = Path(__file__).resolve().parents[2] / "config" / "pbk_value_engine.json"
CFG = json.loads(CFG_PATH.read_text(encoding="utf-8"))


def option(**overrides):
    row = {
        "market_family": "MATCH_RESULT_1X2",
        "line": None,
        "selection": "Away",
        "selection_label": "P2",
        "availability_status": "AVAILABLE",
        "reference_bookmaker": "Bet365",
        "reference_price": 1.80,
        "executable": True,
        "executable_price": 1.90,
        "executable_bookmaker": "Marathonbet",
        "p_market": 0.55,
        "p_market_model_input": 0.54,
        "probability_status": "VALIDATED_CANONICAL_CONTEXT",
        "validated_context": "R2",
        "matching_validated_contexts": ["R2", "R1"],
        "model_version": "stage75_v1_2026-09-11",
        "p_pbk": 0.60,
        "generic_1x2_research_status": None,
        "p_pbk_research_candidate": None,
    }
    row.update(overrides)
    return row


def payload(rows):
    return {
        "status": "OK",
        "engine_version": "PBK_PROBABILITY_ENGINE_V1",
        "reports": [{
            "fixture": {"api_fixture_id": "100", "kickoff_utc": "2026-09-20T12:00:00Z"},
            "options": rows,
        }],
    }


class ValueEngineTests(unittest.TestCase):
    def test_strong_value_is_official_and_ranked(self):
        result = ve.build_value_engine(payload([option(p_pbk=0.60, executable_price=1.90)]), CFG)
        item = result["reports"][0]["official_candidates"][0]
        self.assertEqual(item["value_status"], "STRONG_VALUE")
        self.assertTrue(item["official_ranking_eligible"])
        self.assertAlmostEqual(item["ev"], 0.14)
        self.assertEqual(result["reports"][0]["best_official_value"]["validated_context"], "R2")

    def test_watch_threshold_is_inclusive_and_does_not_create_stage_watch(self):
        # p=.61, odds=1.70 -> EV=3.7%, execution edge ~2.18pp: WATCH but not STRONG.
        row = option(p_pbk=0.61, executable_price=1.70, p_market=0.58)
        result = ve.build_value_engine(payload([row]), CFG)
        item = result["reports"][0]["official_candidates"][0]
        self.assertEqual(item["value_status"], "VALUE_WATCH")
        self.assertFalse(item["creates_stage_watch"])

    def test_market_disagreement_requires_missing_execution(self):
        row = option(p_pbk=0.62, p_market=0.55, executable=False, executable_price=None)
        result = ve.build_value_engine(payload([row]), CFG)
        item = result["reports"][0]["official_candidates"][0]
        self.assertEqual(item["value_status"], "MARKET_DISAGREEMENT")
        self.assertFalse(item["official_ranking_eligible"])
        self.assertIsNone(result["reports"][0]["best_official_value"])

    def test_no_validated_model_never_gets_value_even_if_fields_are_spoofed(self):
        row = option(
            market_family="MATCH_TOTAL",
            selection="O",
            selection_label="TB",
            line=2.5,
            probability_status="NO_VALIDATED_MODEL",
            p_pbk=0.90,
            executable_price=2.00,
        )
        result = ve.build_value_engine(payload([row]), CFG)
        report = result["reports"][0]
        self.assertEqual(report["official_candidates"], [])
        self.assertIsNone(report["best_official_value"])
        self.assertEqual(result["official_value_candidates"], 0)

    def test_generic_1x2_research_candidate_is_visible_but_not_value_authorized(self):
        row = option(
            probability_status="NO_VALIDATED_MODEL",
            p_pbk=None,
            generic_1x2_research_status="FORWARD_REVIEW_REQUIRED_PER_LEAGUE",
            p_pbk_research_candidate=0.64,
            executable_price=2.10,
        )
        result = ve.build_value_engine(payload([row]), CFG)
        research = result["reports"][0]["research_only_candidates"][0]
        self.assertEqual(research["value_status"], "RESEARCH_ONLY_NOT_VALUE_AUTHORIZED")
        self.assertIsNone(research["ev"])
        self.assertFalse(research["official_ranking_eligible"])
        self.assertEqual(result["official_ranked_candidates"], 0)

    def test_longshot_tag_requires_strong_value(self):
        row = option(p_pbk=0.55, executable_price=2.10, p_market=0.48)
        result = ve.build_value_engine(payload([row]), CFG)
        item = result["reports"][0]["official_candidates"][0]
        self.assertEqual(item["value_status"], "STRONG_VALUE")
        self.assertIn("LONGSHOT_STRONG", item["tags"])

    def test_best_value_is_selected_within_fixture(self):
        strong = option(selection="Away", selection_label="P2", p_pbk=0.58, executable_price=2.00, validated_context="R2")
        watch = option(selection="Draw", selection_label="X", p_pbk=0.35, executable_price=3.05, p_market=0.31, validated_context="R3", matching_validated_contexts=["R3"])
        result = ve.build_value_engine(payload([watch, strong]), CFG)
        best = result["reports"][0]["best_official_value"]
        self.assertEqual(best["value_status"], "STRONG_VALUE")
        self.assertEqual(best["selection_label"], "P2")

    def test_waiting_probability_engine_is_fail_closed(self):
        result = ve.build_value_engine({"status": "WAITING_FOR_FULL_MARKET_SCANNER", "reports": []}, CFG)
        self.assertEqual(result["status"], "WAITING_FOR_PROBABILITY_ENGINE")
        self.assertEqual(result["official_value_candidates"], 0)
        self.assertEqual(result["official_ranked_candidates"], 0)

    def test_policy_has_zero_side_effect_authority(self):
        result = ve.build_value_engine(payload([option()]), CFG)
        policy = result["policy"]
        self.assertEqual(policy["api_calls_added"], 0)
        self.assertEqual(policy["signals_created"], 0)
        self.assertEqual(policy["stage_watch_created"], 0)
        self.assertFalse(policy["stake_changes"])
        self.assertFalse(policy["canonical_changes"])
        self.assertFalse(policy["r1_r2_r3_changes"])
        self.assertFalse(policy["ui_changes"])

    def test_run_writes_output_without_provider_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inp = root / "probability.json"
            out = root / "value.json"
            cfg = dict(CFG)
            cfg["input"] = str(inp)
            cfg["output"] = str(out)
            cfg_path = root / "cfg.json"
            inp.write_text(json.dumps(payload([option()])), encoding="utf-8")
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            result = ve.run(cfg_path)
            self.assertTrue(out.exists())
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["policy"]["api_calls_added"], 0)


if __name__ == "__main__":
    unittest.main()
