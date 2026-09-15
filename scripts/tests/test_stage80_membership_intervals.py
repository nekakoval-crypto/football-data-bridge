import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage80_membership_intervals as s80


class Stage80MembershipIntervalTests(unittest.TestCase):
    def row(self, captured, player_id="10", team_id="541", player_name="Player A"):
        return {
            "team_id": team_id,
            "team_name": "Team " + team_id,
            "captured_at_utc": captured,
            "player_id": player_id,
            "player_name": player_name,
            "position": "Attacker",
        }

    def test_player_present_in_all_snapshots_has_open_interval(self):
        rows = [
            self.row("2026-09-01T10:00:00Z"),
            self.row("2026-09-08T10:00:00Z"),
            self.row("2026-09-15T10:00:00Z"),
        ]
        result = s80.build_intervals(rows)
        self.assertEqual(len(result["rows"]), 1)
        item = result["rows"][0]
        self.assertEqual(item["interval_status"], "OPEN_LATEST")
        self.assertEqual(item["first_seen_at_utc"], "2026-09-01T10:00:00Z")
        self.assertEqual(item["last_seen_at_utc"], "2026-09-15T10:00:00Z")
        self.assertEqual(item["observed_snapshot_count"], "3")
        self.assertEqual(item["current_in_latest_snapshot"], "true")

    def test_observed_absence_closes_interval_without_transfer_claim(self):
        rows = [
            self.row("2026-09-01T10:00:00Z", "10"),
            self.row("2026-09-01T10:00:00Z", "11"),
            self.row("2026-09-08T10:00:00Z", "11"),
        ]
        result = s80.build_intervals(rows)
        player = next(item for item in result["rows"] if item["player_id"] == "10")
        self.assertEqual(player["interval_status"], "CLOSED_BY_OBSERVED_ABSENCE")
        self.assertEqual(player["next_absent_at_utc"], "2026-09-08T10:00:00Z")
        self.assertIn("NOT_CONFIRMED_TRANSFER_DATE", player["evidence_semantics"])

    def test_prior_absence_is_recorded_when_player_first_appears_later(self):
        rows = [
            self.row("2026-09-01T10:00:00Z", "11"),
            self.row("2026-09-08T10:00:00Z", "11"),
            self.row("2026-09-08T10:00:00Z", "10"),
        ]
        result = s80.build_intervals(rows)
        player = next(item for item in result["rows"] if item["player_id"] == "10")
        self.assertEqual(player["prior_absent_at_utc"], "2026-09-01T10:00:00Z")
        self.assertEqual(player["first_seen_at_utc"], "2026-09-08T10:00:00Z")
        self.assertEqual(player["interval_status"], "OPEN_LATEST")

    def test_leave_and_return_creates_two_observed_intervals(self):
        rows = [
            self.row("2026-09-01T10:00:00Z", "10"),
            self.row("2026-09-01T10:00:00Z", "11"),
            self.row("2026-09-08T10:00:00Z", "11"),
            self.row("2026-09-15T10:00:00Z", "10"),
            self.row("2026-09-15T10:00:00Z", "11"),
        ]
        result = s80.build_intervals(rows)
        intervals = [item for item in result["rows"] if item["player_id"] == "10"]
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0]["interval_status"], "CLOSED_BY_OBSERVED_ABSENCE")
        self.assertEqual(intervals[1]["interval_status"], "OPEN_LATEST")
        self.assertEqual(intervals[0]["interval_index"], "1")
        self.assertEqual(intervals[1]["interval_index"], "2")

    def test_same_player_on_different_teams_is_separate(self):
        rows = [
            self.row("2026-09-01T10:00:00Z", "10", team_id="541"),
            self.row("2026-09-01T10:00:00Z", "10", team_id="529"),
        ]
        result = s80.build_intervals(rows)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual({item["team_id"] for item in result["rows"]}, {"541", "529"})

    def test_duplicate_player_inside_snapshot_is_collapsed(self):
        row = self.row("2026-09-01T10:00:00Z")
        result = s80.build_intervals([row, dict(row)])
        self.assertEqual(result["duplicate_snapshot_players"], 1)
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["observed_snapshot_count"], "1")

    def test_invalid_history_rows_are_excluded(self):
        result = s80.build_intervals([
            self.row(""),
            {**self.row("2026-09-01T10:00:00Z"), "player_id": ""},
        ])
        self.assertEqual(result["invalid_history_rows"], 2)
        self.assertEqual(result["rows"], [])

    def test_interval_id_is_deterministic(self):
        rows = [self.row("2026-09-01T10:00:00Z")]
        a = s80.build_intervals(rows)["rows"][0]["interval_id"]
        b = s80.build_intervals(rows)["rows"][0]["interval_id"]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
