import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage80_player_profile_capture as p


class Stage80PlayerProfileCaptureTests(unittest.TestCase):
    def test_candidate_teams_only_when_roster_players_missing(self):
        rosters = [
            {"team_id":"10","team_name":"Alpha","player_id":"1"},
            {"team_id":"10","team_name":"Alpha","player_id":"2"},
            {"team_id":"20","team_name":"Beta","player_id":"3"},
        ]
        existing = [
            {"team_id":"10","season":"2026","player_id":"1"},
            {"team_id":"20","season":"2026","player_id":"3"},
        ]
        fixtures = [{
            "provider_league_id":"39",
            "home_team_id":"10","away_team_id":"20",
        }]
        rows = p.candidate_teams(
            rosters, existing, "2026", fixtures, 8,
            now=datetime(2026,9,18,tzinfo=timezone.utc),
            refresh_days=7,
        )
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["team_id"],"10")
        self.assertEqual(rows[0]["missing_roster_players"],1)

    def test_big5_candidates_are_prioritized(self):
        rosters = [
            {"team_id":"10","team_name":"Alpha","player_id":"1"},
            {"team_id":"20","team_name":"Beta","player_id":"2"},
        ]
        fixtures = [
            {"provider_league_id":"218","home_team_id":"10","away_team_id":"99"},
            {"provider_league_id":"39","home_team_id":"20","away_team_id":"98"},
        ]
        rows = p.candidate_teams(
            rosters, [], "2026", fixtures, 8,
            now=datetime(2026,9,18,tzinfo=timezone.utc),
            refresh_days=7,
        )
        self.assertEqual(rows[0]["team_id"],"20")

    def test_recent_successful_team_capture_suppresses_missing_roster_recapture(self):
        rosters = [
            {"team_id":"10","team_name":"Alpha","player_id":"1"},
            {"team_id":"10","team_name":"Alpha","player_id":"2"},
        ]
        existing = [{
            "team_id":"10","season":"2026","player_id":"1",
            "captured_at_utc":"2026-09-18T10:00:00Z",
        }]
        rows = p.candidate_teams(
            rosters, existing, "2026", [], 8,
            now=datetime(2026,9,18,18,tzinfo=timezone.utc),
            refresh_days=7,
        )
        self.assertEqual(rows, [])

    def test_expired_team_capture_becomes_refresh_candidate(self):
        rosters = [
            {"team_id":"10","team_name":"Alpha","player_id":"1"},
            {"team_id":"10","team_name":"Alpha","player_id":"2"},
        ]
        existing = [{
            "team_id":"10","season":"2026","player_id":"1",
            "captured_at_utc":"2026-09-01T10:00:00Z",
        }]
        rows = p.candidate_teams(
            rosters, existing, "2026", [], 8,
            now=datetime(2026,9,18,18,tzinfo=timezone.utc),
            refresh_days=7,
        )
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["team_id"],"10")
        self.assertEqual(rows[0]["missing_roster_players"],1)
        self.assertEqual(rows[0]["last_profile_capture_at_utc"],"2026-09-01T10:00:00Z")

    def test_residual_candidates_include_missing_single_team_player(self):
        rosters = [
            {"team_id":"10","team_name":"Alpha","player_id":"1"},
            {"team_id":"10","team_name":"Alpha","player_id":"2"},
        ]
        existing = [{
            "team_id":"10","season":"2026","player_id":"1",
            "captured_at_utc":"2026-09-18T10:00:00Z",
        }]
        rows, diag = p.residual_candidates(
            rosters, existing, [], "2026", [], 20,
            now=datetime(2026,9,18,18,tzinfo=timezone.utc),
            retry_days=7,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["player_id"], "2")
        self.assertEqual(rows[0]["team_id"], "10")
        self.assertEqual(diag["ambiguous_current_roster_player_ids"], 0)

    def test_recent_empty_residual_attempt_is_suppressed(self):
        rosters = [{"team_id":"10","team_name":"Alpha","player_id":"2"}]
        state = [{
            "season":"2026","player_id":"2","team_id":"10","team_name":"Alpha",
            "status":"EMPTY","attempts":"1",
            "last_attempt_at_utc":"2026-09-18T10:00:00Z","last_error":"",
        }]
        rows, diag = p.residual_candidates(
            rosters, [], state, "2026", [], 20,
            now=datetime(2026,9,18,18,tzinfo=timezone.utc),
            retry_days=7,
        )
        self.assertEqual(rows, [])
        self.assertEqual(diag["suppressed_recent_residual_attempts"], 1)

    def test_residual_error_attempt_remains_retryable(self):
        rosters = [{"team_id":"10","team_name":"Alpha","player_id":"2"}]
        state = [{
            "season":"2026","player_id":"2","team_id":"10","team_name":"Alpha",
            "status":"ERROR","attempts":"1",
            "last_attempt_at_utc":"2026-09-18T10:00:00Z","last_error":"temporary",
        }]
        rows, _ = p.residual_candidates(
            rosters, [], state, "2026", [], 20,
            now=datetime(2026,9,18,18,tzinfo=timezone.utc),
            retry_days=7,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["player_id"], "2")

    def test_residual_candidate_rejects_ambiguous_current_roster_team(self):
        rosters = [
            {"team_id":"10","team_name":"Alpha","player_id":"2"},
            {"team_id":"20","team_name":"Beta","player_id":"2"},
        ]
        rows, diag = p.residual_candidates(
            rosters, [], [], "2026", [], 20,
            now=datetime(2026,9,18,18,tzinfo=timezone.utc),
            retry_days=7,
        )
        self.assertEqual(rows, [])
        self.assertEqual(diag["ambiguous_current_roster_player_ids"], 1)

    def test_capture_residual_player_uses_current_roster_team_context(self):
        calls = []
        def get_page(path, params, **kwargs):
            calls.append((path, dict(params)))
            return {
                "response":[{
                    "player":{
                        "id":2,
                        "name":"Full Player",
                        "firstname":"Full",
                        "lastname":"Player",
                        "birth":{"date":"2000-01-01","place":"Town","country":"X"},
                        "nationality":"X",
                    },
                    "statistics":[{"team":{"id":99,"name":"Old Team"}}],
                }],
            }
        rows = p.capture_residual_player(
            {"player_id":"2","team_id":"10","team_name":"Alpha"},
            "2026",
            get_page,
            "2026-09-18T18:00:00Z",
        )
        self.assertEqual(calls, [("/players", {"id":"2","season":"2026"})])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["team_id"], "10")
        self.assertEqual(rows[0]["team_name"], "Alpha")
        self.assertEqual(rows[0]["source"], p.RESIDUAL_SOURCE)

    def test_capture_residual_player_empty_response_is_not_profile_evidence(self):
        rows = p.capture_residual_player(
            {"player_id":"2","team_id":"10","team_name":"Alpha"},
            "2026",
            lambda *args, **kwargs: {"response":[]},
            "2026-09-18T18:00:00Z",
        )
        self.assertEqual(rows, [])

    def test_update_residual_state_increments_attempts(self):
        state = [{
            "season":"2026","player_id":"2","team_id":"10","team_name":"Alpha",
            "status":"EMPTY","attempts":"1",
            "last_attempt_at_utc":"2026-09-10T00:00:00Z","last_error":"",
        }]
        updated = p.update_residual_state(
            state,
            "2026",
            {"player_id":"2","team_id":"10","team_name":"Alpha"},
            "CAPTURED",
            "2026-09-18T18:00:00Z",
        )
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["attempts"], "2")
        self.assertEqual(updated[0]["status"], "CAPTURED")

    def test_capture_team_reads_all_pages_before_returning(self):
        calls = []
        def get_page(path, params, **kwargs):
            calls.append(params["page"])
            page = params["page"]
            return {
                "paging":{"current":page,"total":2},
                "response":[{
                    "player":{
                        "id":page,
                        "name":f"Player {page}",
                        "firstname":"Player",
                        "lastname":str(page),
                        "birth":{"date":"2000-01-01","place":"","country":"X"},
                        "nationality":"X",
                    },
                    "statistics":[{"team":{"id":10,"name":"Alpha"}}],
                }],
            }
        rows = p.capture_team(
            {"team_id":"10","team_name":"Alpha"},
            "2026",
            get_page,
            max_pages=4,
            captured_at="2026-09-18T00:00:00Z",
        )
        self.assertEqual(calls,[1,2])
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["source"],"api-football:/players?team&season")

    def test_capture_team_fails_closed_if_pagination_exceeds_guard(self):
        def get_page(path, params, **kwargs):
            return {"paging":{"current":1,"total":5},"response":[]}
        with self.assertRaises(RuntimeError):
            p.capture_team(
                {"team_id":"10","team_name":"Alpha"},
                "2026",
                get_page,
                max_pages=4,
                captured_at="2026-09-18T00:00:00Z",
            )

    def test_page_budget_counts_and_preserves_reserve(self):
        state={"api_day":"2026-09-18","api_day_calls":7}
        saved=[]
        budget=p.PageBudget(
            lambda path, params, **kwargs: {"response":[],"paging":{"total":1}},
            state,
            datetime(2026,9,18,tzinfo=timezone.utc),
            max_calls=2,
            daily_limit=10,
            protected_calls=2,
            checkpoint=lambda s:saved.append(dict(s)),
        )
        budget("/players",{"team":"1"})
        self.assertEqual(state["api_day_calls"],8)
        with self.assertRaises(p.audit.ProtectedBudgetError):
            budget("/players",{"team":"2"})
        self.assertTrue(saved)

    def test_merge_rows_is_bounded_by_team_season_player_identity(self):
        existing=[{
            "team_id":"10","season":"2026","player_id":"1",
            "player_name":"Old",
        }]
        incoming=[{
            "team_id":"10","season":"2026","player_id":"1",
            "player_name":"Full Name",
        },{
            "team_id":"10","season":"2026","player_id":"2",
            "player_name":"Second",
        }]
        rows=p.merge_rows(existing,incoming)
        self.assertEqual(len(rows),2)
        self.assertEqual(next(r for r in rows if r["player_id"]=="1")["player_name"],"Full Name")


if __name__=="__main__":
    unittest.main()
