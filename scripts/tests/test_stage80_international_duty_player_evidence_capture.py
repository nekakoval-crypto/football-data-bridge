import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import stage80_international_duty_player_evidence_capture as c
from scripts import stage80_international_duty_player_evidence_backlog as q


def backlog_row(fid="101", endpoint="/fixtures/players", tier="DIRECT_MINUTES", status="PENDING"):
    return {
        "fixture_id": str(fid),
        "provider_league_id": "5",
        "competition_name": "UEFA Nations League",
        "candidate_family": "NATIONS_LEAGUE",
        "season": "2024",
        "round": "League A - 1",
        "kickoff_utc": "2024-09-05T18:45:00Z",
        "source_status": "FT",
        "home_team_id": "10",
        "home_team": "Country A",
        "away_team_id": "20",
        "away_team": "Country B",
        "evidence_tier": tier,
        "capture_endpoint": endpoint,
        "capture_priority": "1" if endpoint == "/fixtures/players" else "2",
        "window_id": "2024_SEP",
        "window_start_utc": "2024-09-02T00:00:00Z",
        "window_end_utc": "2024-09-10T23:59:59Z",
        "window_max_matches": "2",
        "queue_reason": "FINISHED_ALLOWLISTED_FIXTURE_INSIDE_FIXED_INTL_WINDOW",
        "first_queued_at_utc": "2026-09-19T14:40:00Z",
        "last_seen_at_utc": "2026-09-19T14:40:00Z",
        "backlog_status": status,
        "captured_at_utc": "",
        "attempt_count": "0",
        "last_attempt_at_utc": "",
        "last_attempt_result": "",
        "last_error": "",
        "callup_inference_allowed": "false",
        "nationality_inference_allowed": "false",
        "travel_inference_allowed": "false",
        "appearance_inference_allowed": "false",
        "historical_backfill_only": "true",
        "research_only": "true",
        "operational_betting_authority": "false",
        "creates_signal": "false",
        "probability_mutation": "false",
        "eligibility_mutation": "false",
        "stake_changes": "false",
        "forward_journal_mutation": "false",
    }


def players_payload():
    def player(pid, name, minutes, substitute, captain=False):
        return {
            "player": {"id": pid, "name": name},
            "statistics": [{
                "games": {
                    "minutes": minutes,
                    "position": "M",
                    "rating": "7.1",
                    "captain": captain,
                    "substitute": substitute,
                }
            }],
        }
    return {
        "errors": [],
        "paging": {"current": 1, "total": 1},
        "response": [
            {
                "team": {"id": 10, "name": "Country A"},
                "players": [
                    player(1001, "Starter", 90, False, True),
                    player(1002, "Impact Sub", 30, True),
                    player(1003, "Unused Sub", 0, True),
                ],
            },
            {
                "team": {"id": 20, "name": "Country B"},
                "players": [player(2001, "Away Starter", 90, False)],
            },
        ],
    }


def lineups_payload():
    return {
        "errors": [],
        "paging": {"current": 1, "total": 1},
        "response": [
            {
                "team": {"id": 10, "name": "Country A"},
                "startXI": [
                    {"player": {"id": 1001, "name": "Starter", "number": 8, "pos": "M", "grid": "2:2"}}
                ],
                "substitutes": [
                    {"player": {"id": 1002, "name": "Bench", "number": 18, "pos": "M", "grid": None}}
                ],
            },
            {
                "team": {"id": 20, "name": "Country B"},
                "startXI": [
                    {"player": {"id": 2001, "name": "Away Starter", "number": 9, "pos": "F", "grid": "1:1"}}
                ],
                "substitutes": [],
            },
        ],
    }


def write_csv(path, fields, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


class InternationalDutyPlayerEvidenceCaptureTests(unittest.TestCase):
    def test_player_stats_semantics_distinguish_appearance_and_unused_sub(self):
        row = backlog_row()
        rows = c.normalize_player_stats(players_payload(), row, "2026-09-19T15:00:00Z")
        by = {r["player_id"]: r for r in rows}

        starter = by["1001"]
        self.assertEqual(starter["minutes"], 90)
        self.assertEqual(starter["appearance_confirmed"], "true")
        self.assertEqual(starter["minutes_confirmed"], "true")
        self.assertEqual(starter["starter_listed_confirmed"], "false")
        self.assertEqual(starter["substitute_listed_confirmed"], "false")
        self.assertEqual(starter["substitute_appearance_confirmed"], "false")
        self.assertEqual(starter["lineup_role"], "APPEARANCE_ROLE_UNVERIFIED")

        sub = by["1002"]
        self.assertEqual(sub["minutes"], 30)
        self.assertEqual(sub["appearance_confirmed"], "true")
        self.assertEqual(sub["substitute_listed_confirmed"], "false")
        self.assertEqual(sub["starter_listed_confirmed"], "false")
        self.assertEqual(sub["substitute_appearance_confirmed"], "true")
        self.assertEqual(sub["lineup_role"], "SUBSTITUTE_APPEARANCE_PROVIDER_FLAG")

        unused = by["1003"]
        self.assertEqual(unused["minutes"], 0)
        self.assertEqual(unused["minutes_confirmed"], "true")
        self.assertEqual(unused["appearance_confirmed"], "false")
        self.assertEqual(unused["substitute_listed_confirmed"], "false")
        self.assertEqual(unused["starter_listed_confirmed"], "false")
        self.assertEqual(unused["substitute_appearance_confirmed"], "false")
        self.assertEqual(unused["lineup_role"], "PLAYER_STATS_LISTED_NO_APPEARANCE")

        self.assertTrue(all(r["formal_callup_status"] == "NOT_SEPARATELY_VERIFIED" for r in rows))
        self.assertTrue(all(r["travel_status"] == "NOT_DERIVED" for r in rows))

    def test_lineup_listing_never_infers_appearance_or_minutes(self):
        row = backlog_row(
            endpoint="/fixtures/lineups",
            tier="DIRECT_MATCHDAY_SQUAD",
        )
        rows = c.normalize_lineups(lineups_payload(), row, "2026-09-19T15:00:00Z")
        by = {r["player_id"]: r for r in rows}
        self.assertEqual(len(rows), 3)

        starter = by["1001"]
        self.assertEqual(starter["lineup_role"], "STARTER_LISTED")
        self.assertEqual(starter["starter_listed_confirmed"], "true")
        self.assertEqual(starter["matchday_squad_confirmed"], "true")
        self.assertEqual(starter["appearance_confirmed"], "false")
        self.assertEqual(starter["minutes_confirmed"], "false")
        self.assertEqual(starter["minutes"], "")

        bench = by["1002"]
        self.assertEqual(bench["lineup_role"], "SUBSTITUTE_LISTED")
        self.assertEqual(bench["substitute_listed_confirmed"], "true")
        self.assertEqual(bench["substitute_appearance_confirmed"], "false")
        self.assertEqual(bench["appearance_confirmed"], "false")
        self.assertEqual(bench["minutes_confirmed"], "false")

    def test_provider_team_must_match_fixture_national_teams(self):
        row = backlog_row()
        bad = players_payload()
        bad["response"][0]["team"]["id"] = 999
        with self.assertRaises(ValueError):
            c.normalize_player_stats(bad, row, "2026-09-19T15:00:00Z")

    def test_duplicate_player_in_lineup_fails_closed(self):
        row = backlog_row(endpoint="/fixtures/lineups", tier="DIRECT_MATCHDAY_SQUAD")
        bad = lineups_payload()
        bad["response"][0]["substitutes"].append(
            {"player": {"id": 1001, "name": "Starter Duplicate", "number": 8, "pos": "M"}}
        )
        with self.assertRaises(ValueError):
            c.normalize_lineups(bad, row, "2026-09-19T15:00:00Z")

    def test_merge_rejects_endpoint_or_tier_conflict(self):
        base = c.normalize_player_stats(
            players_payload(), backlog_row(), "2026-09-19T15:00:00Z"
        )[0]
        conflict = dict(base)
        conflict["capture_endpoint"] = "/fixtures/lineups"
        conflict["evidence_tier"] = "DIRECT_MATCHDAY_SQUAD"
        with self.assertRaises(ValueError):
            c.merge_evidence([base], [conflict])

    def test_yield_aware_scheduler_and_lineup_reserve(self):
        now = datetime(2026, 9, 19, 15, 0, tzinfo=timezone.utc)
        captured = backlog_row("90")
        captured["provider_league_id"] = "32"
        captured["backlog_status"] = "CAPTURED"
        captured["attempt_count"] = "1"

        proven = backlog_row("1")
        proven["provider_league_id"] = "32"

        unproven = backlog_row("2")
        unproven["provider_league_id"] = "5"
        unproven["kickoff_utc"] = "2025-09-05T18:45:00Z"

        low = []
        for i in range(3):
            row = backlog_row(str(30 + i))
            row["provider_league_id"] = "34"
            row["backlog_status"] = "NO_DATA"
            row["attempt_count"] = "1"
            row["last_attempt_at_utc"] = "2026-09-17T12:00:00Z"
            row["last_attempt_result"] = "NO_DATA"
            low.append(row)
        low_candidate = backlog_row("3")
        low_candidate["provider_league_id"] = "34"

        selected = c.candidate_rows(
            [captured, proven, unproven, low_candidate] + low, now, 3
        )
        self.assertEqual([r["fixture_id"] for r in selected], ["1", "2", "3"])

        lineup = backlog_row("4", "/fixtures/lineups", "DIRECT_MATCHDAY_SQUAD")
        selected = c.candidate_rows([proven, lineup], now, 2, lineup_exploration=1)
        self.assertEqual([r["fixture_id"] for r in selected], ["4", "1"])

    def test_sanitize_existing_v1_player_rows_removes_false_starter_claim(self):
        old = c.normalize_player_stats(
            players_payload(), backlog_row(), "2026-09-19T15:00:00Z"
        )
        # Simulate the durable V1 semantics that existed before the fix.
        old[0]["starter_listed_confirmed"] = "true"
        old[0]["lineup_role"] = "STARTER_APPEARANCE"
        old[1]["substitute_listed_confirmed"] = "true"
        old[1]["lineup_role"] = "SUBSTITUTE_APPEARANCE"
        sanitized, rewritten = c.sanitize_existing_evidence(old)
        by = {r["player_id"]: r for r in sanitized}

        self.assertGreaterEqual(rewritten, 2)
        self.assertEqual(by["1001"]["starter_listed_confirmed"], "false")
        self.assertEqual(by["1001"]["substitute_listed_confirmed"], "false")
        self.assertEqual(by["1001"]["lineup_role"], "APPEARANCE_ROLE_UNVERIFIED")
        self.assertEqual(by["1002"]["starter_listed_confirmed"], "false")
        self.assertEqual(by["1002"]["substitute_listed_confirmed"], "false")
        self.assertEqual(
            by["1002"]["lineup_role"],
            "SUBSTITUTE_APPEARANCE_PROVIDER_FLAG",
        )
        self.assertEqual(by["1003"]["appearance_confirmed"], "false")

    def test_run_captures_players_and_lineups_with_two_calls(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            backlog_path = root / "backlog.csv"
            backlog_meta_path = root / "backlog_meta.json"
            evidence_path = root / "evidence.csv"
            meta_path = root / "meta.json"
            shared_path = root / "shared.json"

            rows = [
                backlog_row("101"),
                backlog_row("102", "/fixtures/lineups", "DIRECT_MATCHDAY_SQUAD"),
            ]
            write_csv(backlog_path, q.FIELDS, rows)
            backlog_meta_path.write_text(json.dumps({
                "version": "PBK_STAGE80_INTERNATIONAL_DUTY_PLAYER_EVIDENCE_BACKLOG_V1",
                "status": "OK",
                "backlog_rows": 2,
                "configured_windows": 39,
                "duplicate_backlog_fixture_ids": 0,
                "invalid_backlog_rows": 0,
                "final_tournaments_included": False,
                "outside_fixed_window_fixtures_queued": False,
                "appearance_inference_allowed": False,
                "provider_calls": 0,
                "research_only": True,
                "operational_betting_authority": False,
            }), encoding="utf-8")

            calls = []
            def fake_get(path, params=None, **kwargs):
                calls.append((path, dict(params or {}), dict(kwargs)))
                if path == "/fixtures/players":
                    return players_payload()
                if path == "/fixtures/lineups":
                    return lineups_payload()
                raise AssertionError(path)

            meta = c.run(
                backlog_path=backlog_path,
                backlog_meta_path=backlog_meta_path,
                evidence_path=evidence_path,
                meta_path=meta_path,
                shared_state_path=shared_path,
                get=fake_get,
                now=datetime(2026, 9, 19, 15, 0, tzinfo=timezone.utc),
                max_calls=2,
            )

            self.assertEqual(meta["status"], "OK")
            self.assertEqual(meta["provider_budget_calls"], 2)
            self.assertEqual(meta["captured_fixtures_total"], 2)
            self.assertEqual(meta["pending_or_retry_fixtures"], 0)
            self.assertEqual(meta["attempt_result_counts"], {"CAPTURED": 2})
            self.assertEqual(meta["evidence_rows"], 7)
            self.assertEqual(meta["evidence_fixture_count"], 2)
            self.assertEqual(meta["duplicate_evidence_rows"], 0)
            self.assertEqual(meta["invalid_evidence_rows"], 0)
            self.assertEqual(meta["formal_callup_rows_confirmed"], 0)
            self.assertEqual(meta["travel_rows_derived"], 0)
            self.assertFalse(meta["formal_callup_separately_verified"])
            self.assertFalse(meta["lineup_listing_implies_appearance"])
            self.assertFalse(meta["player_stats_starter_inference_allowed"])
            self.assertFalse(meta["player_stats_substitute_listing_inference_allowed"])
            self.assertEqual(
                meta["candidate_order"],
                "LINEUP_EXPLORATION_THEN_CELL_YIELD_CLASS_THEN_TIER_THEN_RECENCY",
            )
            self.assertEqual([x[0] for x in calls], ["/fixtures/players", "/fixtures/lineups"])

            saved_backlog = c.read_csv(backlog_path)
            self.assertEqual({r["backlog_status"] for r in saved_backlog}, {"CAPTURED"})
            evidence = c.read_csv(evidence_path)
            self.assertEqual(len(evidence), 7)
            self.assertTrue(all(r["formal_callup_status"] == "NOT_SEPARATELY_VERIFIED" for r in evidence))
            self.assertTrue(all(r["travel_status"] == "NOT_DERIVED" for r in evidence))


if __name__ == "__main__":
    unittest.main()
