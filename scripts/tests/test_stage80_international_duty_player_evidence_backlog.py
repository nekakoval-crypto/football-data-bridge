import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import stage80_international_duty_player_evidence_backlog as q


def fixture(fid, kickoff, tier="DIRECT_MINUTES", status="FT", eligible="true"):
    return {
        "fixture_id": str(fid),
        "provider_league_id": "5",
        "competition_name": "UEFA Nations League",
        "candidate_family": "NATIONS_LEAGUE",
        "season": "2024",
        "round": "League A - 1",
        "kickoff_utc": kickoff,
        "status": status,
        "elapsed": "90",
        "home_team_id": "100",
        "home_team": "Country A",
        "away_team_id": "200",
        "away_team": "Country B",
        "home_goals": "1",
        "away_goals": "0",
        "result": "H",
        "evidence_tier": tier,
        "direct_matchday_squad_evidence_possible": "true" if tier != "FIXTURE_ONLY" else "false",
        "direct_minutes_evidence_possible": "true" if tier == "DIRECT_MINUTES" else "false",
        "player_evidence_backfill_eligible": eligible,
        "captured_at_utc": "2026-09-19T14:00:00Z",
        "source": "API-Football /fixtures?league&season",
        "historical_callup_evidence_possible": "false",
        "nationality_inference_allowed": "false",
        "historical_backfill_only": "true",
        "research_only": "true",
        "operational_betting_authority": "false",
        "creates_signal": "false",
        "probability_mutation": "false",
        "eligibility_mutation": "false",
        "stake_changes": "false",
        "forward_journal_mutation": "false",
    }


def write_csv(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class InternationalDutyPlayerEvidenceBacklogTests(unittest.TestCase):
    def setUp(self):
        _, self.windows = q.iw.load_config(q.CONFIG)

    def test_minutes_and_lineup_endpoints_are_separate(self):
        rows = [
            fixture(1, "2024-03-20T18:00:00Z", "DIRECT_MINUTES"),
            fixture(2, "2024-03-21T18:00:00Z", "DIRECT_MATCHDAY_SQUAD"),
        ]
        backlog, diag = q.build_backlog(
            rows, [], self.windows,
            now=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(diag["backlog_rows"], 2)
        by = {r["fixture_id"]: r for r in backlog}
        self.assertEqual(by["1"]["capture_endpoint"], "/fixtures/players")
        self.assertEqual(by["1"]["capture_priority"], "1")
        self.assertEqual(by["2"]["capture_endpoint"], "/fixtures/lineups")
        self.assertEqual(by["2"]["capture_priority"], "2")
        self.assertEqual(by["1"]["window_id"], "2024_MAR")
        self.assertEqual(by["2"]["window_id"], "2024_MAR")
        self.assertEqual(by["1"]["callup_inference_allowed"], "false")
        self.assertEqual(by["1"]["appearance_inference_allowed"], "false")

    def test_outside_window_nonfinal_and_fixture_only_are_not_queued(self):
        rows = [
            fixture(1, "2024-04-20T18:00:00Z", "DIRECT_MINUTES"),
            fixture(2, "2024-03-20T18:00:00Z", "DIRECT_MINUTES", status="NS"),
            fixture(3, "2024-03-20T18:00:00Z", "FIXTURE_ONLY", eligible="false"),
        ]
        backlog, diag = q.build_backlog(rows, [], self.windows)
        self.assertEqual(backlog, [])
        self.assertEqual(diag["outside_window_finished_player_evidence_eligible_rows"], 1)
        self.assertEqual(diag["backlog_rows"], 0)

    def test_existing_capture_state_is_preserved(self):
        source = [fixture(1, "2024-03-20T18:00:00Z")]
        existing = [{
            "fixture_id": "1",
            "backlog_status": "CAPTURED",
            "captured_at_utc": "2026-09-19T13:00:00Z",
            "attempt_count": "1",
            "last_attempt_at_utc": "2026-09-19T13:00:00Z",
            "last_attempt_result": "CAPTURED",
        }]
        backlog, _ = q.build_backlog(source, existing, self.windows)
        self.assertEqual(backlog[0]["backlog_status"], "CAPTURED")
        self.assertEqual(backlog[0]["captured_at_utc"], "2026-09-19T13:00:00Z")
        self.assertEqual(backlog[0]["attempt_count"], "1")

    def test_duplicate_source_fixture_id_fails_closed(self):
        rows = [
            fixture(1, "2024-03-20T18:00:00Z"),
            fixture(1, "2024-03-21T18:00:00Z"),
        ]
        with self.assertRaises(ValueError):
            q.build_backlog(rows, [], self.windows)

    def test_invalid_evidence_governance_is_not_queued_and_counted(self):
        row = fixture(1, "2024-03-20T18:00:00Z")
        row["appearance_inference_allowed"] = "true"
        # Source archive has no such field, so flip an actual source contract.
        row["historical_callup_evidence_possible"] = "true"
        backlog, diag = q.build_backlog([row], [], self.windows)
        self.assertEqual(backlog, [])
        self.assertEqual(diag["invalid_source_rows"], 1)

    def test_run_validates_completed_fixture_archive_and_materializes_queue(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixtures_path = root / "fixtures.csv"
            fixture_meta_path = root / "fixture_meta.json"
            backlog_path = root / "backlog.csv"
            meta_path = root / "meta.json"

            rows = [
                fixture(1, "2024-03-20T18:00:00Z", "DIRECT_MINUTES"),
                fixture(2, "2024-03-21T18:00:00Z", "DIRECT_MATCHDAY_SQUAD"),
                fixture(3, "2024-04-20T18:00:00Z", "DIRECT_MINUTES"),
                fixture(4, "2024-03-22T18:00:00Z", "FIXTURE_ONLY", eligible="false"),
            ]
            write_csv(fixtures_path, rows)
            fixture_meta_path.write_text(json.dumps({
                "version": "PBK_STAGE80_INTERNATIONAL_DUTY_FIXTURE_BACKFILL_V1",
                "status": "OK",
                "allowlist_rows": 80,
                "state_rows": 80,
                "captured_cells": 80,
                "pending_cells": 0,
                "error_cells": 0,
                "fixture_archive_rows": 4,
                "unique_fixture_ids": 4,
                "duplicate_fixture_ids": 0,
                "invalid_archive_rows": 0,
                "historical_callup_evidence_possible": False,
                "nationality_inference_allowed": False,
                "player_appearance_or_minutes_inferred": False,
                "provider_fixture_history_only": True,
                "research_only": True,
                "operational_betting_authority": False,
            }), encoding="utf-8")

            meta = q.run(
                fixtures_path=fixtures_path,
                fixture_meta_path=fixture_meta_path,
                config_path=q.CONFIG,
                backlog_path=backlog_path,
                meta_path=meta_path,
                now=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
            )
            self.assertEqual(meta["status"], "OK")
            self.assertEqual(meta["backlog_rows"], 2)
            self.assertEqual(meta["configured_windows"], 39)
            self.assertEqual(meta["backlog_window_count"], 1)
            self.assertEqual(meta["capture_endpoint_counts"]["/fixtures/players"], 1)
            self.assertEqual(meta["capture_endpoint_counts"]["/fixtures/lineups"], 1)
            self.assertEqual(meta["outside_window_finished_player_evidence_eligible_rows"], 1)
            self.assertFalse(meta["final_tournaments_included"])
            self.assertFalse(meta["outside_fixed_window_fixtures_queued"])
            self.assertFalse(meta["appearance_inference_allowed"])
            self.assertEqual(meta["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
