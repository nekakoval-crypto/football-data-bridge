import csv
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage71_stage77_backlog_refresh as refresh
import stage77_player_stats_capture as stage77

NOW = datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc)


class Stage71Stage77BacklogRefreshTests(unittest.TestCase):
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

    def terminal_fixture(self):
        return {
            "fixture_id": "100",
            "provider_league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "round": "Regular Season - 4",
            "kickoff_utc": "2026-09-15T14:00:00Z",
            "home_team": "Alpha",
            "away_team": "Beta",
            "status": "finished",
            "source_status": "FT",
        }

    def test_terminal_fixture_is_queued_without_provider_collection(self):
        fixture = self.terminal_fixture()
        self.write_csv("current_round_fixtures.csv", fixture.keys(), [fixture])
        result = refresh.refresh(self.ops, NOW)
        self.assertEqual(result["provider_calls"], 0)
        self.assertEqual(result["terminal_seen"], 1)
        self.assertEqual(result["new_backlog_rows"], 1)
        rows = stage77.read_csv(self.ops / "stage77_player_stats_backlog.csv")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fixture_id"], "100")
        self.assertEqual(rows[0]["backlog_status"], "PENDING")

    def test_queue_survives_current_round_rotation(self):
        fixture = self.terminal_fixture()
        self.write_csv("current_round_fixtures.csv", fixture.keys(), [fixture])
        refresh.refresh(self.ops, NOW)

        future = dict(fixture)
        future.update({
            "fixture_id": "200",
            "kickoff_utc": "2026-09-20T14:00:00Z",
            "status": "scheduled",
            "source_status": "NS",
        })
        self.write_csv("current_round_fixtures.csv", future.keys(), [future])
        result = refresh.refresh(self.ops, NOW)
        rows = stage77.read_csv(self.ops / "stage77_player_stats_backlog.csv")
        self.assertEqual(result["new_backlog_rows"], 0)
        self.assertEqual([row["fixture_id"] for row in rows], ["100"])
        self.assertEqual(rows[0]["backlog_status"], "PENDING")

    def test_existing_queue_reconciles_to_captured_from_both_ledgers(self):
        fixture = self.terminal_fixture()
        self.write_csv("current_round_fixtures.csv", fixture.keys(), [fixture])
        refresh.refresh(self.ops, NOW)
        self.write_csv(
            "player_stats_snapshots.csv",
            ["fixture_id", "player_id", "observed_at_utc"],
            [{"fixture_id": "100", "player_id": "7", "observed_at_utc": "2026-09-15T18:05:00Z"}],
        )
        self.write_csv(
            "player_grade_snapshots.csv",
            ["fixture_id", "player_id", "observed_at_utc"],
            [{"fixture_id": "100", "player_id": "7", "observed_at_utc": "2026-09-15T18:05:00Z"}],
        )
        result = refresh.refresh(self.ops, NOW)
        rows = stage77.read_csv(self.ops / "stage77_player_stats_backlog.csv")
        self.assertEqual(result["captured"], 1)
        self.assertEqual(rows[0]["backlog_status"], "CAPTURED")
        self.assertEqual(rows[0]["captured_at_utc"], "2026-09-15T18:05:00Z")


if __name__ == "__main__":
    unittest.main()
