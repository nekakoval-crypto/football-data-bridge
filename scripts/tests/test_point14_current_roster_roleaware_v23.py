import unittest
from collections import Counter
from scripts.point14_current_roster_roleaware_v23 import latest_roster_snapshot

class TestV23(unittest.TestCase):
    def test_current_roster_latest_only(self):
        rows = [
            {"team_id":"33","captured_at_utc":"2026-09-01T00:00:00Z","player_id":"old"},
            {"team_id":"33","captured_at_utc":"2026-09-18T00:00:00Z","player_id":"new"},
        ]
        r = latest_roster_snapshot(rows, "33", "2026-09-27T00:00:00+00:00")
        self.assertEqual(r["status"], "CURRENT_ROSTER_FRESH")
        self.assertEqual([x["player_id"] for x in r["rows"]], ["new"])

if __name__ == "__main__":
    unittest.main()
