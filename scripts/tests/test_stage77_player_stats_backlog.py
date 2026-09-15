import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage77_player_stats_capture as stage77

NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


def fixture(fid="100", status="finished", source="FT", kickoff="2026-09-15T09:00:00Z"):
    return {
        "fixture_id": fid,
        "provider_league_id": "135",
        "league_name": "Serie A",
        "season": "2026",
        "round": "3",
        "kickoff_utc": kickoff,
        "home_team": "Alpha",
        "away_team": "Beta",
        "status": status,
        "source_status": source,
    }


class Stage77BacklogTests(unittest.TestCase):
    def test_terminal_fixture_is_queued_before_any_provider_capture(self):
        result = stage77.sync_backlog([], [fixture()], [], [], NOW)
        self.assertEqual(result["new_rows"], 1)
        self.assertEqual(result["pending"], 1)
        self.assertEqual(result["captured"], 0)
        row = result["rows"][0]
        self.assertEqual(row["fixture_id"], "100")
        self.assertEqual(row["backlog_status"], "PENDING")
        self.assertEqual(row["source_status"], "FT")
        self.assertEqual(row["first_queued_at_utc"], stage77.iso(NOW))
        self.assertEqual(row["queue_source"], "current_round_terminal_fixture")

    def test_deferred_fixture_survives_after_round_inventory_rotates_away(self):
        first = stage77.sync_backlog([], [fixture()], [], [], NOW)
        later = NOW + timedelta(days=2)
        second = stage77.sync_backlog(first["rows"], [], [], [], later)
        self.assertEqual(second["pending"], 1)
        candidates = stage77.candidate_fixtures(second["rows"], set(), later, 10)
        self.assertEqual([row["fixture_id"] for row in candidates], ["100"])

    def test_live_future_and_nonterminal_fixtures_are_not_queued(self):
        rows = [
            fixture("101", status="live", source="2H"),
            fixture("102", status="scheduled", source="NS"),
            fixture("103", status="finished", source="FT", kickoff="2026-09-15T15:00:00Z"),
        ]
        result = stage77.sync_backlog([], rows, [], [], NOW)
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["terminal_seen"], 0)

    def test_completed_ledgers_mark_queue_captured_with_actual_observed_time(self):
        first = stage77.sync_backlog([], [fixture()], [], [], NOW)
        observed = "2026-09-15T12:30:00Z"
        stats = [{"fixture_id": "100", "team_id": "10", "player_id": "7", "observed_at_utc": observed}]
        grades = [{"fixture_id": "100", "team_id": "10", "player_id": "7", "observed_at_utc": observed}]
        second = stage77.sync_backlog(first["rows"], [], stats, grades, NOW + timedelta(hours=1))
        self.assertEqual(second["captured"], 1)
        self.assertEqual(second["pending"], 0)
        self.assertEqual(second["rows"][0]["backlog_status"], "CAPTURED")
        self.assertEqual(second["rows"][0]["captured_at_utc"], observed)

    def test_stats_without_grade_do_not_false_mark_captured(self):
        first = stage77.sync_backlog([], [fixture()], [], [], NOW)
        stats = [{"fixture_id": "100", "team_id": "10", "player_id": "7", "observed_at_utc": "2026-09-15T12:30:00Z"}]
        second = stage77.sync_backlog(first["rows"], [], stats, [], NOW + timedelta(hours=1))
        self.assertEqual(second["pending"], 1)
        self.assertEqual(second["captured"], 0)
        self.assertEqual(second["rows"][0]["backlog_status"], "PENDING")

    def test_repeat_observation_preserves_first_queue_time_and_updates_last_seen(self):
        first = stage77.sync_backlog([], [fixture()], [], [], NOW)
        later = NOW + timedelta(hours=3)
        second = stage77.sync_backlog(first["rows"], [fixture()], [], [], later)
        row = second["rows"][0]
        self.assertEqual(row["first_queued_at_utc"], stage77.iso(NOW))
        self.assertEqual(row["last_seen_at_utc"], stage77.iso(later))
        self.assertEqual(second["new_rows"], 0)
        self.assertEqual(len(second["rows"]), 1)

    def test_duplicate_fixture_rows_do_not_duplicate_queue_identity(self):
        result = stage77.sync_backlog([], [fixture(), fixture()], [], [], NOW)
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["new_rows"], 1)
        self.assertEqual(result["terminal_seen"], 2)


if __name__ == "__main__":
    unittest.main()
