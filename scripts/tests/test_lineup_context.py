import json
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lineup_context as lineup


KICKOFF = "2026-09-20T16:00:00Z"


def xi(prefix, start=1):
    return [
        {"id": f"{prefix}{i}", "name": f"{prefix}-Player-{i}", "number": i, "pos": "M", "grid": f"2:{i}"}
        for i in range(start, start + 11)
    ]


class LineupContextTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        c = self.conn
        c.execute(
            "CREATE TABLE current_round_matches (fixture_id TEXT, kickoff_utc TEXT, home_team TEXT, away_team TEXT, status TEXT)"
        )
        c.execute(
            "INSERT INTO current_round_matches VALUES (?,?,?,?,?)",
            ("999", KICKOFF, "Alpha", "Beta", "scheduled"),
        )
        c.execute(
            "CREATE TABLE context_latest (api_fixture_id TEXT, captured_at_utc TEXT, home_team_id TEXT, away_team_id TEXT, "
            "lineups_available TEXT, home_formation TEXT, away_formation TEXT, home_coach TEXT, away_coach TEXT, "
            "home_start_xi_json TEXT, away_start_xi_json TEXT)"
        )
        c.execute(
            "INSERT INTO context_latest VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("999", "2026-09-20T12:00:00Z", "10", "20", "NO", "", "", "", "", "[]", "[]"),
        )
        c.execute(
            "CREATE TABLE raw_rotation_snapshots (api_fixture_id TEXT, captured_at_utc TEXT, kickoff_utc TEXT, "
            "home_team_id TEXT, away_team_id TEXT, home_current_formation TEXT, away_current_formation TEXT, "
            "home_current_coach TEXT, away_current_coach TEXT, home_current_xi_json TEXT, away_current_xi_json TEXT, "
            "current_lineups_available TEXT)"
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def add_rotation(self, fixture_id, captured, kickoff, home_id, away_id, home_xi, away_xi,
                     home_formation="4-3-3", away_formation="4-2-3-1", home_coach="Coach A", away_coach="Coach B",
                     available="YES"):
        self.conn.execute(
            "INSERT INTO raw_rotation_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (fixture_id, captured, kickoff, str(home_id), str(away_id), home_formation, away_formation,
             home_coach, away_coach, json.dumps(home_xi), json.dumps(away_xi), available),
        )
        self.conn.commit()

    def build(self):
        status, payload = lineup.build_lineup_context(self.conn, "999")
        self.assertEqual(status, 200)
        return payload

    def test_expected_xi_uses_only_prior_complete_official_lineups(self):
        first = xi("A")
        second = xi("A")
        self.add_rotation("901", "2026-09-01T14:00:00Z", "2026-09-01T15:00:00Z", 10, 31, first, xi("X"))
        self.add_rotation("902", "2026-09-10T14:00:00Z", "2026-09-10T15:00:00Z", 10, 32, second, xi("Y"))
        self.add_rotation("903", "2026-09-01T14:00:00Z", "2026-09-01T15:00:00Z", 40, 20, xi("Z"), xi("B"))
        self.add_rotation("904", "2026-09-10T14:00:00Z", "2026-09-10T15:00:00Z", 41, 20, xi("W"), xi("B"))

        payload = self.build()
        self.assertEqual(payload["home"]["status"], "EXPECTED")
        self.assertEqual(payload["away"]["status"], "EXPECTED")
        self.assertEqual(payload["home"]["expected_confidence"], "LOW")
        self.assertEqual(payload["home"]["expected_basis_fixtures"], 2)
        self.assertEqual(len(payload["home"]["starting_xi"]), 11)
        self.assertEqual(payload["home"]["formation"], "4-3-3")
        self.assertEqual(payload["home"]["coach"], "Coach A")
        self.assertTrue(payload["no_lookahead"])
        self.assertFalse(payload["provider_polling"])
        self.assertFalse(payload["creates_signal"])

    def test_post_kickoff_lineup_is_never_used(self):
        self.add_rotation("901", "2026-09-01T14:00:00Z", "2026-09-01T15:00:00Z", 10, 31, xi("A"), xi("X"))
        self.add_rotation("902", "2026-09-10T14:00:00Z", "2026-09-10T15:00:00Z", 10, 32, xi("A"), xi("Y"))
        self.add_rotation("999", "2026-09-20T16:05:00Z", KICKOFF, 10, 20, xi("LIVE"), xi("POST"))
        payload = self.build()
        self.assertEqual(payload["home"]["status"], "EXPECTED")
        self.assertNotIn("LIVE1", {p["id"] for p in payload["home"]["starting_xi"]})
        self.assertIsNone(payload["home"]["official"])

    def test_pre_kickoff_official_xi_overrides_expected(self):
        self.add_rotation("901", "2026-09-01T14:00:00Z", "2026-09-01T15:00:00Z", 10, 31, xi("A"), xi("X"))
        self.add_rotation("902", "2026-09-10T14:00:00Z", "2026-09-10T15:00:00Z", 10, 32, xi("A"), xi("Y"))
        official = xi("OFF")
        self.add_rotation("999", "2026-09-20T15:20:00Z", KICKOFF, 10, 20, official, xi("BETA"),
                          home_formation="3-4-2-1", home_coach="Official Coach")
        payload = self.build()
        self.assertEqual(payload["home"]["status"], "CONFIRMED")
        self.assertTrue(payload["home"]["confirmed"])
        self.assertEqual(payload["home"]["formation"], "3-4-2-1")
        self.assertEqual(payload["home"]["coach"], "Official Coach")
        self.assertEqual(payload["home"]["starting_xi"][0]["id"], "OFF1")
        self.assertEqual(payload["home"]["official"]["source"], "raw_rotation_snapshots:official_lineup")

    def test_context_official_xi_is_accepted_but_postkickoff_context_is_not(self):
        pre = json.dumps(xi("CTX"))
        self.conn.execute(
            "INSERT INTO context_latest VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("999", "2026-09-20T15:10:00Z", "10", "20", "YES", "4-4-2", "4-3-3", "Ctx H", "Ctx A", pre, json.dumps(xi("CA"))),
        )
        self.conn.execute(
            "INSERT INTO context_latest VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("999", "2026-09-20T16:10:00Z", "10", "20", "YES", "9-9-9", "9-9-9", "Leak", "Leak", json.dumps(xi("LEAK")), json.dumps(xi("LEAKA"))),
        )
        self.conn.commit()
        payload = self.build()
        self.assertEqual(payload["home"]["status"], "CONFIRMED")
        self.assertEqual(payload["home"]["formation"], "4-4-2")
        self.assertEqual(payload["home"]["starting_xi"][0]["id"], "CTX1")
        self.assertNotEqual(payload["home"]["coach"], "Leak")

    def test_incomplete_or_insufficient_history_stays_unknown(self):
        self.add_rotation("901", "2026-09-01T14:00:00Z", "2026-09-01T15:00:00Z", 10, 31, xi("A"), xi("X"))
        self.add_rotation("902", "2026-09-10T14:00:00Z", "2026-09-10T15:00:00Z", 40, 20, xi("Z"), xi("B")[:10])
        payload = self.build()
        self.assertEqual(payload["home"]["status"], "UNKNOWN")
        self.assertEqual(payload["away"]["status"], "UNKNOWN")
        self.assertEqual(payload["coverage"]["status"], "UNKNOWN")
        self.assertIn("EXPECTED_XI_HISTORY_INSUFFICIENT", payload["home"]["limitations"])

    def test_missing_fixture_and_missing_id_contracts_are_stable(self):
        status, payload = lineup.build_lineup_context(self.conn, "")
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "MISSING_FIXTURE_ID")
        status, payload = lineup.build_lineup_context(self.conn, "missing")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "UNKNOWN_FIXTURE")


if __name__ == "__main__":
    unittest.main()
