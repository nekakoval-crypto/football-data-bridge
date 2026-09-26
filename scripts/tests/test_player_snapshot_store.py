import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import player_snapshot_store as s


class PlayerSnapshotStoreTests(unittest.TestCase):
    def write_csv(self, path, rows):
        fields = list(rows[0].keys())
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def rows(self):
        return [
            {"fixture_id": "1", "kickoff_utc": "2024-01-01T12:00:00Z", "player_id": "10"},
            {"fixture_id": "2", "kickoff_utc": "2025-01-01T12:00:00Z", "player_id": "20"},
            {"fixture_id": "3", "kickoff_utc": "", "player_id": "30"},
        ]

    def test_reads_legacy_monolith(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "player_grade_snapshots.csv"
            self.write_csv(base, self.rows())
            loaded = s.read_snapshot_rows(base)
            self.assertEqual(len(loaded), 3)

    def test_migration_partitions_and_removes_legacy_blob(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = root / "player_grade_snapshots.csv"
            parts = s.snapshot_parts_dir(base)
            rows = self.rows()
            self.write_csv(base, rows)

            result = s.migrate_legacy_monolith(
                base,
                parts,
                ["fixture_id", "kickoff_utc", "player_id"],
                rows,
            )

            self.assertFalse(base.exists())
            self.assertEqual(result["partitions"], 3)
            self.assertTrue((parts / "2024.csv").exists())
            self.assertTrue((parts / "2025.csv").exists())
            self.assertTrue((parts / "unknown.csv").exists())
            loaded = s.read_snapshot_rows(base, parts)
            self.assertEqual(
                sorted(r["fixture_id"] for r in loaded),
                ["1", "2", "3"],
            )

    def test_rewrite_removes_stale_partition(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base = root / "player_stats_snapshots.csv"
            parts = s.snapshot_parts_dir(base)
            fields = ["fixture_id", "kickoff_utc", "player_id"]
            s.write_partitioned_rows(self.rows(), parts, fields)
            self.assertTrue((parts / "2024.csv").exists())

            s.write_partitioned_rows(
                [self.rows()[1]],
                parts,
                fields,
            )
            self.assertFalse((parts / "2024.csv").exists())
            self.assertTrue((parts / "2025.csv").exists())


if __name__ == "__main__":
    unittest.main()
