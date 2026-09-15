import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage80_archive_readiness as s80


class Stage80Stage77BacklogReadinessTests(unittest.TestCase):
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

    def test_missing_backlog_is_explicit_first_run_gap(self):
        report = s80.build_report(self.ops, archive_dir="")
        backlog = report["stage77_backlog"]
        self.assertFalse(backlog["present"])
        self.assertEqual(backlog["total_fixtures"], 0)
        self.assertIn("STAGE77_BACKLOG_WAITING_FIRST_OPERATIONAL_RUN", report["gaps"])
        self.assertEqual(report["provider_calls"], 0)

    def test_pending_and_captured_backlog_are_counted_without_inference(self):
        self.write_csv(
            "stage77_player_stats_backlog.csv",
            ["fixture_id", "first_queued_at_utc", "backlog_status"],
            [
                {"fixture_id": "10", "first_queued_at_utc": "2026-09-14T10:00:00Z", "backlog_status": "PENDING"},
                {"fixture_id": "11", "first_queued_at_utc": "2026-09-15T10:00:00Z", "backlog_status": "CAPTURED"},
            ],
        )
        self.write_csv(
            "player_stats_snapshots.csv",
            ["fixture_id", "player_id"],
            [{"fixture_id": "11", "player_id": "100"}],
        )
        self.write_csv(
            "player_grade_snapshots.csv",
            ["fixture_id", "player_id"],
            [{"fixture_id": "11", "player_id": "100"}],
        )
        report = s80.build_report(self.ops, archive_dir="")
        backlog = report["stage77_backlog"]
        self.assertTrue(backlog["present"])
        self.assertEqual(backlog["total_fixtures"], 2)
        self.assertEqual(backlog["pending_fixtures"], 1)
        self.assertEqual(backlog["captured_fixtures"], 1)
        self.assertEqual(backlog["captured_without_complete_ledgers"], 0)
        self.assertEqual(backlog["oldest_pending_first_queued_at_utc"], "2026-09-14T10:00:00Z")
        self.assertIn("PLAYER_STATS_BACKLOG_PENDING", report["gaps"])
        self.assertNotIn("STAGE77_BACKLOG_CAPTURED_LEDGER_MISMATCH", report["gaps"])

    def test_captured_backlog_requires_both_stats_and_grade_ledgers(self):
        self.write_csv(
            "stage77_player_stats_backlog.csv",
            ["fixture_id", "first_queued_at_utc", "backlog_status"],
            [{"fixture_id": "12", "first_queued_at_utc": "2026-09-15T10:00:00Z", "backlog_status": "CAPTURED"}],
        )
        self.write_csv(
            "player_stats_snapshots.csv",
            ["fixture_id", "player_id"],
            [{"fixture_id": "12", "player_id": "100"}],
        )
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["stage77_backlog"]["captured_without_complete_ledgers"], 1)
        self.assertIn("STAGE77_BACKLOG_CAPTURED_LEDGER_MISMATCH", report["gaps"])


if __name__ == "__main__":
    unittest.main()
