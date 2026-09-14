import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import standings_snapshot_capture as capture


NOW = datetime(2026, 9, 14, 10, 0, tzinfo=timezone.utc)
FIELDS = capture.FIELDS


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def schedule(league="39", season="2026", kickoff=NOW + timedelta(minutes=60), fixture_id=None):
    return {
        "provider_league_id": league, "league_name": f"League {league}",
        "season": season, "fixture_id": fixture_id or f"{league}-{kickoff.minute}",
        "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
    }


def provider(league="39", season=2026, groups=None):
    groups = groups if groups is not None else [[{
        "rank": 1, "team": {"id": 10, "name": "Alpha", "logo": "logo"},
        "points": 20, "all": {"played": 8, "win": 6, "draw": 2, "lose": 0,
                              "goals": {"for": 18, "against": 4}},
        "goalsDiff": 14, "form": "WWDWW", "group": "Group A",
        "description": "Champions League",
    }]]
    return {"response": [{"league": {"id": int(league), "season": season,
                                     "name": f"League {league}", "standings": groups}}]}


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Path(self.temp.name)
        write_csv(self.ops / "current_round_leagues.csv",
                  ["provider_league_id", "league_name", "season"], [
                      {"provider_league_id": "39", "league_name": "League 39", "season": "2026"},
                      {"provider_league_id": "140", "league_name": "League 140", "season": "2026"}])
        self.write_fixtures([schedule()])
        (self.ops / "stage71_observation_state.json").write_text(
            json.dumps({"api_day": NOW.date().isoformat(), "api_day_calls": 0}), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def write_fixtures(self, rows):
        write_csv(self.ops / "current_round_fixtures.csv",
                  ["fixture_id", "provider_league_id", "season", "kickoff_utc"], rows)

    def execute(self, fake, now=NOW):
        with patch.object(capture, "NO_DATA_BACKOFF", timedelta(hours=6)):
            return capture.capture_run(now=now, get=fake, ops=self.ops)

    def test_far_future_fixture_has_no_candidate_or_call(self):
        self.write_fixtures([schedule(kickoff=NOW + timedelta(days=3))])
        calls = []
        meta = self.execute(lambda *args, **kwargs: calls.append((args, kwargs)))
        self.assertEqual(calls, [])
        self.assertEqual(meta["candidate_leagues"], 0)

    def test_candidate_calls_provider_with_force_refresh(self):
        calls = []
        meta = self.execute(lambda path, params, **kwargs: calls.append((path, params, kwargs)) or provider())
        self.assertEqual(meta["provider_calls"], 1)
        self.assertEqual(calls[0][0], "/standings")
        self.assertEqual(calls[0][1], {"league": "39", "season": "2026"})
        self.assertTrue(calls[0][2]["force_refresh"])

    def test_adequate_snapshot_skips_call_and_post_kickoff_is_not_adequate(self):
        kickoff = NOW + timedelta(minutes=60)
        existing = {key: "" for key in FIELDS}
        existing.update(snapshot_id="old", provider_league_id="39", season="2026",
                       observed_at_utc=(NOW + timedelta(minutes=30)).isoformat(), team_id="10")
        write_csv(self.ops / "standings_snapshots.csv", FIELDS, [existing])
        calls = []
        meta = self.execute(lambda *args, **kwargs: calls.append(args) or provider())
        self.assertEqual(meta["provider_calls"], 0)
        self.assertEqual(meta["skipped_adequate_snapshot"], 1)

        existing["observed_at_utc"] = (kickoff + timedelta(minutes=1)).isoformat()
        write_csv(self.ops / "standings_snapshots.csv", FIELDS, [existing])
        meta = self.execute(lambda *args, **kwargs: calls.append(args) or provider())
        self.assertEqual(meta["provider_calls"], 1)

    def test_same_league_fixture_cluster_is_one_call_and_two_leagues_are_two(self):
        self.write_fixtures([schedule(fixture_id="39-a"), schedule(kickoff=NOW + timedelta(minutes=70), fixture_id="39-b"),
                             schedule("140", kickoff=NOW + timedelta(minutes=60), fixture_id="140-a")])
        calls = []
        meta = self.execute(lambda path, params, **kwargs: calls.append(params) or provider(params["league"]))
        self.assertEqual(meta["provider_calls"], 2)
        self.assertEqual({x["league"] for x in calls}, {"39", "140"})

    def test_later_fixture_can_become_a_new_candidate(self):
        self.write_fixtures([schedule(kickoff=NOW + timedelta(minutes=60), fixture_id="39-a"),
                             schedule(kickoff=NOW + timedelta(hours=4), fixture_id="39-b")])
        calls = []
        self.execute(lambda path, params, **kwargs: calls.append(params) or provider())
        self.assertEqual(len(calls), 1)
        # capture_run records the real provider-observation clock by design. This test uses a
        # synthetic `now`, so normalize only the test ledger to that synthetic first wake.
        rows = capture.read_snapshot_rows(self.ops / "standings_snapshots.csv")
        for row in rows:
            row["observed_at_utc"] = NOW.isoformat().replace("+00:00", "Z")
        write_csv(self.ops / "standings_snapshots.csv", FIELDS, rows)
        calls.clear()
        later = NOW + timedelta(hours=3, minutes=10)
        self.execute(lambda path, params, **kwargs: calls.append(params) or provider(), now=later)
        self.assertEqual(len(calls), 1)

    def test_group_flattening_and_factual_fields(self):
        payload = provider(groups=[
            [{"rank": 1, "team": {"id": 10, "name": "A"}, "points": 30,
              "all": {"played": 10, "win": 9, "draw": 3, "lose": 0,
                      "goals": {"for": 20, "against": 2}},
              "goalsDiff": 18, "form": "WW", "group": "North",
              "description": "Title"}],
            [{"rank": 2, "team": {"id": 11, "name": "B"}, "points": 28,
              "all": {"played": 10}, "group": "South",
              "description": "Relegation"}]])
        rows = capture.normalize_response(payload, "39", "2026", NOW)
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["group_name"] for r in rows}, {"North", "South"})
        self.assertEqual(rows[0]["description"], "Title")
        self.assertEqual(len({r["snapshot_id"] for r in rows}), 1)

    def test_duplicate_or_malformed_response_rejects_whole_observation(self):
        duplicate = provider(groups=[[{"team": {"id": 10}}, {"team": {"id": 10}}]])
        with self.assertRaises(ValueError):
            capture.normalize_response(duplicate, "39", "2026", NOW)
        with self.assertRaises(ValueError):
            capture.normalize_response({"response": [{"league": {"id": 39}}]}, "39", "2026", NOW)

    def test_failure_leaves_ledger_unchanged_and_no_data_backoff(self):
        before = "snapshot_id,provider_league_id\nold,39\n"
        (self.ops / "standings_snapshots.csv").write_text(before, encoding="utf-8")
        meta = self.execute(lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider down")))
        self.assertEqual((self.ops / "standings_snapshots.csv").read_text(encoding="utf-8"), before)
        self.assertEqual(meta["provider_calls"], 1)

        meta = self.execute(lambda *args, **kwargs: {"response": []})
        self.assertEqual(meta["provider_calls"], 1)
        meta = self.execute(lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must back off")))
        self.assertEqual(meta["skipped_no_data_backoff"], 1)

    def test_missing_schedule_fails_closed(self):
        (self.ops / "current_round_fixtures.csv").unlink()
        calls = []
        meta = self.execute(lambda *args, **kwargs: calls.append(args))
        self.assertEqual(meta["status"], "SCHEDULE_UNKNOWN")
        self.assertEqual(calls, [])

    def test_daily_budget_and_protected_reserve_defer_without_calls(self):
        (self.ops / "stage71_observation_state.json").write_text(
            json.dumps({"api_day": NOW.date().isoformat(), "api_day_calls": 180}), encoding="utf-8")
        calls = []
        meta = self.execute(lambda *args, **kwargs: calls.append(args))
        self.assertEqual(calls, [])
        self.assertEqual(meta["provider_calls"], 0)
        self.assertTrue(meta["standings_available_calls"] == 0)

    def test_headroom_is_consumed_only_by_standings_and_cap_is_enforced(self):
        self.write_fixtures([schedule("39"), schedule("140")])
        calls = []
        meta = self.execute(lambda path, params, **kwargs: calls.append(params) or provider(params["league"]))
        self.assertEqual(meta["provider_calls"], 2)
        self.assertEqual(meta["api_day_calls_after"], 2)


if __name__ == "__main__":
    unittest.main()
