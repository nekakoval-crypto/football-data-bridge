import json
import unittest

from scripts.point14_in_tenure_xi_composition_v20 import (
    audit_team,
    conservative_in_tenure,
)


def tenure():
    return {
        "team_id": "33",
        "team_name": "Team",
        "coach_name": "Coach",
        "valid_from_utc": "2026-01-13",
        "valid_to_utc": "",
        "effective_precision": "DATE",
        "temporal_authority": "HISTORICAL_VERIFIED",
    }


def xi(ids):
    return json.dumps([
        {"id": str(pid), "name": f"P{pid}", "pos": "M"}
        for pid in ids
    ])


def row(fixture, kickoff, ids, formation="4-2-3-1", retrieved="2026-09-27T00:00:00Z"):
    return {
        "team_id": "33",
        "fixture_id": str(fixture),
        "kickoff_utc": kickoff,
        "home_team": "Team",
        "away_team": "Opp",
        "formation": formation,
        "starting_xi_count": "11",
        "starting_xi_json": xi(ids),
        "retrieved_at_utc": retrieved,
        "coach_name": "Retrospective Coach",
        "temporal_authority": "RETROSPECTIVE_ONLY",
    }


class TestV20XiComposition(unittest.TestCase):
    def test_date_boundary_excluded(self):
        self.assertFalse(
            conservative_in_tenure("2026-01-13T20:00:00+00:00", tenure())
        )
        self.assertTrue(
            conservative_in_tenure("2026-01-14T20:00:00+00:00", tenure())
        )

    def test_four_fixtures_are_preliminary(self):
        base = list(range(1, 12))
        rows = [
            row(i, f"2026-01-{14+i:02d}T20:00:00+00:00", base)
            for i in range(4)
        ]
        result = audit_team(tenure(), rows)
        self.assertEqual(result["evidence_status"], "CURRENT_XI_EVIDENCE_PRELIMINARY")

    def test_five_fixtures_are_analyzable(self):
        base = list(range(1, 12))
        rows = [
            row(i, f"2026-01-{14+i:02d}T20:00:00+00:00", base)
            for i in range(5)
        ]
        result = audit_team(tenure(), rows)
        self.assertEqual(result["evidence_status"], "CURRENT_XI_EVIDENCE_ANALYZABLE")
        self.assertEqual(len([p for p in result["players"] if p["ever_present"]]), 11)

    def test_core_threshold_is_sixty_percent(self):
        common = list(range(1, 11))
        rows = []
        for i in range(5):
            ids = common + [11 if i < 3 else 12]
            rows.append(row(i, f"2026-02-{i+1:02d}T20:00:00+00:00", ids))
        result = audit_team(tenure(), rows)
        p11 = next(p for p in result["players"] if p["player_id"] == "11")
        p12 = next(p for p in result["players"] if p["player_id"] == "12")
        self.assertTrue(p11["core_60pct"])
        self.assertFalse(p12["core_60pct"])
        self.assertEqual(result["core_threshold_starts"], 3)

    def test_consecutive_overlap_counts_changes(self):
        a = list(range(1, 12))
        b = list(range(1, 10)) + [12, 13]
        rows = [
            row("1", "2026-02-01T20:00:00+00:00", a),
            row("2", "2026-02-08T20:00:00+00:00", b),
        ]
        result = audit_team(tenure(), rows)
        transition = result["consecutive_lineup_overlap"]["transitions"][0]
        self.assertEqual(transition["shared_starters"], 9)
        self.assertEqual(transition["starter_changes"], 2)

    def test_duplicate_fixture_keeps_latest_retrieval(self):
        old = row("1", "2026-02-01T20:00:00+00:00", list(range(1, 12)), retrieved="2026-09-20T00:00:00Z")
        new = row("1", "2026-02-01T20:00:00+00:00", list(range(2, 13)), retrieved="2026-09-21T00:00:00Z")
        result = audit_team(tenure(), [old, new])
        self.assertEqual(result["distinct_complete_fixtures"], 1)
        self.assertIn("12", result["fixtures"][0]["starter_ids"])
        self.assertNotIn("1", result["fixtures"][0]["starter_ids"])


if __name__ == "__main__":
    unittest.main()
