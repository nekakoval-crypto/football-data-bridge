from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stage80_archive_manifest as manifest
import stage80_archive_readiness as readiness


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class Stage80Stage81ReadinessTests(unittest.TestCase):

    def test_manifest_declares_stage81_queue_and_team_stats(self):
        ids = {
            item["dataset_id"]
            for item in manifest.DATASETS
        }

        self.assertIn("stage81_team_stats_backlog", ids)
        self.assertIn("team_match_statistics", ids)

    def test_readiness_reports_team_stats_and_backlog(self):
        with tempfile.TemporaryDirectory() as temp:
            ops = Path(temp)

            write_csv(
                ops / "current_round_fixtures.csv",
                [
                    "fixture_id",
                    "kickoff_utc",
                    "home_team",
                    "away_team",
                    "source_status",
                    "status",
                    "league_name",
                ],
                [
                    {
                        "fixture_id": "100",
                        "kickoff_utc": "2026-09-17T09:00:00Z",
                        "home_team": "Home FC",
                        "away_team": "Away FC",
                        "source_status": "FT",
                        "status": "finished",
                        "league_name": "Premier League",
                    },
                    {
                        "fixture_id": "200",
                        "kickoff_utc": "2026-09-17T10:00:00Z",
                        "home_team": "Third FC",
                        "away_team": "Fourth FC",
                        "source_status": "FT",
                        "status": "finished",
                        "league_name": "Premier League",
                    },
                ],
            )

            write_csv(
                ops / "team_match_statistics.csv",
                [
                    "fixture_id",
                    "team_id",
                    "side",
                    "observed_at_utc",
                    "kickoff_utc",
                ],
                [
                    {
                        "fixture_id": "100",
                        "team_id": "10",
                        "side": "HOME",
                        "observed_at_utc": "2026-09-17T12:00:00Z",
                        "kickoff_utc": "2026-09-17T09:00:00Z",
                    },
                    {
                        "fixture_id": "100",
                        "team_id": "20",
                        "side": "AWAY",
                        "observed_at_utc": "2026-09-17T12:00:00Z",
                        "kickoff_utc": "2026-09-17T09:00:00Z",
                    },
                ],
            )

            write_csv(
                ops / "stage81_team_stats_backlog.csv",
                [
                    "fixture_id",
                    "first_queued_at_utc",
                    "last_seen_at_utc",
                    "kickoff_utc",
                    "backlog_status",
                ],
                [
                    {
                        "fixture_id": "100",
                        "first_queued_at_utc": "2026-09-17T11:00:00Z",
                        "last_seen_at_utc": "2026-09-17T12:00:00Z",
                        "kickoff_utc": "2026-09-17T09:00:00Z",
                        "backlog_status": "CAPTURED",
                    },
                    {
                        "fixture_id": "200",
                        "first_queued_at_utc": "2026-09-17T11:00:00Z",
                        "last_seen_at_utc": "2026-09-17T12:00:00Z",
                        "kickoff_utc": "2026-09-17T10:00:00Z",
                        "backlog_status": "PENDING",
                    },
                ],
            )

            report = readiness.build_report(ops=ops)

            self.assertEqual(
                report["team_statistics"]["complete_fixture_count"],
                1,
            )
            self.assertEqual(
                report["team_statistics"][
                    "finished_current_inventory_with_team_stats"
                ],
                1,
            )
            self.assertEqual(
                report["team_statistics"][
                    "finished_current_inventory_team_stats_coverage_pct"
                ],
                50.0,
            )

            self.assertEqual(
                report["stage81_backlog"]["pending_fixtures"],
                1,
            )
            self.assertEqual(
                report["stage81_backlog"]["captured_fixtures"],
                1,
            )

            self.assertIn(
                "TEAM_STATS_BACKLOG_PENDING",
                report["gaps"],
            )
            self.assertIn(
                "TEAM_STATS_PARTIAL_FINISHED_FIXTURE_COVERAGE",
                report["gaps"],
            )


if __name__ == "__main__":
    unittest.main()
