import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage80_archive_readiness as s80


class Stage80ArchiveReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Path(self.temp.name) / "ops"
        self.ops.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write_csv(self, name, fields, rows):
        path = self.ops / name
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_missing_sources_are_explicit_bootstrap_not_fake_zero_coverage(self):
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["status"], "BOOTSTRAPPING")
        self.assertFalse(report["source_presence"]["roster_history"]["present"])
        self.assertIsNone(report["source_presence"]["roster_history"]["rows"])
        self.assertIsNone(report["fixtures"]["finished_current_inventory_player_stats_coverage_pct"])
        self.assertIn("ROSTER_HISTORY_WAITING_FIRST_CAPTURE", report["gaps"])
        self.assertEqual(report["provider_calls"], 0)

    def test_finished_fixture_player_stats_coverage_is_measured_without_hindsight_claims(self):
        self.write_csv(
            "current_round_fixtures.csv",
            ["fixture_id", "league_name", "status", "source_status"],
            [
                {"fixture_id": "1", "league_name": "Serie A", "status": "finished", "source_status": "FT"},
                {"fixture_id": "2", "league_name": "Serie A", "status": "finished", "source_status": "FT"},
                {"fixture_id": "3", "league_name": "Serie A", "status": "scheduled", "source_status": "NS"},
            ],
        )
        self.write_csv(
            "player_stats_snapshots.csv",
            ["fixture_id", "player_id"],
            [
                {"fixture_id": "1", "player_id": "10"},
                {"fixture_id": "1", "player_id": "11"},
            ],
        )
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["fixtures"]["finished_in_current_inventory"], 2)
        self.assertEqual(report["fixtures"]["finished_current_inventory_with_player_stats"], 1)
        self.assertEqual(report["fixtures"]["finished_current_inventory_player_stats_coverage_pct"], 50.0)
        self.assertEqual(report["fixtures"]["per_league"][0]["player_stats_coverage_pct"], 50.0)
        self.assertIn("PLAYER_STATS_PARTIAL_FINISHED_FIXTURE_COVERAGE", report["gaps"])

    def test_roster_history_and_membership_counts_are_reported(self):
        self.write_csv(
            "team_rosters.csv",
            ["team_id", "player_id"],
            [
                {"team_id": "100", "player_id": "1"},
                {"team_id": "100", "player_id": "2"},
            ],
        )
        self.write_csv(
            "team_roster_history.csv",
            ["team_id", "captured_at_utc", "player_id"],
            [
                {"team_id": "100", "captured_at_utc": "2026-09-01T00:00:00Z", "player_id": "1"},
                {"team_id": "100", "captured_at_utc": "2026-09-01T00:00:00Z", "player_id": "2"},
                {"team_id": "100", "captured_at_utc": "2026-09-08T00:00:00Z", "player_id": "2"},
            ],
        )
        self.write_csv(
            "team_membership_intervals.csv",
            ["team_id", "player_id", "interval_status"],
            [
                {"team_id": "100", "player_id": "1", "interval_status": "CLOSED_BY_OBSERVED_ABSENCE"},
                {"team_id": "100", "player_id": "2", "interval_status": "OPEN_LATEST"},
            ],
        )
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["rosters"]["current_roster_teams"], 1)
        self.assertEqual(report["rosters"]["history_teams"], 1)
        self.assertEqual(report["rosters"]["history_team_snapshots"], 2)
        self.assertEqual(report["rosters"]["membership_intervals"], 2)
        self.assertEqual(report["rosters"]["open_latest_intervals"], 1)
        self.assertEqual(report["rosters"]["closed_by_observed_absence_intervals"], 1)

    def test_context_counts_lineup_and_injury_evidence_but_labels_scope_limit(self):
        self.write_csv(
            "match_context_snapshots.csv",
            ["api_fixture_id", "lineups_available", "injuries_count", "injuries_json"],
            [
                {"api_fixture_id": "1", "lineups_available": "true", "injuries_count": "2", "injuries_json": "[]"},
                {"api_fixture_id": "2", "lineups_available": "0", "injuries_count": "0", "injuries_json": "[]"},
            ],
        )
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["context"]["unique_fixtures"], 2)
        self.assertEqual(report["context"]["fixtures_with_official_lineup_snapshot"], 1)
        self.assertEqual(report["context"]["fixtures_with_injury_evidence"], 1)
        self.assertIn("canonical-signal scoped", report["context"]["coverage_note"])
        self.assertIn("MATCH_CONTEXT_COVERAGE_IS_CANONICAL_SCOPE_ONLY", report["gaps"])

    def test_raw_archive_manifest_is_counted_without_exposing_storage_path(self):
        archive = Path(self.temp.name) / "raw-archive"
        archive.mkdir()
        rows = [
            {"payload_sha256": "aaa", "path": "/fixtures", "payload_bytes": 100},
            {"payload_sha256": "aaa", "path": "/fixtures", "payload_bytes": 100},
            {"payload_sha256": "bbb", "path": "/players/squads", "payload_bytes": 50},
        ]
        with (archive / "manifest.jsonl").open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row) + "\n")
        report = s80.build_report(self.ops, archive_dir=archive)
        raw = report["raw_provider_archive"]
        self.assertTrue(raw["configured"])
        self.assertEqual(raw["status"], "OK")
        self.assertEqual(raw["manifest_observations"], 3)
        self.assertEqual(raw["unique_payloads"], 2)
        self.assertEqual(raw["unique_paths"], 2)
        self.assertEqual(raw["manifest_payload_bytes"], 250)
        self.assertNotIn(str(archive), json.dumps(raw))

    def test_corrupt_raw_manifest_line_is_attention_not_exception(self):
        archive = Path(self.temp.name) / "raw-archive"
        archive.mkdir()
        (archive / "manifest.jsonl").write_text('{"payload_sha256":"aaa","path":"/fixtures"}\n{broken\n', encoding="utf-8")
        raw = s80.raw_archive_inventory(archive)
        self.assertEqual(raw["status"], "ATTENTION")
        self.assertEqual(raw["manifest_observations"], 1)
        self.assertEqual(raw["manifest_invalid_lines"], 1)

    def test_verified_s3_storage_telemetry_closes_durable_storage_gap(self):
        (self.ops / "stage80_raw_archive_storage_last_run.json").write_text(
            json.dumps({
                "backend": "S3",
                "status": "READY",
                "run_at_utc": "2026-09-18T12:30:00Z",
                "readback_match": True,
                "durable": True,
                "bucket": "pbk-api-football-raw",
                "prefix": "api-football-raw",
            }),
            encoding="utf-8",
        )
        report = s80.build_report(self.ops, archive_dir="")
        raw = report["raw_provider_archive"]
        self.assertTrue(raw["configured"])
        self.assertEqual(raw["backend"], "S3")
        self.assertEqual(raw["status"], "OK")
        self.assertTrue(raw["storage_readback_match"])
        self.assertNotIn("RAW_ARCHIVE_DURABLE_STORAGE_NOT_CONFIGURED", report["gaps"])
        self.assertNotIn("RAW_ARCHIVE_STORAGE_NEEDS_ATTENTION", report["gaps"])


    def test_verified_transfer_gap_closes_only_with_valid_durable_evidence(self):
        self.write_csv(
            "historical_transfer_events.csv",
            [
                "transfer_event_id", "pbk_player_id", "transfermarkt_player_id",
                "transfer_date", "mapping_method", "mapping_confidence",
            ],
            [{
                "transfer_event_id": "evt-1",
                "pbk_player_id": "11",
                "transfermarkt_player_id": "900",
                "transfer_date": "2024-07-01",
                "mapping_method": "EXACT_NAME_CURRENT_CLUB",
                "mapping_confidence": "HIGH",
            }],
        )
        report = s80.build_report(self.ops, archive_dir="")
        transfer = report["transfer_history"]
        self.assertTrue(transfer["present"])
        self.assertEqual(transfer["valid_rows"], 1)
        self.assertEqual(transfer["unique_pbk_players"], 1)
        self.assertEqual(transfer["unique_transfermarkt_players"], 1)
        self.assertNotIn("VERIFIED_TRANSFER_EVENTS_NOT_YET_INGESTED", report["gaps"])

    def test_invalid_transfer_dataset_keeps_verified_transfer_gap(self):
        self.write_csv(
            "historical_transfer_events.csv",
            [
                "transfer_event_id", "pbk_player_id", "transfermarkt_player_id",
                "transfer_date", "mapping_method", "mapping_confidence",
            ],
            [{
                "transfer_event_id": "",
                "pbk_player_id": "11",
                "transfermarkt_player_id": "900",
                "transfer_date": "2024-07-01",
                "mapping_method": "EXACT_NAME_UNIQUE",
                "mapping_confidence": "MEDIUM",
            }],
        )
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["transfer_history"]["valid_rows"], 0)
        self.assertEqual(report["transfer_history"]["invalid_identity_rows"], 1)
        self.assertIn("VERIFIED_TRANSFER_EVENTS_NOT_YET_INGESTED", report["gaps"])
        self.assertIn("TRANSFER_HISTORY_INVALID_IDENTITY_ROWS", report["gaps"])

    def test_readiness_never_mutates_strategy_contracts(self):
        report = s80.build_report(self.ops, archive_dir="")
        self.assertFalse(report["creates_signal"])
        self.assertFalse(report["probability_mutation"])
        self.assertFalse(report["eligibility_mutation"])
        self.assertFalse(report["stake_changes"])
        self.assertFalse(report["forward_journal_mutation"])


if __name__ == "__main__":
    unittest.main()
