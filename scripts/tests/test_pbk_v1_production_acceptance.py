import csv
import json
import socket
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pbk_v1_production_acceptance as acceptance


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class ProductionAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ops = self.root / "ops"
        self.db = self.root / "pbk.sqlite"
        self.ops.mkdir()
        write_json(self.ops / "system_health.json", {
            "status": "WARN", "summary": {"critical_issues": 0, "warnings": 2}
        })
        write_json(self.ops / "stage72_last_run.json", {
            "run_at_utc": "2026-09-15T12:10:00Z", "status": "OK", "integrity_check": "ok",
            "schema_version": "14", "historical_leakage_violations": 0,
            "stable_counts": {"standings_snapshots": 0, "fixture_motivation": 1},
        })
        write_json(self.ops / "stage73_last_run.json", {
            "run_at_utc": "2026-09-15T12:11:00Z", "status": "OK", "passed": 16, "total": 16,
        })
        write_csv(self.ops / "current_round_fixtures.csv", [
            "fixture_id", "provider_league_id", "season", "kickoff_utc", "status", "source_status"
        ], [{
            "fixture_id": "999", "provider_league_id": "39", "season": "2026",
            "kickoff_utc": "2026-09-15T12:30:00Z", "status": "scheduled", "source_status": "NS",
        }])
        self.live_fields = [
            "fixture_id", "source_status", "status", "score_home", "score_away", "elapsed",
            "observed_at_utc", "live_observed_at_utc", "live_freshness_status",
            "red_cards_home", "red_cards_away",
        ]
        write_csv(self.ops / "live_fixture_overlay.csv", self.live_fields, [])
        self.make_db(available=False)

    def tearDown(self):
        self.tmp.cleanup()

    def make_db(self, available):
        if self.db.exists():
            self.db.unlink()
        conn = sqlite3.connect(self.db)
        conn.execute("CREATE TABLE fixture_motivation (fixture_id TEXT, available TEXT, no_lookahead TEXT)")
        conn.execute("INSERT INTO fixture_motivation VALUES ('999', ?, '1')", ('1' if available else '0',))
        conn.commit()
        conn.close()

    def waiting_runtime(self):
        write_json(self.ops / "current_round_last_run.json", {
            "run_at_utc": "2026-09-15T12:00:00Z", "status": "ATTENTION",
            "served_available_leagues": 16, "served_fixture_rows": 129,
            "api_calls": 0, "refreshed_leagues": 0, "budget_exhausted": True,
            "last_good_preserved": True, "refresh_status": "BUDGET_EXHAUSTED",
        })
        write_json(self.ops / "live_fixture_overlay_last_run.json", {
            "observed_at_utc": "2026-09-15T12:02:00Z", "status": "ATTENTION",
            "candidate_fixtures": 8, "provider_calls": 0, "updated_fixtures": 0,
            "budget_exhausted": True,
        })

    def passing_runtime(self):
        write_json(self.ops / "current_round_last_run.json", {
            "run_at_utc": "2026-09-15T11:17:00Z", "status": "OK",
            "served_available_leagues": 16, "served_fixture_rows": 129,
            "api_calls": 16, "refreshed_leagues": 16, "budget_exhausted": False,
            "last_good_preserved": True, "refresh_status": "OK",
        })
        write_json(self.ops / "live_fixture_overlay_last_run.json", {
            "observed_at_utc": "2026-09-15T12:02:00Z", "status": "OK",
            "candidate_fixtures": 3, "provider_calls": 1, "updated_fixtures": 3,
            "budget_exhausted": False,
        })
        write_csv(self.ops / "live_fixture_overlay.csv", self.live_fields, [{
            "fixture_id": "999", "source_status": "1H", "status": "live",
            "score_home": "1", "score_away": "0", "elapsed": "35",
            "observed_at_utc": "2026-09-15T12:02:00Z",
            "live_observed_at_utc": "2026-09-15T12:02:00Z", "live_freshness_status": "fresh",
            "red_cards_home": "0", "red_cards_away": "1",
        }])
        write_csv(self.ops / "standings_snapshots.csv", [
            "snapshot_id", "provider_league_id", "league_name", "season", "observed_at_utc",
            "team_id", "team_name", "team_logo_url", "rank", "points", "played", "win", "draw",
            "lose", "goals_for", "goals_against", "goals_diff", "form", "group_name", "description", "source",
        ], [
            {"snapshot_id": "snap-1", "provider_league_id": "39", "league_name": "Premier League",
             "season": "2026", "observed_at_utc": "2026-09-15T11:45:00Z", "team_id": "1",
             "team_name": "Alpha", "source": "api-football:/standings"},
            {"snapshot_id": "snap-1", "provider_league_id": "39", "league_name": "Premier League",
             "season": "2026", "observed_at_utc": "2026-09-15T11:45:00Z", "team_id": "2",
             "team_name": "Beta", "source": "api-football:/standings"},
        ])
        stage72 = json.loads((self.ops / "stage72_last_run.json").read_text())
        stage72["stable_counts"]["standings_snapshots"] = 2
        stage72["run_at_utc"] = "2026-09-15T12:10:00Z"
        write_json(self.ops / "stage72_last_run.json", stage72)
        self.make_db(available=True)

    def test_budget_exhaustion_with_last_good_is_waiting_not_failure(self):
        self.waiting_runtime()
        payload = acceptance.canonical_payload(self.ops, self.db)
        self.assertEqual(payload["status"], "WAITING")
        self.assertEqual(payload["items"]["4_today_live"]["status"], "WAITING")
        safety = {x["code"]: x for x in payload["items"]["4_today_live"]["checks"]}
        self.assertEqual(safety["CURRENT_ROUND_BUDGET_SAFETY"]["status"], "PASS")
        self.assertEqual(payload["provider_calls"], 0)
        self.assertEqual(payload["network_calls"], 0)

    def test_full_real_evidence_passes_items_4_and_5(self):
        self.passing_runtime()
        payload = acceptance.canonical_payload(self.ops, self.db)
        self.assertEqual(payload["status"], "PASS")
        self.assertTrue(payload["ready_to_close"])
        self.assertEqual(payload["items"]["4_today_live"]["status"], "PASS")
        self.assertEqual(payload["items"]["5_standings_motivation"]["status"], "PASS")

    def test_postkickoff_standings_evidence_fails_closed(self):
        self.passing_runtime()
        path = self.ops / "standings_snapshots.csv"
        fields, rows = acceptance.read_csv(path)
        for row in rows:
            row["observed_at_utc"] = "2026-09-15T12:31:00Z"
        write_csv(path, fields, rows)
        payload = acceptance.canonical_payload(self.ops, self.db)
        self.assertEqual(payload["items"]["5_standings_motivation"]["status"], "FAIL")
        self.assertEqual(payload["status"], "FAIL")

    def test_destructive_budget_regression_is_hard_failure(self):
        self.waiting_runtime()
        meta = json.loads((self.ops / "current_round_last_run.json").read_text())
        meta.update(served_available_leagues=0, served_fixture_rows=0, last_good_preserved=False)
        write_json(self.ops / "current_round_last_run.json", meta)
        payload = acceptance.canonical_payload(self.ops, self.db)
        self.assertEqual(payload["items"]["4_today_live"]["status"], "FAIL")

    def test_pass_is_latched_across_later_waiting_state_but_not_failure(self):
        self.passing_runtime()
        first = acceptance.canonical_payload(self.ops, self.db)
        self.assertEqual(first["items"]["4_today_live"]["status"], "PASS")
        self.waiting_runtime()
        second = acceptance.canonical_payload(self.ops, self.db, previous=first)
        self.assertEqual(second["items"]["4_today_live"]["status"], "PASS")
        self.assertTrue(second["items"]["4_today_live"].get("latched"))
        meta = json.loads((self.ops / "current_round_last_run.json").read_text())
        meta.update(served_available_leagues=0, served_fixture_rows=0, last_good_preserved=False)
        write_json(self.ops / "current_round_last_run.json", meta)
        third = acceptance.canonical_payload(self.ops, self.db, previous=second)
        self.assertEqual(third["items"]["4_today_live"]["status"], "FAIL")

    def test_output_is_stable_when_acceptance_state_does_not_change(self):
        self.waiting_runtime()
        first, changed1 = acceptance.write_outputs(self.ops, self.db)
        raw1 = (self.ops / "pbk_v1_production_acceptance.json").read_bytes()
        second, changed2 = acceptance.write_outputs(self.ops, self.db)
        raw2 = (self.ops / "pbk_v1_production_acceptance.json").read_bytes()
        self.assertTrue(changed1)
        self.assertFalse(changed2)
        self.assertEqual(raw1, raw2)
        self.assertEqual(first["state_fingerprint"], second["state_fingerprint"])

    def test_gate_performs_no_network_calls(self):
        self.waiting_runtime()
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            payload = acceptance.canonical_payload(self.ops, self.db)
        self.assertIn(payload["status"], {"WAITING", "PASS", "FAIL"})


if __name__ == "__main__":
    unittest.main()
