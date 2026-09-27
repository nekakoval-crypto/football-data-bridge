import unittest

from scripts.point14_current_roster_firewall_v22 import latest_roster_snapshot


class TestCurrentRosterFirewallV22(unittest.TestCase):
    def test_latest_snapshot_is_selected(self):
        rows = [
            {"team_id":"33","captured_at_utc":"2026-09-01T00:00:00Z","player_id":"1"},
            {"team_id":"33","captured_at_utc":"2026-09-18T00:00:00Z","player_id":"2"},
            {"team_id":"33","captured_at_utc":"2026-09-18T00:00:00Z","player_id":"3"},
        ]
        r = latest_roster_snapshot(rows, team_id="33", as_of_utc="2026-09-27T00:00:00+00:00")
        self.assertEqual(r["status"], "CURRENT_ROSTER_FRESH")
        self.assertEqual(r["player_count"], 2)
        self.assertEqual({x["player_id"] for x in r["rows"]}, {"2","3"})

    def test_stale_snapshot_fails_closed(self):
        rows = [{"team_id":"33","captured_at_utc":"2026-07-01T00:00:00Z","player_id":"1"}]
        r = latest_roster_snapshot(rows, team_id="33", as_of_utc="2026-09-27T00:00:00+00:00")
        self.assertEqual(r["status"], "CURRENT_ROSTER_STALE")

    def test_missing_snapshot_fails_closed(self):
        r = latest_roster_snapshot([], team_id="33", as_of_utc="2026-09-27T00:00:00+00:00")
        self.assertEqual(r["status"], "CURRENT_ROSTER_EVIDENCE_MISSING")


if __name__ == "__main__":
    unittest.main()
