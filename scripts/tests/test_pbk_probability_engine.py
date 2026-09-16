import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from pbk_probability_engine import (  # noqa: E402
    attach_probabilities,
    load_json,
    market_probability,
    run,
)


def option(family, selection, label, ref, exe, line=None, executable=True, status="AVAILABLE_EXECUTABLE"):
    return {
        "market_family": family,
        "selection": selection,
        "selection_label": label,
        "line": line,
        "reference_bookmaker": "Bet365",
        "reference_price": ref,
        "executable_bookmaker": "Marathonbet",
        "executable_price": exe,
        "best_observed_price": exe,
        "best_observed_bookmaker": "Marathonbet",
        "availability_status": status,
        "executable": executable,
    }


def scanner_payload():
    rows = [
        option("MATCH_RESULT_1X2", "P1", "P1", 2.00, 2.10),
        option("MATCH_RESULT_1X2", "X", "X", 3.40, 3.30),
        option("MATCH_RESULT_1X2", "P2", "P2", 3.80, 3.70),
        option("DOUBLE_CHANCE", "1X", "1X", 1.25, 1.27),
        option("DOUBLE_CHANCE", "X2", "X2", 1.75, 1.78),
        option("DOUBLE_CHANCE", "12", "12", 1.30, 1.31),
        option("DRAW_NO_BET", "H", "F1(0)", 1.55, 1.58, 0.0),
        option("DRAW_NO_BET", "A", "F2(0)", 2.35, 2.30, 0.0),
        option("ASIAN_HANDICAP", "H", "F1(-0.5)", 1.95, 2.00, -0.5),
        option("ASIAN_HANDICAP", "A", "F2(0.5)", 1.95, 1.90, 0.5),
        option("ASIAN_HANDICAP", "H", "F1(-0.25)", 1.90, 1.92, -0.25, False, "BLOCKED_QUARTER_ASIAN_HANDICAP"),
        option("ASIAN_HANDICAP", "A", "F2(0.25)", 2.00, 1.98, 0.25, False, "BLOCKED_QUARTER_ASIAN_HANDICAP"),
        option("EUROPEAN_HANDICAP", "H", "EH1(-1)", 3.20, 3.25, -1),
        option("EUROPEAN_HANDICAP", "D", "EHX(-1)", 3.60, 3.55, -1),
        option("EUROPEAN_HANDICAP", "A", "EH2(-1)", 1.95, 1.97, -1),
        option("MATCH_TOTAL", "O", "TB(2.5)", 1.85, 1.88, 2.5),
        option("MATCH_TOTAL", "U", "TM(2.5)", 2.00, 1.98, 2.5),
        option("MATCH_TOTAL", "O", "TB(2)", 1.70, 1.72, 2.0),
        option("MATCH_TOTAL", "U", "TM(2)", 2.20, 2.15, 2.0),
        option("BTTS", "YES", "YES", 1.72, 1.75),
        option("BTTS", "NO", "NO", 2.05, 2.02),
        option("TEAM_TOTAL_HOME", "O", "ITB1(1.5)", 1.90, 1.93, 1.5),
        option("TEAM_TOTAL_HOME", "U", "ITM1(1.5)", 1.90, 1.87, 1.5),
        option("TEAM_TOTAL_AWAY", "O", "ITB2(0.5)", 1.70, 1.72, 0.5),
        option("TEAM_TOTAL_AWAY", "U", "ITM2(0.5)", 2.10, 2.08, 0.5),
    ]
    return {
        "status": "OK",
        "reports": [{
            "fixture": {
                "api_fixture_id": "1001",
                "league": "Premier League",
                "league_id": 39,
                "kickoff_utc": "2026-09-20T15:00:00Z",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
            },
            "options": rows,
            "coverage": {},
        }],
    }


def predictions():
    return [
        {
            "prediction_id": "r1",
            "model_version": "stage75_v1_2026-09-11",
            "rule": "R1",
            "api_fixture_id": "1001",
            "selection": "Away",
            "p_market_no_vig": "0.280000000",
            "p_pbk": "0.600000000",
            "status": "FROZEN_PREMATCH",
        },
        {
            "prediction_id": "r2",
            "model_version": "stage75_v1_2026-09-11",
            "rule": "R2",
            "api_fixture_id": "1001",
            "selection": "Away",
            "p_market_no_vig": "0.290000000",
            "p_pbk": "0.640000000",
            "status": "FROZEN_PREMATCH",
        },
        {
            "prediction_id": "r3",
            "model_version": "stage75_v1_2026-09-11",
            "rule": "R3",
            "api_fixture_id": "1001",
            "selection": "Draw",
            "p_market_no_vig": "0.260000000",
            "p_pbk": "0.300000000",
            "status": "FROZEN_PREMATCH",
        },
    ]


def generic_rows():
    return [{
        "fixture_id": "1001",
        "league": "Premier League",
        "authority": "RESEARCH",
        "forward_only": True,
        "value_authorized": False,
        "p_market": {"H": 0.46, "D": 0.25, "A": 0.29},
        "p_m1": {"H": 0.45, "D": 0.25, "A": 0.30},
    }]


class ProbabilityEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine_cfg = load_json(ROOT / "config" / "pbk_probability_engine.json")
        cls.model_cfg = load_json(ROOT / "config" / "pbk_probability_models.json")

    def result(self):
        return attach_probabilities(
            scanner_payload(), predictions(), self.model_cfg, self.engine_cfg, generic_rows()
        )

    def row(self, result, label):
        return next(x for x in result["reports"][0]["options"] if x["selection_label"] == label)

    def test_r2_priority_over_r1_on_same_exact_selection(self):
        result = self.result()
        row = self.row(result, "P2")
        self.assertEqual(row["probability_status"], "VALIDATED_CANONICAL_CONTEXT")
        self.assertEqual(row["validated_context"], "R2")
        self.assertEqual(row["matching_validated_contexts"], ["R2", "R1"])
        self.assertAlmostEqual(row["p_market_model_input"], 0.29)
        self.assertAlmostEqual(row["p_pbk"], 0.64)
        self.assertAlmostEqual(row["fair_odds"], 1 / 0.64)
        self.assertAlmostEqual(row["edge_vs_model_market"], 0.35)
        self.assertAlmostEqual(row["ev"], 0.64 * 3.70 - 1.0)

    def test_r3_draw_is_exact_context_only(self):
        result = self.result()
        draw = self.row(result, "X")
        home = self.row(result, "P1")
        self.assertEqual(draw["validated_context"], "R3")
        self.assertAlmostEqual(draw["p_pbk"], 0.30)
        self.assertEqual(home["probability_status"], "NO_VALIDATED_MODEL")
        self.assertIsNone(home["p_pbk"])
        self.assertIsNone(home["fair_odds"])
        self.assertIsNone(home["ev"])

    def test_generic_1x2_is_research_candidate_not_official_probability(self):
        result = self.result()
        home = self.row(result, "P1")
        away = self.row(result, "P2")
        self.assertEqual(home["generic_1x2_research_status"], "FORWARD_REVIEW_REQUIRED_PER_LEAGUE")
        self.assertAlmostEqual(home["p_pbk_research_candidate"], 0.45)
        self.assertIsNone(home["p_pbk"])
        self.assertAlmostEqual(away["p_pbk_research_candidate"], 0.30)
        self.assertAlmostEqual(away["p_pbk"], 0.64)

    def test_market_probability_semantics_are_explicit(self):
        result = self.result()
        self.assertEqual(self.row(result, "P1")["p_market_status"], "NO_VIG_VALID_EXHAUSTIVE")
        self.assertEqual(self.row(result, "TB(2.5)")["p_market_status"], "NO_VIG_VALID_EXHAUSTIVE")
        self.assertEqual(self.row(result, "TB(2)")["p_market_status"], "NO_VIG_CONDITIONAL_ON_NO_PUSH")
        self.assertEqual(self.row(result, "F1(0)")["p_market_status"], "NO_VIG_CONDITIONAL_ON_NO_PUSH")
        self.assertEqual(self.row(result, "1X")["p_market_status"], "RAW_IMPLIED_ONLY_OVERLAPPING_OUTCOMES")
        self.assertEqual(self.row(result, "F1(-0.25)")["p_market_status"], "BLOCKED_EXECUTION_LINE_RAW_ONLY")

    def test_non_1x2_markets_never_inherit_r1_r2_r3_probability(self):
        result = self.result()
        for label in ("TB(2.5)", "YES", "ITB1(1.5)", "F1(-0.5)", "EH1(-1)", "1X"):
            row = self.row(result, label)
            self.assertEqual(row["probability_status"], "NO_VALIDATED_MODEL")
            self.assertIsNone(row["p_pbk"])
            self.assertIsNone(row["fair_odds"])
            self.assertIsNone(row["edge_vs_model_market"])
            self.assertIsNone(row["ev"])

    def test_market_probability_can_exist_without_pbk_model(self):
        result = self.result()
        total = self.row(result, "TB(2.5)")
        self.assertIsNotNone(total["p_market"])
        self.assertIsNotNone(total["p_market_no_vig"])
        self.assertIsNone(total["p_pbk"])
        self.assertIsNone(total["ev"])

    def test_engine_has_zero_signal_stake_or_canonical_authority(self):
        result = self.result()
        policy = result["policy"]
        self.assertEqual(policy["api_calls_added"], 0)
        self.assertEqual(policy["signals_created"], 0)
        self.assertEqual(policy["watch_created"], 0)
        self.assertFalse(policy["stake_changes"])
        self.assertFalse(policy["canonical_changes"])
        self.assertFalse(policy["r1_r2_r3_changes"])
        self.assertFalse(policy["ui_changes"])
        self.assertFalse(policy["cross_market_probability_transfer"])
        self.assertFalse(policy["cross_line_probability_transfer"])
        self.assertFalse(policy["cross_selection_probability_transfer"])

    def test_waiting_state_when_scanner_has_not_materialized(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = dict(self.engine_cfg)
            cfg["inputs"] = dict(cfg["inputs"])
            cfg["inputs"]["full_market_scanner"] = str(root / "missing.json")
            cfg["output"] = str(root / "out.json")
            cfg_path = root / "cfg.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            result = run(cfg_path)
            saved = json.loads((root / "out.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "WAITING_FOR_FULL_MARKET_SCANNER")
        self.assertEqual(saved["fixture_reports"], 0)
        self.assertEqual(saved["policy"]["api_calls_added"], 0)


if __name__ == "__main__":
    unittest.main()
