import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage98_historical_context_backfill as s98


class Stage98HistoricalContextBackfillTests(unittest.TestCase):
    def now(self):
        return datetime(2026, 9, 18, 20, 0, tzinfo=timezone.utc)

    def fixture(self, fixture_id="100", terminal="YES"):
        return {
            "fixture_id": fixture_id,
            "provider_league_id": "140",
            "league_name": "La Liga",
            "season": "2026",
            "round": "Regular Season - 6",
            "home_team": "Home",
            "away_team": "Away",
            "latest_kickoff_utc": "2026-09-18T18:00:00Z",
            "terminal_observed": terminal,
        }

    def backlog_row(self, fixture_id="100"):
        return {
            "fixture_id": fixture_id,
            "provider_league_id": "140",
            "league_name": "La Liga",
            "season": "2026",
            "round": "Regular Season - 6",
            "kickoff_utc": "2026-09-18T18:00:00Z",
            "home_team": "Home",
            "away_team": "Away",
            "first_queued_at_utc": "2026-09-18T19:00:00Z",
            "last_seen_at_utc": "2026-09-18T19:00:00Z",
            "queue_source": "stage80_historical_terminal_fixture",
            "lineup_status": "PENDING",
            "lineup_attempt_count": "0",
            "lineup_last_attempt_at_utc": "",
            "lineup_last_attempt_result": "",
            "lineup_captured_at_utc": "",
            "injury_status": "PENDING",
            "injury_attempt_count": "0",
            "injury_last_attempt_at_utc": "",
            "injury_last_attempt_result": "",
            "injury_captured_at_utc": "",
        }

    def lineup_block(self, team_id, name):
        return {
            "team": {"id": team_id, "name": name},
            "formation": "4-3-3",
            "coach": {"name": f"{name} Coach"},
            "startXI": [
                {"player": {
                    "id": team_id * 100 + i,
                    "name": f"{name} P{i}",
                    "number": i,
                    "pos": "M",
                    "grid": "1:1",
                }}
                for i in range(1, 12)
            ],
        }

    def test_sync_backlog_queues_only_terminal_historical_fixtures(self):
        result = s98.sync_backlog(
            [],
            [self.fixture("100", "YES"), self.fixture("101", "NO")],
            [],
            [],
            self.now(),
        )
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["fixture_id"], "100")
        self.assertEqual(result["lineup_pending"], 1)
        self.assertEqual(result["injury_pending"], 1)

    def test_complete_two_team_lineup_is_evidence(self):
        fixture = self.backlog_row()
        payload = {"response": [
            self.lineup_block(1, "Home"),
            self.lineup_block(2, "Away"),
        ]}
        rows = s98.normalize_lineups(
            payload, fixture, "2026-09-18T20:00:00Z"
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["side"] for r in rows}, {"HOME", "AWAY"})
        self.assertTrue(all(r["starting_xi_count"] == "11" for r in rows))
        self.assertTrue(all(r["research_only"] == "true" for r in rows))

    def test_partial_lineup_is_rejected_not_frozen(self):
        fixture = self.backlog_row()
        home = self.lineup_block(1, "Home")
        away = self.lineup_block(2, "Away")
        away["startXI"] = away["startXI"][:10]
        rows = s98.normalize_lineups(
            {"response": [home, away]},
            fixture,
            "2026-09-18T20:00:00Z",
        )
        self.assertEqual(rows, [])

    def test_empty_injury_response_is_unknown_not_zero(self):
        rows = s98.normalize_injuries(
            {"response": []},
            self.backlog_row(),
            "2026-09-18T20:00:00Z",
        )
        self.assertEqual(rows, [])

    def test_explicit_injury_rows_are_deduplicated(self):
        item = {
            "player": {
                "id": 10,
                "name": "Player",
                "type": "Missing Fixture",
                "reason": "Knee Injury",
            },
            "team": {"id": 1, "name": "Home"},
        }
        rows = s98.normalize_injuries(
            {"response": [item, item]},
            self.backlog_row(),
            "2026-09-18T20:00:00Z",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["player_id"], "10")
        self.assertEqual(rows[0]["availability_type"], "Missing Fixture")

    def test_no_data_cooldown_is_endpoint_specific(self):
        row = self.backlog_row()
        row["lineup_attempt_count"] = "1"
        row["lineup_last_attempt_result"] = "NO_DATA"
        row["lineup_last_attempt_at_utc"] = "2026-09-18T18:00:00Z"
        self.assertFalse(s98.retry_ready(row, "lineup", self.now()))
        self.assertTrue(s98.retry_ready(row, "injury", self.now()))

    def test_record_attempt_increments_only_target_endpoint(self):
        row = self.backlog_row()
        updated = s98.record_attempt(
            [row], "100", "lineup", "2026-09-18T20:00:00Z", "NO_DATA"
        )
        self.assertEqual(updated[0]["lineup_attempt_count"], "1")
        self.assertEqual(updated[0]["lineup_last_attempt_result"], "NO_DATA")
        self.assertEqual(updated[0]["injury_attempt_count"], "0")

    def test_capture_keeps_empty_injuries_pending(self):
        backlog = [self.backlog_row()]
        calls = []

        def get(path, params, **kwargs):
            calls.append((path, dict(params)))
            if path == "/fixtures/lineups":
                return {"response": [
                    self.lineup_block(1, "Home"),
                    self.lineup_block(2, "Away"),
                ]}
            if path == "/injuries":
                return {"response": []}
            raise AssertionError(path)

        result = s98.capture(
            backlog, [], [], get, self.now(), max_fixtures=10
        )
        self.assertEqual(result["tasks_attempted"], 2)
        self.assertEqual(result["lineup_rows_added"], 2)
        self.assertEqual(result["injury_rows_added"], 0)
        self.assertEqual(result["backlog"]["lineup_captured"], 1)
        self.assertEqual(result["backlog"]["injury_pending"], 1)
        self.assertEqual(result["injury_no_data"], 1)
        self.assertEqual(calls, [
            ("/fixtures/lineups", {"fixture": "100"}),
            ("/injuries", {"fixture": "100"}),
        ])

    def test_existing_complete_evidence_is_not_requeried(self):
        fixture = self.backlog_row()
        lineups = s98.normalize_lineups(
            {"response": [
                self.lineup_block(1, "Home"),
                self.lineup_block(2, "Away"),
            ]},
            fixture,
            "2026-09-18T19:00:00Z",
        )
        injuries = s98.normalize_injuries(
            {"response": [{
                "player": {"id": 10, "name": "P", "type": "Missing", "reason": "Knee"},
                "team": {"id": 1, "name": "Home"},
            }]},
            fixture,
            "2026-09-18T19:00:00Z",
        )
        synced = s98.sync_backlog(
            [fixture], [], lineups, injuries, self.now()
        )
        candidates = s98.candidate_fixtures(
            synced["rows"], self.now(), 10
        )
        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
