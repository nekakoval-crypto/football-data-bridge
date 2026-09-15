import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage80_roster_history_archive as s80


class Stage80RosterHistoryTests(unittest.TestCase):
    def row(self, captured, player_id="10", name="Player A", number="7"):
        return {
            "team_id": "541",
            "team_name": "Real Madrid",
            "captured_at_utc": captured,
            "player_id": player_id,
            "player_name": name,
            "age": "25",
            "number": number,
            "position": "Attacker",
            "photo_url": "https://example.invalid/p.png",
            "source": "api-football:/players/squads",
        }

    def test_new_snapshot_is_appended_without_replacing_old_snapshot(self):
        old = [self.row("2026-09-01T10:00:00Z")]
        current = [self.row("2026-09-15T14:00:00Z")]
        result = s80.append_snapshots(old, current)
        self.assertEqual(result["added_rows"], 1)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(s80.snapshot_count(result["rows"]), 2)
        captures = {row["captured_at_utc"] for row in result["rows"]}
        self.assertEqual(captures, {"2026-09-01T10:00:00Z", "2026-09-15T14:00:00Z"})

    def test_same_snapshot_rerun_is_idempotent(self):
        row = self.row("2026-09-15T14:00:00Z")
        first = s80.append_snapshots([], [row])
        second = s80.append_snapshots(first["rows"], [row])
        self.assertEqual(first["added_rows"], 1)
        self.assertEqual(second["added_rows"], 0)
        self.assertEqual(second["duplicate_current_rows"], 1)
        self.assertEqual(second["rows"], first["rows"])

    def test_existing_historical_observation_wins_on_duplicate_drift(self):
        existing = [self.row("2026-09-15T14:00:00Z", number="7")]
        drifted = [self.row("2026-09-15T14:00:00Z", number="9")]
        result = s80.append_snapshots(existing, drifted)
        self.assertEqual(result["added_rows"], 0)
        self.assertEqual(result["rows"][0]["number"], "7")

    def test_multiple_players_belong_to_same_team_snapshot(self):
        current = [
            self.row("2026-09-15T14:00:00Z", player_id="10", name="A"),
            self.row("2026-09-15T14:00:00Z", player_id="11", name="B"),
        ]
        result = s80.append_snapshots([], current)
        self.assertEqual(result["added_rows"], 2)
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(s80.snapshot_count(result["rows"]), 1)

    def test_missing_capture_or_identity_is_not_archived(self):
        current = [
            self.row(""),
            {**self.row("2026-09-15T14:00:00Z"), "player_id": ""},
        ]
        result = s80.append_snapshots([], current)
        self.assertEqual(result["added_rows"], 0)
        self.assertEqual(result["invalid_current_rows"], 2)
        self.assertEqual(result["rows"], [])

    def test_archive_version_is_explicit(self):
        result = s80.append_snapshots([], [self.row("2026-09-15T14:00:00Z")])
        self.assertEqual(result["rows"][0]["archive_version"], s80.ARCHIVE_VERSION)


if __name__ == "__main__":
    unittest.main()
