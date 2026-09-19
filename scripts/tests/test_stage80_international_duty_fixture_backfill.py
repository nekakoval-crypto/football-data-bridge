import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import stage80_international_duty_fixture_backfill as b


def allow_row(i, tier="DIRECT_MINUTES", priority="1", season="2024"):
    return {
        "provider_league_id": str(1000 + i),
        "competition_name": f"National Competition {i}",
        "competition_type": "Cup",
        "provider_country_name": "World",
        "provider_country_code": "",
        "candidate_family": "TEST_FAMILY",
        "season": str(season),
        "season_start": "2024-01-01",
        "season_end": "2024-12-31",
        "current_season": "false",
        "coverage_events": "true",
        "coverage_lineups": "true",
        "coverage_fixture_statistics": "true",
        "coverage_player_statistics": "true" if tier == "DIRECT_MINUTES" else "false",
        "coverage_players": "true",
        "coverage_injuries": "false",
        "direct_matchday_squad_evidence_possible": "true" if tier != "FIXTURE_ONLY" else "false",
        "direct_minutes_evidence_possible": "true" if tier == "DIRECT_MINUTES" else "false",
        "evidence_tier": tier,
        "player_evidence_backfill_eligible": "true" if tier != "FIXTURE_ONLY" else "false",
        "fixture_backfill_priority": priority,
        "pbk_source_selection_status": "EXPLICIT_ALLOWLIST",
        "pbk_source_selection_reason": "TEST",
        "historical_callup_evidence_possible": "false",
        "nationality_inference_allowed": "false",
        "future_fixture_backfill_required": "true",
        "research_only": "true",
        "operational_betting_authority": "false",
        "creates_signal": "false",
        "probability_mutation": "false",
        "eligibility_mutation": "false",
        "stake_changes": "false",
        "forward_journal_mutation": "false",
    }


def payload(league_id, season, fixture_id, status="FT"):
    return {
        "errors": [],
        "paging": {"current": 1, "total": 1},
        "response": [{
            "fixture": {
                "id": fixture_id,
                "date": "2024-09-10T18:45:00+00:00",
                "status": {"short": status, "elapsed": 90 if status == "FT" else None},
                "venue": {"id": 1, "name": "National Stadium", "city": "Capital"},
            },
            "league": {
                "id": int(league_id),
                "name": f"National Competition {int(league_id)-1000}",
                "season": int(season),
                "round": "Group Stage - 1",
            },
            "teams": {
                "home": {"id": 11, "name": "Country A"},
                "away": {"id": 22, "name": "Country B"},
            },
            "goals": {"home": 2, "away": 1},
        }],
    }


def write_csv(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class InternationalDutyFixtureBackfillTests(unittest.TestCase):
    def test_validate_allowlist_and_priority_order(self):
        rows = [
            allow_row(1, "FIXTURE_ONLY", "9", "2025"),
            allow_row(2, "DIRECT_MATCHDAY_SQUAD", "2", "2024"),
            allow_row(3, "DIRECT_MINUTES", "1", "2023"),
            allow_row(4, "DIRECT_MINUTES", "1", "2025"),
        ]
        valid, invalid = b.validate_allowlist(rows)
        self.assertEqual(invalid, [])
        self.assertEqual(
            [(r["provider_league_id"], r["season"]) for r in valid],
            [("1004", "2025"), ("1003", "2023"), ("1002", "2024"), ("1001", "2025")],
        )

    def test_invalid_authority_or_callup_claim_is_rejected(self):
        row = allow_row(1)
        row["historical_callup_evidence_possible"] = "true"
        valid, invalid = b.validate_allowlist([row])
        self.assertEqual(valid, [])
        self.assertEqual(len(invalid), 1)

    def test_state_preserves_captured_cells(self):
        specs = [allow_row(1), allow_row(2)]
        existing = [{
            "provider_league_id": "1001",
            "season": "2024",
            "status": "CAPTURED",
            "attempt_count": "1",
            "fixture_rows": "3",
        }]
        state = b.state_rows_for_allowlist(specs, existing)
        by = {b.cell_key(r): r for r in state}
        self.assertEqual(by[("1001", "2024")]["status"], "CAPTURED")
        self.assertEqual(by[("1001", "2024")]["fixture_rows"], "3")
        self.assertEqual(by[("1002", "2024")]["status"], "PENDING")

    def test_normalize_preserves_source_tier_without_player_inference(self):
        spec = allow_row(1)
        rows = b.normalize_payload(
            payload("1001", "2024", 501),
            spec,
            "2026-09-19T12:00:00Z",
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["fixture_id"], "501")
        self.assertEqual(row["result"], "H")
        self.assertEqual(row["evidence_tier"], "DIRECT_MINUTES")
        self.assertEqual(row["historical_callup_evidence_possible"], "false")
        self.assertEqual(row["nationality_inference_allowed"], "false")
        self.assertEqual(row["operational_betting_authority"], "false")
        self.assertEqual(row["creates_signal"], "false")

    def test_normalize_rejects_provider_cell_drift(self):
        spec = allow_row(1)
        with self.assertRaises(ValueError):
            b.normalize_payload(
                payload("9999", "2024", 501),
                spec,
                "2026-09-19T12:00:00Z",
            )

    def test_merge_archive_rejects_cross_competition_fixture_collision(self):
        old = [{
            "fixture_id": "501",
            "provider_league_id": "1001",
            "season": "2024",
            "kickoff_utc": "2024-01-01T00:00:00Z",
        }]
        new = [{
            "fixture_id": "501",
            "provider_league_id": "1002",
            "season": "2024",
            "kickoff_utc": "2024-01-01T00:00:00Z",
        }]
        with self.assertRaises(ValueError):
            b.merge_archive(old, new)

    def test_run_is_resumable_and_honors_two_call_budget(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rows = [allow_row(i) for i in range(80)]
            allow_path = root / "allow.csv"
            archive_path = root / "archive.csv"
            state_path = root / "state.csv"
            meta_path = root / "meta.json"
            shared_path = root / "shared.json"
            write_csv(allow_path, rows)

            calls = []
            def fake_get(path, params=None, **kwargs):
                calls.append((path, dict(params or {}), dict(kwargs)))
                lid = str(params["league"])
                season = str(params["season"])
                return payload(lid, season, 900000 + int(lid))

            meta = b.run(
                allowlist_path=allow_path,
                archive_path=archive_path,
                state_path=state_path,
                meta_path=meta_path,
                shared_state_path=shared_path,
                get=fake_get,
                now=datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
                max_calls=2,
            )

            self.assertEqual(meta["status"], "COLLECTING")
            self.assertEqual(meta["allowlist_rows"], 80)
            self.assertEqual(meta["state_rows"], 80)
            self.assertEqual(meta["captured_cells"], 2)
            self.assertEqual(meta["pending_cells"], 78)
            self.assertEqual(meta["error_cells"], 0)
            self.assertEqual(meta["provider_budget_calls"], 2)
            self.assertEqual(meta["fixture_archive_rows"], 2)
            self.assertEqual(meta["unique_fixture_ids"], 2)
            self.assertEqual(meta["duplicate_fixture_ids"], 0)
            self.assertEqual(meta["invalid_archive_rows"], 0)
            self.assertEqual(meta["finished_fixture_rows"], 2)
            self.assertFalse(meta["historical_callup_evidence_possible"])
            self.assertFalse(meta["player_appearance_or_minutes_inferred"])
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(call[0] == "/fixtures" for call in calls))

            state = b.read_csv(state_path)
            self.assertEqual(sum(r["status"] == "CAPTURED" for r in state), 2)
            self.assertEqual(sum(r["status"] == "PENDING" for r in state), 78)

            # Second run skips captured cells and captures the next one only.
            meta2 = b.run(
                allowlist_path=allow_path,
                archive_path=archive_path,
                state_path=state_path,
                meta_path=meta_path,
                shared_state_path=shared_path,
                get=fake_get,
                now=datetime(2026, 9, 19, 12, 5, tzinfo=timezone.utc),
                max_calls=1,
            )
            self.assertEqual(meta2["captured_cells"], 3)
            self.assertEqual(meta2["pending_cells"], 77)
            self.assertEqual(meta2["fixture_archive_rows"], 3)
            self.assertEqual(len(calls), 3)

    def test_run_requires_exact_eighty_allowlisted_cells(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rows = [allow_row(i) for i in range(79)]
            allow_path = root / "allow.csv"
            write_csv(allow_path, rows)
            with self.assertRaises(ValueError):
                b.run(
                    allowlist_path=allow_path,
                    archive_path=root / "archive.csv",
                    state_path=root / "state.csv",
                    meta_path=root / "meta.json",
                    shared_state_path=root / "shared.json",
                    get=lambda *a, **k: {},
                    max_calls=1,
                )


if __name__ == "__main__":
    unittest.main()
