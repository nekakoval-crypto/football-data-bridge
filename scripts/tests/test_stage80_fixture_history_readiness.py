import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage80_archive_readiness as s80


class Stage80FixtureHistoryReadinessTests(unittest.TestCase):
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

    def test_missing_history_is_explicit_seed_gap(self):
        report = s80.build_report(self.ops, archive_dir="")
        self.assertFalse(report["fixture_history"]["present"])
        self.assertEqual(report["fixture_history"]["valid_observations"], 0)
        self.assertIn("FIXTURE_HISTORY_WAITING_FIRST_PRODUCTION_SEED", report["gaps"])
        self.assertEqual(report["provider_calls"], 0)

    def test_history_counts_observations_runs_and_finished_fixtures(self):
        self.write_csv(
            "fixture_history_snapshots.csv",
            ["fixture_id", "observed_at_utc", "status", "source_status"],
            [
                {"fixture_id": "10", "observed_at_utc": "2026-09-15T15:17:00Z", "status": "scheduled", "source_status": "NS"},
                {"fixture_id": "10", "observed_at_utc": "2026-09-15T23:17:00Z", "status": "finished", "source_status": "FT"},
                {"fixture_id": "11", "observed_at_utc": "2026-09-15T23:17:00Z", "status": "scheduled", "source_status": "NS"},
            ],
        )
        report = s80.build_report(self.ops, archive_dir="")
        history = report["fixture_history"]
        self.assertTrue(history["present"])
        self.assertEqual(history["rows"], 3)
        self.assertEqual(history["valid_observations"], 3)
        self.assertEqual(history["unique_fixtures"], 2)
        self.assertEqual(history["observation_runs"], 2)
        self.assertEqual(history["finished_fixtures_observed"], 1)
        self.assertEqual(history["invalid_identity_rows"], 0)
        self.assertNotIn("FIXTURE_HISTORY_WAITING_FIRST_PRODUCTION_SEED", report["gaps"])

    def test_invalid_history_identity_is_visible(self):
        self.write_csv(
            "fixture_history_snapshots.csv",
            ["fixture_id", "observed_at_utc", "status", "source_status"],
            [
                {"fixture_id": "10", "observed_at_utc": "", "status": "finished", "source_status": "FT"},
                {"fixture_id": "", "observed_at_utc": "2026-09-15T23:17:00Z", "status": "finished", "source_status": "FT"},
            ],
        )
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["fixture_history"]["invalid_identity_rows"], 2)
        self.assertIn("FIXTURE_HISTORY_INVALID_IDENTITY_ROWS", report["gaps"])


if __name__ == "__main__":
    unittest.main()
