import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import stage80_archive_readiness as readiness


class PBK16InternationalWindowReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_csv(self, name, fields, rows):
        with (self.ops / name).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def write_json(self, name, payload):
        (self.ops / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def materialize(self, authority_leak=False):
        source_rows = []
        context_rows = []
        for i in range(16):
            fixture_id = str(1000 + i)
            league_id = str(200 + i)
            source_rows.append({
                "fixture_id": fixture_id,
                "competition_role": "DOMESTIC_LEAGUE",
                "provider_competition_id": league_id,
                "season": "2025",
                "kickoff_utc": "2025-09-12T15:00:00Z",
                "home_team_id": str(3000 + i * 2),
                "away_team_id": str(3001 + i * 2),
                "historical_backfill_only": "true",
                "research_only": "true",
                "operational_betting_authority": "false",
                "creates_signal": "false",
                "probability_mutation": "false",
                "eligibility_mutation": "false",
                "stake_changes": "false",
                "forward_journal_mutation": "false",
            })
            context_rows.append({
                "domestic_fixture_id": fixture_id,
                "provider_league_id": league_id,
                "season": "2025",
                "kickoff_utc": "2025-09-12T15:00:00Z",
                "home_team_id": str(3000 + i * 2),
                "away_team_id": str(3001 + i * 2),
                "player_level_international_status": "UNVERIFIED",
                "final_tournaments_included": "false",
                "non_uefa_only_windows_included": "false",
                "calendar_level_only": "true",
                "as_known_calendar_reference": "true",
                "no_match_result_dependency": "true",
                "no_lookahead": "true",
                "historical_backfill_only": "true",
                "research_only": "true",
                "operational_betting_authority": (
                    "true" if authority_leak and i == 0 else "false"
                ),
                "creates_signal": "false",
                "probability_mutation": "false",
                "eligibility_mutation": "false",
                "stake_changes": "false",
                "forward_journal_mutation": "false",
            })

        self.write_csv(
            "pbk16_all_competition_fixture_history.csv",
            list(source_rows[0]),
            source_rows,
        )
        self.write_csv(
            "pbk16_international_window_context_research.csv",
            list(context_rows[0]),
            context_rows,
        )
        self.write_json(
            "stage80_pbk16_international_window_context_last_run.json",
            {
                "version": "PBK_STAGE80_PBK16_INTERNATIONAL_WINDOW_CONTEXT_V1",
                "status": "OK",
                "source_domestic_rows": 16,
                "output_rows": 16,
                "unique_domestic_fixture_ids": 16,
                "duplicate_domestic_fixture_ids": 0,
                "invalid_domestic_rows": 0,
                "domestic_anchor_league_ids": 16,
                "calendar_windows": 39,
                "calendar_sources": 5,
                "within_72h_before_rows": 2,
                "within_96h_before_rows": 3,
                "within_72h_after_rows": 4,
                "within_96h_after_rows": 5,
                "either_first_domestic_after_window_rows": 6,
                "player_level_international_status": "UNVERIFIED",
                "player_level_callup_inference": False,
                "player_level_travel_inference": False,
                "player_level_appearance_inference": False,
                "final_tournaments_included": False,
                "non_uefa_only_windows_included": False,
                "calendar_level_only": True,
                "as_known_calendar_reference": True,
                "no_match_result_dependency": True,
                "no_lookahead": True,
                "provider_calls": 0,
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

    def test_complete_materialization_closes_international_window_gaps(self):
        self.materialize()
        report = readiness.build_report(self.ops, archive_dir="")
        layer = report["pbk16_international_window_context"]
        self.assertTrue(layer["meta_valid"])
        self.assertEqual(layer["valid_rows"], 16)
        self.assertEqual(layer["invalid_rows"], 0)
        self.assertEqual(layer["duplicate_domestic_fixture_ids"], 0)
        self.assertEqual(layer["calendar_windows"], 39)
        self.assertEqual(layer["player_level_international_status"], "UNVERIFIED")
        self.assertFalse(layer["operational_betting_authority"])
        self.assertNotIn(
            "PBK16_INTERNATIONAL_WINDOW_CONTEXT_NOT_MATERIALIZED",
            report["gaps"],
        )
        self.assertNotIn(
            "PBK16_INTERNATIONAL_WINDOW_CONTEXT_INVALID",
            report["gaps"],
        )

    def test_missing_materialization_is_explicit(self):
        report = readiness.build_report(self.ops, archive_dir="")
        self.assertIn(
            "PBK16_INTERNATIONAL_WINDOW_CONTEXT_NOT_MATERIALIZED",
            report["gaps"],
        )

    def test_authority_leak_invalidates_layer(self):
        self.materialize(authority_leak=True)
        report = readiness.build_report(self.ops, archive_dir="")
        self.assertIn(
            "PBK16_INTERNATIONAL_WINDOW_CONTEXT_INVALID",
            report["gaps"],
        )

    def test_player_level_status_cannot_be_promoted_without_evidence(self):
        self.materialize()
        path = self.ops / "pbk16_international_window_context_research.csv"
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        rows[0]["player_level_international_status"] = "CONFIRMED"
        self.write_csv(path.name, list(rows[0]), rows)

        report = readiness.build_report(self.ops, archive_dir="")
        self.assertIn(
            "PBK16_INTERNATIONAL_WINDOW_CONTEXT_INVALID",
            report["gaps"],
        )


if __name__ == "__main__":
    unittest.main()
