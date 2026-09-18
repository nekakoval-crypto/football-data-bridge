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
