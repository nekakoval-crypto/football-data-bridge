import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pbk_value_engine as ve
from pbk_calculation_contract import CONTRACT_VERSION


CFG_PATH = Path(__file__).resolve().parents[2] / "config" / "pbk_value_engine.json"
CFG = json.loads(CFG_PATH.read_text(encoding="utf-8"))


def option(**overrides):
    row = {
        "market_family": "MATCH_RESULT_1X2",
        "line": None,
        "selection": "P2",
        "selection_label": "P2",
        "availability_status": "AVAILABLE_EXECUTABLE",
        "reference_bookmaker": "Bet365",
        "reference_price": 2.02,
        "executable": True,
        "executable_price": 2.00,
        "executable_bookmaker": "Marathonbet",
        "p_market": 0.495,
        "p_market_status": "NO_VIG_VALID_EXHAUSTIVE",
        "p_market_model_input": 0.49,
        "probability_status": "VALIDATED_CANONICAL_CONTEXT",
        "validated_context": "R2",
        "matching_validated_contexts": ["R2", "R1"],
        "model_version": "stage75_v1_2026-09-11",
        "p_pbk": 0.525,
        "generic_1x2_research_status": None,
        "p_pbk_research_candidate": None,
    }
    row.update(overrides)
    return row


def payload(rows):
    return {
        "status": "OK",
        "engine_version": "PBK_PROBABILITY_ENGINE_V1",
        "reports": [
            {
                "fixture": {
                    "api_fixture_id": "100",
                    "kickoff_utc": "2026-09-20T12:00:00Z",
                    "home_team": "Alpha",
                    "away_team": "Beta",
                },
                "options": rows,
            }
        ],
    }


class ValueEngineRecoveryTests(unittest.TestCase):
    def test_strong_value_uses_canonical_calc_contract(self):
        result = ve.build_value_engine(payload([option()]), CFG)
        item = result["reports"][0]["official_candidates"][0]
        self.assertEqual(item["value_status"], "STRONG_VALUE")
        self.assertTrue(item["official_ranking_eligible"])
        self.assertAlmostEqual(item["ev"], 0.05)
        self.assertAlmostEqual(item["edge"], 0.03)
        self.assertEqual(item["calculation_contract_version"], CONTRACT_VERSION)
        self.assertIn("LONGSHOT_STRONG", item["tags"])
        self.assertEqual(
            result["reports"][0]["best_official_value"]["validated_context"], "R2"
        )

    def test_watch_name_matches_existing_radar_contract(self):
        row = option(p_pbk=0.51, p_market=0.49, executable_price=2.00)
        result = ve.build_value_engine(payload([row]), CFG)
        item = result["reports"][0]["official_candidates"][0]
        self.assertEqual(item["value_status"], "WATCH_VALUE")
        self.assertTrue(item["official_ranking_eligible"])
        self.assertFalse(item["creates_stage_watch"])

    def test_market_disagreement_without_execution_is_not_ranked(self):
        row = option(
            p_pbk=0.55,
            p_market=0.50,
            executable=False,
            executable_price=None,
            executable_bookmaker=None,
        )
        result = ve.build_value_engine(payload([row]), CFG)
        item = result["reports"][0]["official_candidates"][0]
        self.assertEqual(item["value_status"], "MARKET_DISAGREEMENT")
        self.assertFalse(item["official_ranking_eligible"])
        self.assertIsNone(item["ev"])
        self.assertIsNone(result["reports"][0]["best_official_value"])

    def test_high_probability_low_value_is_descriptive_only(self):
        row = option(p_pbk=0.65, p_market=0.64, executable_price=1.50)
        result = ve.build_value_engine(payload([row]), CFG)
        item = result["reports"][0]["official_candidates"][0]
        self.assertEqual(item["value_status"], "HIGH_PROB_LOW_VALUE")
        self.assertFalse(item["official_ranking_eligible"])
        self.assertFalse(item["creates_signal"])

    def test_no_validated_model_never_receives_official_value(self):
        row = option(
            market_family="MATCH_TOTAL",
            line=2.5,
            selection="O",
            selection_label="TB(2.5)",
            probability_status="NO_VALIDATED_MODEL",
            p_pbk=0.90,
            executable_price=2.00,
        )
        result = ve.build_value_engine(payload([row]), CFG)
        report = result["reports"][0]
        self.assertEqual(report["official_candidates"], [])
        self.assertIsNone(report["best_official_value"])
        self.assertEqual(result["official_value_candidates"], 0)

    def test_generic_1x2_candidate_is_visible_but_never_value_authorized(self):
        row = option(
            probability_status="NO_VALIDATED_MODEL",
            p_pbk=None,
            generic_1x2_research_status="FORWARD_REVIEW_REQUIRED_PER_LEAGUE",
            p_pbk_research_candidate=0.64,
            executable_price=2.10,
        )
        result = ve.build_value_engine(payload([row]), CFG)
        research = result["reports"][0]["research_only_candidates"][0]
        self.assertEqual(
            research["value_status"], "RESEARCH_ONLY_NOT_VALUE_AUTHORIZED"
        )
        self.assertIsNone(research["ev"])
        self.assertIsNone(research["fair_odds"])
        self.assertFalse(research["official_ranking_eligible"])
        self.assertEqual(result["official_ranked_candidates"], 0)

    def test_invalid_current_market_probability_fails_closed(self):
        row = option(
            p_market_status="RAW_IMPLIED_ONLY_INCOMPLETE_COMPLEMENT",
            p_market=0.50,
        )
        result = ve.build_value_engine(payload([row]), CFG)
        item = result["reports"][0]["official_candidates"][0]
        self.assertEqual(
            item["value_status"], "NO_VALID_CURRENT_MARKET_PROBABILITY"
        )
        self.assertIsNone(item["ev"])
        self.assertFalse(item["official_ranking_eligible"])

    def test_best_official_value_is_selected_within_fixture(self):
        watch = option(
            selection="X",
            selection_label="X",
            validated_context="R3",
            matching_validated_contexts=["R3"],
            p_pbk=0.51,
            p_market=0.49,
            executable_price=2.00,
        )
        strong = option(
            selection="P2",
            selection_label="P2",
            validated_context="R2",
            p_pbk=0.55,
            p_market=0.50,
            executable_price=2.00,
        )
        result = ve.build_value_engine(payload([watch, strong]), CFG)
        best = result["reports"][0]["best_official_value"]
        self.assertEqual(best["value_status"], "STRONG_VALUE")
        self.assertEqual(best["selection_label"], "P2")

    def test_execution_edge_is_informational_not_second_rating_contract(self):
        row = option(p_pbk=0.525, p_market=0.495, executable_price=2.00)
        item = ve.build_value_engine(payload([row]), CFG)["reports"][0][
            "official_candidates"
        ][0]
        self.assertEqual(item["value_status"], "STRONG_VALUE")
        self.assertAlmostEqual(item["execution_edge"], 0.025)
        self.assertTrue(
            ve.policy_payload(CFG)["execution_edge_is_informational_only"]
        )

    def test_waiting_probability_engine_is_fail_closed(self):
        result = ve.build_value_engine(
            {"status": "WAITING_FOR_FULL_MARKET_SCANNER", "reports": []}, CFG
        )
        self.assertEqual(result["status"], "WAITING_FOR_PROBABILITY_ENGINE")
        self.assertEqual(result["official_value_candidates"], 0)
        self.assertEqual(result["official_ranked_candidates"], 0)

    def test_policy_has_zero_side_effect_authority(self):
        policy = ve.build_value_engine(payload([option()]), CFG)["policy"]
        self.assertEqual(policy["api_calls_added"], 0)
        self.assertEqual(policy["signals_created"], 0)
        self.assertEqual(policy["stage_watch_created"], 0)
        self.assertFalse(policy["stake_changes"])
        self.assertFalse(policy["eligibility_mutation"])
        self.assertFalse(policy["canonical_changes"])
        self.assertFalse(policy["r1_r2_r3_changes"])
        self.assertFalse(policy["forward_journal_mutation"])
        self.assertFalse(policy["ui_changes"])

    def test_run_writes_output_without_network(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "probability.json"
            out = root / "value.json"
            cfg = dict(CFG)
            cfg["input"] = str(inp)
            cfg["output"] = str(out)
            cfg_path = root / "cfg.json"
            inp.write_text(json.dumps(payload([option()])), encoding="utf-8")
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            with patch.object(
                socket, "socket", side_effect=AssertionError("Network forbidden")
            ):
                result = ve.run(cfg_path)
            self.assertTrue(out.exists())
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["policy"]["api_calls_added"], 0)

    def test_contract_version_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = json.loads(json.dumps(CFG))
            cfg["calculation_contract"]["version"] = "PBK_CALC_FUTURE"
            cfg["input"] = str(root / "missing.json")
            cfg["output"] = str(root / "out.json")
            cfg_path = root / "cfg.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "expects PBK_CALC_FUTURE"):
                ve.run(cfg_path)


if __name__ == "__main__":
    unittest.main()
