import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_archive_readiness as readiness


class PBK16CompetitionReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_csv(self, name, fields, rows):
        with (self.ops / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def write_json(self, name, payload):
        (self.ops / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def materialize_valid_pbk16(self, unavailable=0, pending=0, errors=0):
        league_ids = [
            39, 140, 135, 78, 61, 218, 144, 119,
            362, 365, 88, 103, 106, 94, 203, 179,
        ]
        catalog = []
        fixtures = []
        state = []
        congestion = []
        for index, league_id in enumerate(league_ids, start=1):
            country = f"Country {index}"
            catalog.append({
                "competition_role": "DOMESTIC_LEAGUE",
                "country": country,
                "slot": "LEAGUE",
                "canonical_name": f"League {index}",
                "provider_league_id": str(league_id),
                "provider_name": f"League {index}",
                "provider_type": "League",
                "requested_seasons": "2025",
                "available_requested_seasons": "2025",
                "missing_requested_seasons": "",
                "required": "true",
                "discovery_status": "RESOLVED",
                "error": "",
            })
            fixtures.append({
                "fixture_id": str(1000 + index),
                "competition_role": "DOMESTIC_LEAGUE",
                "country": country,
                "slot": "LEAGUE",
                "provider_competition_id": str(league_id),
                "competition_name": f"League {index}",
                "provider_competition_type": "League",
                "season": "2025",
                "round": "Round 1",
                "kickoff_utc": "2025-08-10T15:00:00+00:00",
                "status": "FT",
                "home_team_id": str(2000 + index),
                "home_team": f"Home {index}",
                "away_team_id": str(3000 + index),
                "away_team": f"Away {index}",
                "historical_backfill_only": "true",
                "research_only": "true",
                "operational_betting_authority": "false",
                "creates_signal": "false",
                "probability_mutation": "false",
                "eligibility_mutation": "false",
                "stake_changes": "false",
                "forward_journal_mutation": "false",
            })
            state.append({
                "competition_role": "DOMESTIC_LEAGUE",
                "country": country,
                "slot": "LEAGUE",
                "provider_competition_id": str(league_id),
                "competition_name": f"League {index}",
                "season": "2025",
                "provider_season_available": "true",
                "status": "CAPTURED",
            })
            congestion.append({
                "domestic_fixture_id": str(1000 + index),
                "provider_league_id": str(league_id),
                "league_name": f"League {index}",
                "country": country,
                "season": "2025",
                "round": "Round 1",
                "kickoff_utc": "2025-08-10T15:00:00+00:00",
                "status": "FT",
                "home_team_id": str(2000 + index),
                "home_team": f"Home {index}",
                "away_team_id": str(3000 + index),
                "away_team": f"Away {index}",
                "strictly_prior_fixture_evidence_only": "true",
                "future_schedule_used": "false",
                "no_lookahead": "true",
                "historical_backfill_only": "true",
                "research_only": "true",
                "operational_betting_authority": "false",
                "creates_signal": "false",
                "probability_mutation": "false",
                "eligibility_mutation": "false",
                "stake_changes": "false",
                "forward_journal_mutation": "false",
            })

        if unavailable:
            state[0]["status"] = "UNAVAILABLE_PROVIDER_SEASON"
            state[0]["provider_season_available"] = "false"
        if pending:
            state[1]["status"] = "PENDING"
        if errors:
            state[2]["status"] = "ERROR"

        self.write_csv(
            "stage80_pbk16_competition_catalog.csv",
            list(catalog[0].keys()),
            catalog,
        )
        self.write_csv(
            "pbk16_all_competition_fixture_history.csv",
            list(fixtures[0].keys()),
            fixtures,
        )
        self.write_csv(
            "stage80_pbk16_competition_backfill_state.csv",
            list(state[0].keys()),
            state,
        )
        self.write_csv(
            "pbk16_competition_congestion_research.csv",
            list(congestion[0].keys()),
            congestion,
        )
        self.write_json(
            "stage80_pbk16_competition_backfill_last_run.json",
            {
                "version": "PBK_STAGE80_PBK16_ALL_COMPETITION_BACKFILL_V1",
                "status": "PARTIAL_PROVIDER_COVERAGE" if unavailable else "OK",
                "locked_national_leagues": 16,
                "historical_backfill_only": True,
                "research_only": True,
                "operational_betting_authority": False,
                "creates_signal": False,
                "probability_mutation": False,
                "eligibility_mutation": False,
                "stake_changes": False,
                "forward_journal_mutation": False,
            },
        )
        self.write_json(
            "stage80_pbk16_competition_congestion_last_run.json",
            {
                "version": "PBK_STAGE80_PBK16_COMPETITION_CONGESTION_V1",
                "status": "OK",
                "strictly_prior_fixture_evidence_only": True,
                "future_schedule_used": False,
                "no_lookahead": True,
                "projection_provider_calls": 0,
                "historical_backfill_only": True,
                "research_only": True,
                "operational_betting_authority": False,
                "creates_signal": False,
                "probability_mutation": False,
                "eligibility_mutation": False,
                "stake_changes": False,
                "forward_journal_mutation": False,
                "rows_either_prev_nonleague_72h": 0,
                "rows_either_prev_uefa_72h": 0,
                "rows_either_prev_cup_72h": 0,
                "rows_either_previous_nonleague_was_thursday": 0,
            },
        )

    def test_complete_pbk16_materialization_closes_new_layer_gaps(self):
        self.materialize_valid_pbk16()
        report = readiness.build_report(self.ops, archive_dir="")

        history = report["pbk16_competition_history"]
        congestion = report["pbk16_competition_congestion"]
        self.assertTrue(history["meta_valid"])
        self.assertEqual(history["domestic_anchor_league_ids"], 16)
        self.assertEqual(history["required_unresolved_competitions"], 0)
        self.assertEqual(history["captured_fixture_cells"], 16)
        self.assertTrue(congestion["meta_valid"])
        self.assertEqual(congestion["valid_rows"], 16)
        self.assertTrue(congestion["no_lookahead"])
        self.assertFalse(congestion["future_schedule_used"])

        self.assertNotIn("PBK16_COMPETITION_HISTORY_NOT_MATERIALIZED", report["gaps"])
        self.assertNotIn("PBK16_COMPETITION_HISTORY_INVALID", report["gaps"])
        self.assertNotIn("PBK16_DOMESTIC_ANCHOR_LEAGUE_COVERAGE_PARTIAL", report["gaps"])
        self.assertNotIn("PBK16_COMPETITION_CONGESTION_NOT_MATERIALIZED", report["gaps"])
        self.assertNotIn("PBK16_COMPETITION_CONGESTION_INVALID", report["gaps"])

    def test_provider_unavailable_season_is_explicit_partial_coverage_not_invalid(self):
        self.materialize_valid_pbk16(unavailable=1)
        report = readiness.build_report(self.ops, archive_dir="")
        history = report["pbk16_competition_history"]

        self.assertEqual(history["unavailable_provider_season_cells"], 1)
        self.assertIn("PBK16_COMPETITION_PROVIDER_SEASONS_PARTIAL", report["gaps"])
        self.assertNotIn("PBK16_COMPETITION_HISTORY_INVALID", report["gaps"])

    def test_pending_and_error_cells_remain_visible(self):
        self.materialize_valid_pbk16(pending=1, errors=1)
        report = readiness.build_report(self.ops, archive_dir="")
        self.assertIn("PBK16_COMPETITION_BACKFILL_PENDING", report["gaps"])
        self.assertIn("PBK16_COMPETITION_BACKFILL_ERRORS", report["gaps"])

    def test_missing_layer_is_explicit(self):
        report = readiness.build_report(self.ops, archive_dir="")
        self.assertIn("PBK16_COMPETITION_HISTORY_NOT_MATERIALIZED", report["gaps"])
        self.assertIn("PBK16_COMPETITION_CONGESTION_NOT_MATERIALIZED", report["gaps"])


if __name__ == "__main__":
    unittest.main()
