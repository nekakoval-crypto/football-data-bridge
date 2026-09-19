import csv
import tempfile
import unittest
from pathlib import Path

import scripts.stage80_archive_manifest as manifest


class Stage80ArchiveManifestTests(unittest.TestCase):
    def write_csv(self, root, name, fields, rows=None):
        path = Path(root) / name
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in rows or []:
                writer.writerow(row)
        return path

    def test_missing_declared_files_are_pending_not_false_attention(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = manifest.build_manifest(Path(tmp), raw_archive_dir="")
        self.assertEqual(report["status"], "OK")
        self.assertGreater(report["summary"]["pending_materializations_or_storage"], 0)
        fixture = next(x for x in report["datasets"] if x["dataset_id"] == "fixture_history_snapshots")
        self.assertEqual(fixture["contract_status"], "PENDING_MATERIALIZATION")

    def test_materialized_good_fixture_history_passes_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_csv(tmp, "fixture_history_snapshots.csv", [
                "fixture_id", "observed_at_utc", "kickoff_utc", "status"
            ], [{"fixture_id": "10", "observed_at_utc": "2026-09-15T10:00:00Z", "kickoff_utc": "2026-09-15T12:00:00Z", "status": "scheduled"}])
            report = manifest.build_manifest(Path(tmp), raw_archive_dir="")
        fixture = next(x for x in report["datasets"] if x["dataset_id"] == "fixture_history_snapshots")
        self.assertEqual(fixture["contract_status"], "OK")
        self.assertEqual(fixture["row_count"], 1)
        self.assertEqual(fixture["identity_key_text"], "fixture_id+observed_at_utc")

    def test_materialized_contract_drift_is_attention(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_csv(tmp, "team_roster_history.csv", ["team_id", "player_id", "player_name"])
            report = manifest.build_manifest(Path(tmp), raw_archive_dir="")
        roster = next(x for x in report["datasets"] if x["dataset_id"] == "team_roster_history")
        self.assertEqual(report["status"], "ATTENTION")
        self.assertEqual(roster["contract_status"], "ATTENTION")
        self.assertIn("captured_at_utc", roster["missing_required_fields"])

    def test_materialized_transfer_history_requires_identity_and_effective_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_csv(
                tmp,
                "historical_transfer_events.csv",
                ["transfer_event_id", "ingested_at_utc", "transfer_date", "pbk_player_id", "transfermarkt_player_id"],
                [{
                    "transfer_event_id": "evt-1",
                    "ingested_at_utc": "2026-09-18T13:00:00Z",
                    "transfer_date": "2024-07-01",
                    "pbk_player_id": "11",
                    "transfermarkt_player_id": "900",
                }],
            )
            report = manifest.build_manifest(Path(tmp), raw_archive_dir="")
        transfer = next(x for x in report["datasets"] if x["dataset_id"] == "historical_transfer_events")
        self.assertEqual(transfer["contract_status"], "OK")
        self.assertEqual(transfer["identity_key_text"], "transfer_event_id")
        self.assertEqual(transfer["effective_time_fields_text"], "transfer_date")

    def test_statsbomb_player_xg_xa_manifest_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_csv(
                tmp,
                "statsbomb_player_xg_xa.csv",
                ["record_id", "match_date", "statsbomb_match_id", "statsbomb_player_id", "statsbomb_team_id"],
                [{
                    "record_id": "r1",
                    "match_date": "2024-06-18",
                    "statsbomb_match_id": "100",
                    "statsbomb_player_id": "10",
                    "statsbomb_team_id": "1",
                }],
            )
            report = manifest.build_manifest(Path(tmp), raw_archive_dir="")
        item = next(x for x in report["datasets"] if x["dataset_id"] == "statsbomb_player_xg_xa")
        self.assertEqual(item["contract_status"], "OK")
        self.assertEqual(item["identity_key_text"], "record_id")
        self.assertEqual(item["effective_time_fields_text"], "match_date")
        self.assertEqual(item["role"], "RESEARCH_ENRICHMENT")

    def test_stage92_mapping_and_mapped_xg_xa_manifest_contracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_csv(
                tmp,
                "statsbomb_pbk_player_mapping_candidates.csv",
                ["statsbomb_player_id", "match_status", "pbk_player_id"],
                [{
                    "statsbomb_player_id": "10",
                    "match_status": "AUTO_MATCH",
                    "pbk_player_id": "11",
                }],
            )
            self.write_csv(
                tmp,
                "pbk_player_xg_xa_research.csv",
                ["pbk_player_id", "statsbomb_record_id", "match_date", "xg_total", "xa"],
                [{
                    "pbk_player_id": "11",
                    "statsbomb_record_id": "r1",
                    "match_date": "2024-06-18",
                    "xg_total": "0.5",
                    "xa": "0.2",
                }],
            )
            report = manifest.build_manifest(Path(tmp), raw_archive_dir="")
        mapping = next(x for x in report["datasets"] if x["dataset_id"] == "statsbomb_pbk_player_mapping_candidates")
        mapped = next(x for x in report["datasets"] if x["dataset_id"] == "pbk_player_xg_xa_research")
        self.assertEqual(mapping["contract_status"], "OK")
        self.assertEqual(mapping["identity_key_text"], "statsbomb_player_id")
        self.assertEqual(mapped["contract_status"], "OK")
        self.assertEqual(mapped["identity_key_text"], "pbk_player_id+statsbomb_record_id")
        self.assertEqual(mapped["effective_time_fields_text"], "match_date")

    def test_player_profile_manifest_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_csv(
                tmp,
                "player_profile_evidence.csv",
                [
                    "team_id", "season", "player_id", "captured_at_utc",
                    "firstname", "lastname", "birth_date", "source",
                ],
                [{
                    "team_id": "10",
                    "season": "2026",
                    "player_id": "11",
                    "captured_at_utc": "2026-09-18T17:34:38Z",
                    "firstname": "Manuel",
                    "lastname": "Akanji",
                    "birth_date": "1995-07-19",
                    "source": "api-football:/players?team&season",
                }],
            )
            report = manifest.build_manifest(Path(tmp), raw_archive_dir="")
        profile = next(
            x for x in report["datasets"]
            if x["dataset_id"] == "player_profile_evidence"
        )
        self.assertEqual(profile["contract_status"], "OK")
        self.assertEqual(profile["identity_key_text"], "team_id+season+player_id")
        self.assertEqual(profile["effective_time_fields_text"], "season")
        self.assertEqual(profile["role"], "IDENTITY_ENRICHMENT_EVIDENCE")

    def test_player_profile_residual_state_manifest_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_csv(
                tmp,
                "player_profile_residual_state.csv",
                [
                    "season", "player_id", "team_id", "team_name", "status",
                    "attempts", "last_attempt_at_utc", "last_error",
                ],
                [{
                    "season": "2026",
                    "player_id": "11",
                    "team_id": "10",
                    "team_name": "Alpha",
                    "status": "EMPTY",
                    "attempts": "1",
                    "last_attempt_at_utc": "2026-09-18T18:00:00Z",
                    "last_error": "",
                }],
            )
            report = manifest.build_manifest(Path(tmp), raw_archive_dir="")
        residual = next(
            x for x in report["datasets"]
            if x["dataset_id"] == "player_profile_residual_state"
        )
        self.assertEqual(residual["contract_status"], "OK")
        self.assertEqual(residual["identity_key_text"], "season+player_id")
        self.assertEqual(residual["role"], "OPERATIONAL_RETRY_LEDGER")

    def test_transfer_identity_manifest_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_csv(
                tmp,
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
            report = manifest.build_manifest(Path(tmp), raw_archive_dir="")
        identity = next(
            x for x in report["datasets"]
            if x["dataset_id"] == "pbk_transfermarkt_player_identity"
        )
        self.assertEqual(identity["contract_status"], "OK")
        self.assertEqual(
            identity["identity_key_text"],
            "pbk_player_id+transfermarkt_player_id",
        )
        self.assertEqual(identity["role"], "VERIFIED_IDENTITY_BRIDGE")

    def test_pbk14_market_bridge_manifest_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_csv(
                tmp,
                "pbk14_football_data_fixture_bridge.csv",
                ["historical_match_id", "date_iso", "mapping_status", "api_fixture_id"],
                [{
                    "historical_match_id": "hist-1",
                    "date_iso": "2024-08-10",
                    "mapping_status": "AUTO",
                    "api_fixture_id": "9001",
                }],
            )
            report = manifest.build_manifest(Path(tmp), raw_archive_dir="")
        bridge = next(
            x for x in report["datasets"]
            if x["dataset_id"] == "pbk14_football_data_fixture_bridge"
        )
        self.assertEqual(bridge["contract_status"], "OK")
        self.assertEqual(bridge["identity_key_text"], "historical_match_id")
        self.assertEqual(bridge["effective_time_fields_text"], "date_iso")
        self.assertEqual(bridge["role"], "RESEARCH_IDENTITY_MAPPING")

    def test_raw_archive_does_not_expose_real_storage_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = manifest.build_manifest(Path(tmp), raw_archive_dir="/secret/server/archive")
        raw = next(x for x in report["datasets"] if x["dataset_id"] == "raw_api_football_payloads")
        self.assertTrue(raw["present"])
        self.assertEqual(raw["path"], "EXTERNAL_DURABLE_STORAGE")
        self.assertNotIn("/secret/server/archive", str(report))

    def test_verified_s3_storage_is_manifest_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "stage80_raw_archive_storage_last_run.json").write_text(
                '{"backend":"S3","status":"READY","readback_match":true,"durable":true,"run_at_utc":"2026-09-18T12:30:00Z"}',
                encoding="utf-8",
            )
            report = manifest.build_manifest(root, raw_archive_dir="")
        raw = next(x for x in report["datasets"] if x["dataset_id"] == "raw_api_football_payloads")
        self.assertTrue(raw["present"])
        self.assertEqual(raw["storage_backend"], "S3")
        self.assertEqual(raw["contract_status"], "CONFIGURED")


    def test_write_outputs_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = manifest.build_manifest(root, raw_archive_dir="")
            manifest.write_outputs(report, root)
            self.assertTrue((root / "stage80_archive_manifest.json").exists())
            self.assertTrue((root / "stage80_archive_manifest.csv").exists())


if __name__ == "__main__":
    unittest.main()
