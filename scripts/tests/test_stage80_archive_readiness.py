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

    def test_team_xg_verified_partial_coverage_is_reported_separately(self):
        self.write_csv(
            "team_match_statistics.csv",
            ["fixture_id", "team_id", "side", "expected_goals"],
            [
                {"fixture_id": "1", "team_id": "10", "side": "HOME", "expected_goals": "1.25"},
                {"fixture_id": "1", "team_id": "11", "side": "AWAY", "expected_goals": "0.80"},
                {"fixture_id": "2", "team_id": "20", "side": "HOME", "expected_goals": ""},
                {"fixture_id": "2", "team_id": "21", "side": "AWAY", "expected_goals": ""},
            ],
        )
        report = s80.build_report(self.ops, archive_dir="")
        advanced = report["advanced_metrics"]
        self.assertEqual(advanced["team_xg_rows"], 2)
        self.assertEqual(advanced["team_xg_complete_fixture_count"], 1)
        self.assertEqual(advanced["team_stats_complete_fixture_count"], 2)
        self.assertEqual(advanced["team_xg_captured_fixture_coverage_pct"], 50.0)
        self.assertNotIn("TEAM_XG_NO_VERIFIED_OBSERVATIONS", report["gaps"])
        self.assertIn("TEAM_XG_PARTIAL_CAPTURED_FIXTURE_COVERAGE", report["gaps"])
        self.assertIn("PLAYER_XG_XA_RESEARCH_SOURCE_NOT_MATERIALIZED", report["gaps"])
        self.assertNotIn("XG_XA_REQUIRE_VERIFIED_SOURCE", report["gaps"])

    def test_team_xg_full_captured_coverage_closes_team_gap_only(self):
        self.write_csv(
            "team_match_statistics.csv",
            ["fixture_id", "team_id", "side", "expected_goals"],
            [
                {"fixture_id": "1", "team_id": "10", "side": "HOME", "expected_goals": "0"},
                {"fixture_id": "1", "team_id": "11", "side": "AWAY", "expected_goals": "2.10"},
            ],
        )
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["advanced_metrics"]["team_xg_complete_fixture_count"], 1)
        self.assertEqual(report["advanced_metrics"]["team_xg_captured_fixture_coverage_pct"], 100.0)
        self.assertNotIn("TEAM_XG_NO_VERIFIED_OBSERVATIONS", report["gaps"])
        self.assertNotIn("TEAM_XG_PARTIAL_CAPTURED_FIXTURE_COVERAGE", report["gaps"])
        self.assertIn("PLAYER_XG_XA_RESEARCH_SOURCE_NOT_MATERIALIZED", report["gaps"])

    def test_missing_team_xg_keeps_team_and_player_source_gaps_explicit(self):
        self.write_csv(
            "team_match_statistics.csv",
            ["fixture_id", "team_id", "side", "expected_goals"],
            [
                {"fixture_id": "1", "team_id": "10", "side": "HOME", "expected_goals": ""},
                {"fixture_id": "1", "team_id": "11", "side": "AWAY", "expected_goals": ""},
            ],
        )
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["advanced_metrics"]["team_xg_rows"], 0)
        self.assertIn("TEAM_XG_NO_VERIFIED_OBSERVATIONS", report["gaps"])
        self.assertIn("PLAYER_XG_XA_RESEARCH_SOURCE_NOT_MATERIALIZED", report["gaps"])

    def test_materialized_statsbomb_player_xg_xa_becomes_research_source_not_operational_authority(self):
        self.write_csv(
            "statsbomb_player_xg_xa.csv",
            [
                "record_id", "statsbomb_match_id", "statsbomb_player_id",
                "statsbomb_team_id", "source_event_sha256", "source",
                "xg_source_field", "xa_derivation_method", "research_only",
                "operational_betting_authority", "xg_total", "xa",
            ],
            [{
                "record_id": "r1",
                "statsbomb_match_id": "100",
                "statsbomb_player_id": "10",
                "statsbomb_team_id": "1",
                "source_event_sha256": "abc",
                "source": "StatsBomb Open Data",
                "xg_source_field": "shot.statsbomb_xg",
                "xa_derivation_method": "JOIN_PASS_EVENT_ID_TO_SHOT_KEY_PASS_ID_THEN_ASSIGN_SHOT_XG",
                "research_only": "true",
                "operational_betting_authority": "false",
                "xg_total": "0.5",
                "xa": "0.2",
            }],
        )
        report = s80.build_report(self.ops, archive_dir="")
        advanced = report["advanced_metrics"]
        self.assertEqual(
            advanced["player_xg_xa_source_status"],
            "RESEARCH_SOURCE_MATERIALIZED_MAPPING_NOT_MATERIALIZED",
        )
        self.assertEqual(advanced["player_xg_xa_research_rows"], 1)
        self.assertEqual(advanced["player_xg_xa_research_matches"], 1)
        self.assertEqual(advanced["player_xg_xa_research_unique_players"], 1)
        self.assertFalse(advanced["player_xg_xa_operational_authority"])
        self.assertNotIn("PLAYER_XG_XA_RESEARCH_SOURCE_NOT_MATERIALIZED", report["gaps"])
        self.assertIn("PLAYER_XG_XA_PBK_IDENTITY_MAPPING_NOT_MATERIALIZED", report["gaps"])
        self.assertEqual(
            advanced["player_xg_xa_pbk_identity_mapping"],
            "STAGE92_NOT_MATERIALIZED",
        )

    def test_stage92_auto_high_mapping_materialization_closes_identity_gap(self):
        self.write_csv(
            "statsbomb_player_xg_xa.csv",
            [
                "record_id", "statsbomb_match_id", "statsbomb_player_id",
                "statsbomb_team_id", "source_event_sha256", "source",
                "xg_source_field", "xa_derivation_method", "research_only",
                "operational_betting_authority", "xg_total", "xa",
            ],
            [{
                "record_id": "r1",
                "statsbomb_match_id": "100",
                "statsbomb_player_id": "10",
                "statsbomb_team_id": "1",
                "source_event_sha256": "abc",
                "source": "StatsBomb Open Data",
                "xg_source_field": "shot.statsbomb_xg",
                "xa_derivation_method": "JOIN_PASS_EVENT_ID_TO_SHOT_KEY_PASS_ID_THEN_ASSIGN_SHOT_XG",
                "research_only": "true",
                "operational_betting_authority": "false",
                "xg_total": "0.5",
                "xa": "0.2",
            }],
        )
        self.write_csv(
            "statsbomb_pbk_player_mapping_candidates.csv",
            [
                "statsbomb_player_id", "pbk_player_id", "match_status",
                "match_method", "match_confidence",
                "authoritative_for_player_xg_xa",
            ],
            [{
                "statsbomb_player_id": "10",
                "pbk_player_id": "11",
                "match_status": "AUTO_MATCH",
                "match_method": "EXACT_FULL_NAME_VIA_VERIFIED_TRANSFER",
                "match_confidence": "HIGH",
                "authoritative_for_player_xg_xa": "true",
            }],
        )
        self.write_csv(
            "pbk_player_xg_xa_research.csv",
            [
                "pbk_player_id", "statsbomb_player_id", "statsbomb_match_id",
                "statsbomb_record_id", "source_event_sha256", "mapping_method",
                "mapping_confidence", "research_only",
                "operational_betting_authority", "xg_total", "xa",
            ],
            [{
                "pbk_player_id": "11",
                "statsbomb_player_id": "10",
                "statsbomb_match_id": "100",
                "statsbomb_record_id": "r1",
                "source_event_sha256": "abc",
                "mapping_method": "EXACT_FULL_NAME_VIA_VERIFIED_TRANSFER",
                "mapping_confidence": "HIGH",
                "research_only": "true",
                "operational_betting_authority": "false",
                "xg_total": "0.5",
                "xa": "0.2",
            }],
        )
        report = s80.build_report(self.ops, archive_dir="")
        advanced = report["advanced_metrics"]
        self.assertEqual(
            advanced["player_xg_xa_source_status"],
            "RESEARCH_MAPPED_TO_PBK_RESEARCH_ONLY",
        )
        self.assertEqual(
            advanced["player_xg_xa_pbk_identity_mapping"],
            "AUTO_HIGH_MATERIALIZED",
        )
        self.assertEqual(advanced["player_xg_xa_auto_high_mappings"], 1)
        self.assertEqual(advanced["player_xg_xa_mapped_research_rows"], 1)
        self.assertEqual(advanced["player_xg_xa_mapped_pbk_players"], 1)
        self.assertNotIn("PLAYER_XG_XA_PBK_IDENTITY_MAPPING_NOT_MATERIALIZED", report["gaps"])
        self.assertNotIn("PLAYER_XG_XA_NO_HIGH_CONFIDENCE_PBK_MAPPING", report["gaps"])

    def test_review_only_stage92_mapping_does_not_close_identity_gap(self):
        self.write_csv(
            "statsbomb_player_xg_xa.csv",
            [
                "record_id", "statsbomb_match_id", "statsbomb_player_id",
                "statsbomb_team_id", "source_event_sha256", "source",
                "xg_source_field", "xa_derivation_method", "research_only",
                "operational_betting_authority",
            ],
            [{
                "record_id": "r1",
                "statsbomb_match_id": "100",
                "statsbomb_player_id": "10",
                "statsbomb_team_id": "1",
                "source_event_sha256": "abc",
                "source": "StatsBomb Open Data",
                "xg_source_field": "shot.statsbomb_xg",
                "xa_derivation_method": "JOIN_PASS_EVENT_ID_TO_SHOT_KEY_PASS_ID_THEN_ASSIGN_SHOT_XG",
                "research_only": "true",
                "operational_betting_authority": "false",
            }],
        )
        self.write_csv(
            "statsbomb_pbk_player_mapping_candidates.csv",
            [
                "statsbomb_player_id", "pbk_player_id", "match_status",
                "match_method", "match_confidence",
                "authoritative_for_player_xg_xa",
            ],
            [{
                "statsbomb_player_id": "10",
                "pbk_player_id": "11",
                "match_status": "REVIEW",
                "match_method": "INITIAL_SURNAME_PBK_CANDIDATE",
                "match_confidence": "MEDIUM",
                "authoritative_for_player_xg_xa": "false",
            }],
        )
        self.write_csv(
            "pbk_player_xg_xa_research.csv",
            ["pbk_player_id", "statsbomb_player_id", "statsbomb_match_id",
             "statsbomb_record_id", "source_event_sha256", "mapping_method",
             "mapping_confidence", "research_only", "operational_betting_authority"],
            [],
        )
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(
            report["advanced_metrics"]["player_xg_xa_source_status"],
            "RESEARCH_SOURCE_MATERIALIZED_NO_HIGH_CONFIDENCE_MAPPING",
        )
        self.assertEqual(report["advanced_metrics"]["player_xg_xa_auto_high_mappings"], 0)
        self.assertEqual(report["advanced_metrics"]["player_xg_xa_review_mappings"], 1)
        self.assertIn("PLAYER_XG_XA_NO_HIGH_CONFIDENCE_PBK_MAPPING", report["gaps"])

    def test_invalid_statsbomb_player_xg_xa_fails_closed(self):
        self.write_csv(
            "statsbomb_player_xg_xa.csv",
            [
                "record_id", "statsbomb_match_id", "statsbomb_player_id",
                "statsbomb_team_id", "source_event_sha256", "source",
                "xg_source_field", "xa_derivation_method", "research_only",
                "operational_betting_authority",
            ],
            [{
                "record_id": "",
                "statsbomb_match_id": "100",
                "statsbomb_player_id": "10",
                "statsbomb_team_id": "1",
                "source_event_sha256": "",
                "source": "StatsBomb Open Data",
                "xg_source_field": "shot.statsbomb_xg",
                "xa_derivation_method": "WRONG",
                "research_only": "true",
                "operational_betting_authority": "false",
            }],
        )
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(
            report["advanced_metrics"]["player_xg_xa_source_status"],
            "RESEARCH_SOURCE_EMPTY_OR_INVALID",
        )
        self.assertIn("PLAYER_XG_XA_RESEARCH_SOURCE_INVALID", report["gaps"])
        self.assertIn("PLAYER_XG_XA_RESEARCH_SOURCE_INVALID_ROWS", report["gaps"])

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


    def test_verified_transfer_identity_is_reported_independently_of_transfer_events(self):
        self.write_csv(
            "pbk_transfermarkt_player_identity.csv",
            [
                "pbk_player_id", "transfermarkt_player_id",
                "mapping_method", "mapping_confidence", "match_status",
            ],
            [{
                "pbk_player_id": "11",
                "transfermarkt_player_id": "900",
                "mapping_method": "EXACT_STATS_NAME_CURRENT_CLUB",
                "mapping_confidence": "HIGH",
                "match_status": "AUTO_MATCH",
            }],
        )
        report = s80.build_report(self.ops, archive_dir="")
        identity = report["transfer_identity"]
        self.assertTrue(identity["present"])
        self.assertEqual(identity["valid_rows"], 1)
        self.assertEqual(identity["unique_pbk_players"], 1)
        self.assertNotIn("VERIFIED_TRANSFER_IDENTITY_NOT_MATERIALIZED", report["gaps"])
        self.assertIn("VERIFIED_TRANSFER_EVENTS_NOT_YET_INGESTED", report["gaps"])

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

    def test_stats_name_transfer_method_also_counts_as_verified(self):
        self.write_csv(
            "historical_transfer_events.csv",
            [
                "transfer_event_id", "pbk_player_id", "transfermarkt_player_id",
                "transfer_date", "mapping_method", "mapping_confidence",
            ],
            [{
                "transfer_event_id": "evt-stats",
                "pbk_player_id": "11",
                "transfermarkt_player_id": "900",
                "transfer_date": "2024-07-01",
                "mapping_method": "EXACT_STATS_NAME_CURRENT_CLUB",
                "mapping_confidence": "HIGH",
            }],
        )
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["transfer_history"]["valid_rows"], 1)
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
