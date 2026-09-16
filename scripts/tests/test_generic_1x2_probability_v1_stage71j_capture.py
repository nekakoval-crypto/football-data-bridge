import json
import tempfile
import unittest
from pathlib import Path

from scripts import generic_1x2_probability_v1_stage71j_capture as adapter


BIG5 = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
EXTENDED = [
    "Austrian Bundesliga", "Belgian Pro League", "Danish Superliga", "A Lyga",
    "Virsliga", "Eredivisie", "Eliteserien", "Ekstraklasa", "Primeira Liga",
    "Super Lig", "Scottish Premiership",
]
LEAGUES = {
    "Premier League": 39, "La Liga": 140, "Serie A": 135, "Bundesliga": 78,
    "Ligue 1": 61, "Austrian Bundesliga": 218, "Belgian Pro League": 144,
    "Danish Superliga": 119, "A Lyga": 362, "Virsliga": 365,
    "Eredivisie": 88, "Eliteserien": 103, "Ekstraklasa": 106,
    "Primeira Liga": 94, "Super Lig": 203, "Scottish Premiership": 179,
}


class Generic1X2Stage71JCaptureTests(unittest.TestCase):
    process_time = "2026-09-20T12:00:00Z"

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

    def cache(self, league="Premier League", fixture_id="1001", update="2026-09-20T10:00:00Z",
              complete=True, bet365_home="2.10"):
        league_id = LEAGUES[league]
        values = [
            {"value": "Home", "odd": bet365_home},
            {"value": "Draw", "odd": "3.40"},
        ]
        if complete:
            values.append({"value": "Away", "odd": "3.60"})
        return {
            ("/fixtures", (("league", str(league_id)), ("next", "10"), ("season", "2026"), ("timezone", "UTC"))): {
                "response": [{
                    "fixture": {"id": int(fixture_id), "date": "2026-09-20T15:00:00Z"},
                    "teams": {"home": {"name": "Home"}, "away": {"name": "Away"}},
                }]
            },
            ("/odds", (("fixture", fixture_id),)): {
                "response": [{
                    "update": update,
                    "bookmakers": [
                        {"name": "Marathonbet", "bets": [{
                            "id": 1,
                            "name": "Match Winner",
                            "values": [
                                {"value": "Home", "odd": "1.50"},
                                {"value": "Draw", "odd": "4.50"},
                                {"value": "Away", "odd": "6.50"},
                            ],
                        }]},
                        {"name": "Bet365", "bets": [{
                            "id": 1, "name": "Match Winner", "values": values,
                        }]},
                    ],
                }]
            },
        }

    def test_extracts_only_complete_bet365_match_winner(self):
        rows, meta = adapter.rows_from_stage71j_cache(self.cache(), LEAGUES, self.process_time)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["league"], "Premier League")
        self.assertEqual(row["b365_home"], 2.10)
        self.assertEqual(row["b365_draw"], 3.40)
        self.assertEqual(row["b365_away"], 3.60)
        self.assertEqual(row["observed_at_utc"], "2026-09-20T10:00:00Z")
        self.assertEqual(row["source"], adapter.SOURCE)
        self.assertEqual(meta["complete_candidate_rows"], 1)

    def test_incomplete_hda_is_not_candidate(self):
        rows, meta = adapter.rows_from_stage71j_cache(
            self.cache(complete=False), LEAGUES, self.process_time)
        self.assertEqual(rows, [])
        self.assertEqual(meta["missing_complete_bet365_match_winner"], 1)

    def test_missing_or_future_provider_update_is_not_candidate(self):
        cache = self.cache(update="2026-09-20T12:01:00Z")
        rows, _ = adapter.rows_from_stage71j_cache(cache, LEAGUES, self.process_time)
        self.assertEqual(rows, [])
        cache[("/odds", (("fixture", "1001"),))]["response"][0]["update"] = ""
        rows, _ = adapter.rows_from_stage71j_cache(cache, LEAGUES, self.process_time)
        self.assertEqual(rows, [])

    def test_extended_league_is_captured_with_canonical_query_name(self):
        rows, _ = adapter.rows_from_stage71j_cache(
            self.cache(league="Eredivisie"), LEAGUES, self.process_time)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["league"], "Eredivisie")

    def test_first_frozen_observation_is_immutable(self):
        cfg = self.config()
        with tempfile.TemporaryDirectory() as td:
            rows, _ = adapter.rows_from_stage71j_cache(self.cache(), LEAGUES, self.process_time)
            first = adapter.capture_rows(rows, cfg, td, self.process_time)
            self.assertEqual(first["observations_added"], 1)
            changed, _ = adapter.rows_from_stage71j_cache(
                self.cache(bet365_home="1.70", update="2026-09-20T11:00:00Z"),
                LEAGUES, self.process_time)
            second = adapter.capture_rows(changed, cfg, td, self.process_time)
            self.assertEqual(second["observations_added"], 0)
            self.assertEqual(second["rejections"][0]["reason"], "already_frozen")
            prematch = Path(td, "generic_1x2_v1_forward_prematch.jsonl").read_text(encoding="utf-8")
            event = json.loads(prematch.strip())
            self.assertEqual(event["payload"]["b365_home"], 2.10)

    def test_postkickoff_processing_cannot_backfill(self):
        cfg = self.config()
        rows, _ = adapter.rows_from_stage71j_cache(self.cache(), LEAGUES, self.process_time)
        with tempfile.TemporaryDirectory() as td:
            result = adapter.capture_rows(rows, cfg, td, "2026-09-20T15:01:00Z")
        self.assertEqual(result["observations_added"], 0)
        self.assertEqual(result["rejections"][0]["reason"], "historical_backfill_forbidden")

    def test_full_adapter_reports_zero_extra_api_calls(self):
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
            result = adapter.capture_from_stage71j_cache(
                self.cache(), LEAGUES, td, process_time=self.process_time, config_path=config_path)
            self.assertEqual(result["api_calls_added"], 0)
            self.assertEqual(result["observations_added"], 1)
            self.assertFalse(result["settlement_performed"])
            self.assertEqual(result["mode"], "STAGE71J_ZERO_EXTRA_CALL_PROSPECTIVE_CAPTURE")


if __name__ == "__main__":
    unittest.main()
