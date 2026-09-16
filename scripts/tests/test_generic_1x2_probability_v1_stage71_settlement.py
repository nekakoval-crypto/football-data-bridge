import json
import tempfile
import unittest
from pathlib import Path

from scripts import generic_1x2_probability_v1_forward as fwd
from scripts import generic_1x2_probability_v1_stage71_settlement as adapter


BIG5 = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
EXTENDED = [
    "Austrian Bundesliga", "Belgian Pro League", "Danish Superliga", "A Lyga",
    "Virsliga", "Eredivisie", "Eliteserien", "Ekstraklasa", "Primeira Liga",
    "Super Lig", "Scottish Premiership",
]


class Generic1X2Stage71SettlementTests(unittest.TestCase):
    def config(self):
        return {
            "research_id": "PBK_GENERIC_1X2_PROBABILITY_V1_FORWARD",
            "model_version": "PBK_GENERIC_1X2_PROBABILITY_V1",
            "scope": {
                "locked_total_leagues": 16,
                "tracked_leagues": BIG5 + EXTENDED,
                "historical_big5_pooled_leagues": BIG5,
                "historically_unvalidated_leagues": EXTENDED,
            },
            "frozen_model": {"alpha_h": -0.018, "alpha_d": 0.0, "alpha_a": -0.004},
            "capture_policy": {"snapshot": "FIRST_COMPLETE_VALID_BET365_PREMATCH_OBSERVATION"},
            "forward_review": {
                "review_unit": "LEAGUE",
                "pooled_big5_diagnostic_only": True,
                "combined_16_league_verdict": False,
                "diagnostic_checkpoints_per_league": [250, 500],
                "minimum_settled_rows_per_league": 1000,
                "minimum_settled_outcomes_per_class_per_league": 150,
                "maximum_absolute_class_calibration_error": 0.03,
            },
            "guards": {"probability_sum_tolerance": 1e-9},
            "outputs": {
                "prematch_journal": "generic_1x2_v1_forward_prematch.jsonl",
                "settlement_journal": "generic_1x2_v1_forward_settlements.jsonl",
                "performance_report": "generic_1x2_v1_forward_performance.json",
            },
        }

    def prematch(self, fixture_id="1001", league="Premier League"):
        cfg = self.config()
        return fwd.observation_to_event({
            "fixture_id": fixture_id,
            "league": league,
            "home_team": "Home",
            "away_team": "Away",
            "kickoff_utc": "2026-09-20T15:00:00Z",
            "observed_at_utc": "2026-09-20T10:00:00Z",
            "b365_home": "2.10",
            "b365_draw": "3.40",
            "b365_away": "3.60",
        }, cfg, process_time="2026-09-20T12:00:00Z")

    def test_result_from_score(self):
        self.assertEqual(adapter.result_from_score("2", "1"), "H")
        self.assertEqual(adapter.result_from_score("1", "1"), "D")
        self.assertEqual(adapter.result_from_score("0", "3"), "A")
        self.assertIsNone(adapter.result_from_score("", "1"))

    def test_only_exact_ft_with_frozen_prematch_is_eligible(self):
        prematch = [self.prematch()]
        rows = [
            {"fixture_id": "1001", "status": "finished", "source_status": "FT",
             "score_home": "2", "score_away": "1", "observed_at_utc": "2026-09-20T17:00:00Z"},
            {"fixture_id": "1002", "status": "finished", "source_status": "FT",
             "score_home": "1", "score_away": "0", "observed_at_utc": "2026-09-20T17:00:00Z"},
        ]
        eligible, meta = adapter.rows_from_overlay(rows, prematch, [])
        self.assertEqual(eligible, [{
            "fixture_id": "1001", "result": "H", "settled_at_utc": "2026-09-20T17:00:00Z"
        }])
        self.assertEqual(meta["without_frozen_prematch"], 1)

    def test_aet_penalty_or_nonfinished_rows_are_not_settled(self):
        prematch = [self.prematch()]
        rows = [
            {"fixture_id": "1001", "status": "finished", "source_status": "AET",
             "score_home": "2", "score_away": "1", "observed_at_utc": "2026-09-20T17:00:00Z"},
            {"fixture_id": "1001", "status": "live", "source_status": "2H",
             "score_home": "1", "score_away": "1", "observed_at_utc": "2026-09-20T16:00:00Z"},
        ]
        eligible, meta = adapter.rows_from_overlay(rows, prematch, [])
        self.assertEqual(eligible, [])
        self.assertEqual(meta["not_exact_ft"], 1)
        self.assertEqual(meta["not_finished"], 1)

    def test_existing_settlement_is_not_repeated(self):
        prematch = [self.prematch()]
        settlement = fwd.settlement_to_event({
            "fixture_id": "1001", "result": "D", "settled_at_utc": "2026-09-20T17:00:00Z"
        }, {"1001": prematch[0]})
        eligible, meta = adapter.rows_from_overlay([{
            "fixture_id": "1001", "status": "finished", "source_status": "FT",
            "score_home": "2", "score_away": "1", "observed_at_utc": "2026-09-20T17:05:00Z"
        }], prematch, [settlement])
        self.assertEqual(eligible, [])
        self.assertEqual(meta["already_settled"], 1)

    def test_settlement_timestamp_must_be_after_kickoff(self):
        prematch = [self.prematch()]
        eligible, _ = adapter.rows_from_overlay([{
            "fixture_id": "1001", "status": "finished", "source_status": "FT",
            "score_home": "2", "score_away": "1", "observed_at_utc": "2026-09-20T14:59:00Z"
        }], prematch, [])
        added, rejected = fwd.settle_rows(eligible, prematch, [])
        self.assertEqual(added, [])
        self.assertEqual(rejected[0]["reason"], "settlement must occur after kickoff")

    def test_full_run_appends_settlement_and_reports_zero_provider_calls(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            historical = td / "historical.json"
            historical.write_text(json.dumps({
                "final_verdict": "PASS_HISTORICAL_PROBABILITY_GATE",
                "execution": {"no_posthoc_tuning": True},
                "authorization": {"production_integration_authorized": False},
                "fit": {"alpha_h": -0.018, "alpha_d": 0.0, "alpha_a": -0.004},
            }), encoding="utf-8")
            cfg = self.config()
            cfg["historical_result_path"] = str(historical)
            cfg["historical_result_required_verdict"] = "PASS_HISTORICAL_PROBABILITY_GATE"
            config_path = td / "forward.json"
            config_path.write_text(json.dumps(cfg), encoding="utf-8")

            prematch = self.prematch()
            Path(td, cfg["outputs"]["prematch_journal"]).write_text(
                json.dumps(prematch) + "\n", encoding="utf-8")
            overlay = td / "live_fixture_overlay.csv"
            overlay.write_text(
                "fixture_id,status,source_status,score_home,score_away,observed_at_utc\n"
                "1001,finished,FT,1,1,2026-09-20T17:00:00Z\n",
                encoding="utf-8")

            result = adapter.run(td, config_path=config_path, overlay_path=overlay)
            self.assertEqual(result["provider_calls_added"], 0)
            self.assertEqual(result["settlements_added"], 1)
            self.assertEqual(result["settled_rows"], 1)
            settlement_path = td / cfg["outputs"]["settlement_journal"]
            event = json.loads(settlement_path.read_text(encoding="utf-8").strip())
            self.assertEqual(event["payload"]["result"], "D")
            self.assertFalse(event["payload"]["creates_signal"])
            self.assertFalse(event["payload"]["value_authorized"])


if __name__ == "__main__":
    unittest.main()
