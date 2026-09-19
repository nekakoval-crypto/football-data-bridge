import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_archive_readiness as readiness


class PBK14InternationalWindowMarketReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_csv(self, name, fields, rows):
        with (self.ops / name).open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    def write_json(self, name, payload):
        (self.ops / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def materialize(self, *, player_status="UNVERIFIED", authority=False):
        row = {
            "historical_match_id": "hist-1",
            "api_fixture_id": "9001",
            "mapping_status": "AUTO",
            "mapping_reason": "EXACT_DATE_TEAMS_SCORE_UNIQUE",
            "provider_league_id": "39",
            "season_start": "2024",
            "api_kickoff_utc": "2024-09-14T14:00:00+00:00",
            "league_code": "E0",
            "date_iso": "2024-09-14",
            "player_level_international_status": player_status,
            "final_tournaments_included": "false",
            "non_uefa_only_windows_included": "false",
            "calendar_level_only": "true",
            "as_known_calendar_reference": "true",
            "no_match_result_dependency": "true",
            "no_lookahead": "true",
            "context_provider_calls": "0",
            "fuzzy_string_matching_used": "false",
            "one_to_one_verified": "true",
            "historical_backfill_only": "true",
            "research_only": "true",
            "operational_betting_authority": "true" if authority else "false",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        }
        self.write_csv(
            "pbk14_international_window_market_join_research.csv",
            list(row),
            [row],
        )
        self.write_json(
            "stage80_pbk14_international_window_market_join_last_run.json",
            {
                "version": "PBK_STAGE80_PBK14_INTERNATIONAL_WINDOW_MARKET_JOIN_V1",
                "joined_rows": 1,
                "missing_market_rows": 0,
                "missing_context_rows": 0,
                "bridge_eligible_duplicate_historical_ids": 0,
                "bridge_eligible_duplicate_api_fixture_ids": 0,
                "context_invalid_rows": 0,
                "context_duplicate_fixture_ids": 0,
                "join_coverage_pct": 100.0,
                "closing_1x2_matches": 1,
                "closing_total25_matches": 1,
                "within_72h_before_rows": 0,
                "within_96h_before_rows": 0,
                "within_72h_after_rows": 1,
                "within_96h_after_rows": 1,
                "either_first_domestic_after_window_rows": 1,
                "player_level_international_status": "UNVERIFIED",
                "player_callup_inferred": False,
                "player_travel_inferred": False,
                "player_appearance_inferred": False,
                "review_unmapped_excluded": True,
                "fuzzy_string_matching_used": False,
                "calendar_level_only": True,
                "as_known_calendar_reference": True,
                "no_match_result_dependency": True,
                "no_lookahead": True,
                "provider_calls": 0,
                "research_only": True,
                "operational_betting_authority": False,
                "creates_signal": False,
                "probability_mutation": False,
                "eligibility_mutation": False,
                "stake_changes": False,
                "forward_journal_mutation": False,
            },
        )

    def test_valid_materialization_closes_join_gap(self):
        self.materialize()
        report = readiness.build_report(self.ops, archive_dir="")
        layer = report["pbk14_international_window_market_join"]
        self.assertTrue(layer["meta_valid"])
        self.assertEqual(layer["valid_rows"], 1)
        self.assertEqual(layer["invalid_rows"], 0)
        self.assertEqual(layer["duplicate_historical_match_ids"], 0)
        self.assertEqual(layer["duplicate_api_fixture_ids"], 0)
        self.assertEqual(layer["player_level_international_status"], "UNVERIFIED")
        self.assertFalse(layer["operational_betting_authority"])
        self.assertNotIn(
            "PBK14_INTERNATIONAL_WINDOW_MARKET_JOIN_NOT_MATERIALIZED",
            report["gaps"],
        )
        self.assertNotIn(
            "PBK14_INTERNATIONAL_WINDOW_MARKET_JOIN_INVALID",
            report["gaps"],
        )

    def test_missing_materialization_is_explicit(self):
        report = readiness.build_report(self.ops, archive_dir="")
        self.assertIn(
            "PBK14_INTERNATIONAL_WINDOW_MARKET_JOIN_NOT_MATERIALIZED",
            report["gaps"],
        )

    def test_player_level_promotion_is_fail_closed(self):
        self.materialize(player_status="CONFIRMED")
        report = readiness.build_report(self.ops, archive_dir="")
        self.assertIn(
            "PBK14_INTERNATIONAL_WINDOW_MARKET_JOIN_INVALID",
            report["gaps"],
        )

    def test_authority_leak_is_fail_closed(self):
        self.materialize(authority=True)
        report = readiness.build_report(self.ops, archive_dir="")
        self.assertIn(
            "PBK14_INTERNATIONAL_WINDOW_MARKET_JOIN_INVALID",
            report["gaps"],
        )


if __name__ == "__main__":
    unittest.main()
