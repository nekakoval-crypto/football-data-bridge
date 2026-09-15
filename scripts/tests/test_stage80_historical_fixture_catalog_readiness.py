import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage80_archive_readiness as s80


class HistoricalFixtureCatalogReadinessTests(unittest.TestCase):
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

    def write_history(self):
        self.write_csv(
            "fixture_history_snapshots.csv",
            ["fixture_id", "observed_at_utc", "status", "source_status"],
            [
                {"fixture_id":"10","observed_at_utc":"2026-09-15T10:00:00Z","status":"scheduled","source_status":"NS"},
                {"fixture_id":"10","observed_at_utc":"2026-09-15T20:00:00Z","status":"finished","source_status":"FT"},
                {"fixture_id":"11","observed_at_utc":"2026-09-15T10:00:00Z","status":"scheduled","source_status":"NS"},
            ],
        )

    def write_catalog(self, rows):
        self.write_csv(
            "historical_fixtures.csv",
            ["fixture_id", "terminal_observed", "reschedule_observed", "observation_count"],
            rows,
        )

    def test_complete_catalog_matches_history(self):
        self.write_history()
        self.write_catalog([
            {"fixture_id":"10","terminal_observed":"YES","reschedule_observed":"NO","observation_count":"2"},
            {"fixture_id":"11","terminal_observed":"NO","reschedule_observed":"NO","observation_count":"1"},
        ])
        report = s80.build_report(self.ops, archive_dir="")
        catalog = report["historical_fixture_catalog"]
        self.assertEqual(catalog["history_fixture_coverage_pct"], 100.0)
        self.assertEqual(catalog["missing_history_fixtures"], 0)
        self.assertEqual(catalog["orphan_catalog_fixtures"], 0)
        self.assertEqual(catalog["missing_terminal_evidence"], 0)
        self.assertEqual(catalog["observation_count_total"], 3)
        self.assertNotIn("HISTORICAL_FIXTURE_CATALOG_MISSING_HISTORY_FIXTURES", report["gaps"])
        self.assertNotIn("HISTORICAL_FIXTURE_CATALOG_TERMINAL_EVIDENCE_MISMATCH", report["gaps"])

    def test_missing_fixture_is_named_gap(self):
        self.write_history()
        self.write_catalog([
            {"fixture_id":"10","terminal_observed":"YES","reschedule_observed":"NO","observation_count":"2"},
        ])
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["historical_fixture_catalog"]["missing_history_fixtures"], 1)
        self.assertEqual(report["historical_fixture_catalog"]["history_fixture_coverage_pct"], 50.0)
        self.assertIn("HISTORICAL_FIXTURE_CATALOG_MISSING_HISTORY_FIXTURES", report["gaps"])

    def test_orphan_and_duplicate_catalog_rows_are_visible(self):
        self.write_history()
        self.write_catalog([
            {"fixture_id":"10","terminal_observed":"YES","reschedule_observed":"NO","observation_count":"2"},
            {"fixture_id":"10","terminal_observed":"YES","reschedule_observed":"NO","observation_count":"2"},
            {"fixture_id":"11","terminal_observed":"NO","reschedule_observed":"NO","observation_count":"1"},
            {"fixture_id":"99","terminal_observed":"NO","reschedule_observed":"NO","observation_count":"1"},
        ])
        report = s80.build_report(self.ops, archive_dir="")
        catalog = report["historical_fixture_catalog"]
        self.assertEqual(catalog["duplicate_fixture_ids"], 1)
        self.assertEqual(catalog["orphan_catalog_fixtures"], 1)
        self.assertIn("HISTORICAL_FIXTURE_CATALOG_DUPLICATE_FIXTURE_IDS", report["gaps"])
        self.assertIn("HISTORICAL_FIXTURE_CATALOG_ORPHAN_FIXTURES", report["gaps"])

    def test_terminal_evidence_mismatch_is_named_gap(self):
        self.write_history()
        self.write_catalog([
            {"fixture_id":"10","terminal_observed":"NO","reschedule_observed":"NO","observation_count":"2"},
            {"fixture_id":"11","terminal_observed":"NO","reschedule_observed":"NO","observation_count":"1"},
        ])
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["historical_fixture_catalog"]["missing_terminal_evidence"], 1)
        self.assertIn("HISTORICAL_FIXTURE_CATALOG_TERMINAL_EVIDENCE_MISMATCH", report["gaps"])

    def test_observation_count_mismatch_is_named_gap(self):
        self.write_history()
        self.write_catalog([
            {"fixture_id":"10","terminal_observed":"YES","reschedule_observed":"NO","observation_count":"999"},
            {"fixture_id":"11","terminal_observed":"NO","reschedule_observed":"NO","observation_count":"bad"},
        ])
        report = s80.build_report(self.ops, archive_dir="")
        self.assertEqual(report["historical_fixture_catalog"]["invalid_observation_count_rows"], 1)
        self.assertIn("HISTORICAL_FIXTURE_CATALOG_OBSERVATION_COUNT_MISMATCH", report["gaps"])

    def test_history_without_catalog_is_explicit_build_gap(self):
        self.write_history()
        report = s80.build_report(self.ops, archive_dir="")
        self.assertIn("HISTORICAL_FIXTURE_CATALOG_WAITING_FIRST_BUILD", report["gaps"])
        self.assertEqual(report["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
