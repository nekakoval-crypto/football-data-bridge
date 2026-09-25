from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import player_availability_prematch_journal as m


class PrematchAvailabilityJournalTests(unittest.TestCase):
    def snapshot(self):
        return {
            "forward_id": "f1",
            "api_fixture_id": "100",
            "captured_at_utc": "2026-09-25T15:00:00Z",
            "current_kickoff_utc": "2026-09-25T18:00:00Z",
            "snapshot_type": "T3",
            "home_team_id": "10",
            "home_team": "Home",
            "away_team_id": "20",
            "away_team": "Away",
            "injuries_json": json.dumps([
                {
                    "player_id": 7,
                    "player": "Absent One",
                    "team_id": 10,
                    "team": "Home",
                    "type": "Missing Fixture",
                    "reason": "Hamstring",
                }
            ]),
            "lineups_available": "NO",
            "home_start_xi_json": "[]",
            "away_start_xi_json": "[]",
        }

    def test_explicit_injury_becomes_absent(self):
        events, status = m.events_from_snapshot(self.snapshot())
        self.assertEqual(status, "OK")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["state"], "ABSENT")
        self.assertEqual(events[0]["player_id"], "7")
        self.assertEqual(events[0]["prematch_known"], "YES")

    def test_official_xi_players_become_present_only(self):
        snap = self.snapshot()
        snap["snapshot_type"] = "T60"
        snap["lineups_available"] = "YES"
        snap["injuries_json"] = "[]"
        snap["home_start_xi_json"] = json.dumps([
            {"id": i, "name": f"P{i}"} for i in range(1, 12)
        ])
        events, status = m.events_from_snapshot(snap)
        self.assertEqual(status, "OK")
        self.assertEqual(len(events), 11)
        self.assertEqual({row["state"] for row in events}, {"PRESENT"})
        self.assertEqual({row["source"] for row in events}, {"STAGE55_OFFICIAL_XI"})

    def test_post_kickoff_snapshot_is_rejected(self):
        snap = self.snapshot()
        snap["captured_at_utc"] = "2026-09-25T19:00:00Z"
        events, status = m.events_from_snapshot(snap)
        self.assertEqual(events, [])
        self.assertEqual(status, "LOOKAHEAD_VIOLATION")

    def test_append_only_merge_is_idempotent(self):
        events, _ = m.events_from_snapshot(self.snapshot())
        rows, added, invalid = m.merge_events([], events)
        self.assertEqual(added, 1)
        self.assertEqual(invalid, 0)
        rows2, added2, invalid2 = m.merge_events(rows, events)
        self.assertEqual(len(rows2), 1)
        self.assertEqual(added2, 0)
        self.assertEqual(invalid2, 0)


if __name__ == "__main__":
    unittest.main()
