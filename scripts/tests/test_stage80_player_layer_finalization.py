import json
import unittest
from datetime import datetime, timezone

from scripts import stage80_player_layer_finalization as p


class PlayerLayerFinalizationTests(unittest.TestCase):

    def xi(self, ids):
        return json.dumps([
            {"player": {"id": str(i), "name": f"P{i}"}} for i in ids
        ])

    def test_fixture_outcomes_supports_canonical_pbk16_archive_schema(self):
        outcomes = p.fixture_outcomes([{
            "fixture_id": "1382426",
            "status": "FT",
            "home_goals": "2",
            "away_goals": "1",
        }])
        self.assertEqual(outcomes["1382426"]["home_points"], 3)
        self.assertEqual(outcomes["1382426"]["away_points"], 0)
        self.assertEqual(outcomes["1382426"]["home_gd"], 1.0)

    def test_fixture_outcomes_rejects_nonterminal_rows(self):
        outcomes = p.fixture_outcomes([{
            "fixture_id": "1382426",
            "status": "NS",
            "home_goals": "2",
            "away_goals": "1",
        }])
        self.assertNotIn("1382426", outcomes)

    def test_prior_grade_excludes_target_and_future_match(self):
        histories = {
            "7": [
                (datetime(2026, 1, 1, tzinfo=timezone.utc), 6.0, 90.0, "1"),
                (datetime(2026, 1, 8, tzinfo=timezone.utc), 7.0, 90.0, "2"),
                (datetime(2026, 1, 15, tzinfo=timezone.utc), 10.0, 90.0, "3"),
            ]
        }
        value, sample = p.prior_grade(
            "7", datetime(2026, 1, 15, tzinfo=timezone.utc), histories
        )
        self.assertEqual(value, 6.5)
        self.assertEqual(sample, 2)

    def test_importance_uses_only_captured_with_without_samples(self):
        lineups = {"10": []}
        outcomes = {}
        for i in range(10):
            fid = str(i + 1)
            starters = list(range(1, 12)) if i < 5 else list(range(2, 13))
            lineups["10"].append({
                "fixture_id": fid,
                "kickoff_utc": f"2026-01-{i+1:02d}T12:00:00Z",
                "kickoff_dt": datetime(2026, 1, i + 1, 12, tzinfo=timezone.utc),
                "team_id": "10",
                "team_name": "Team",
                "side": "HOME",
                "xi": [{"player_id": str(x), "player_name": f"P{x}"} for x in starters],
            })
            outcomes[fid] = {
                "home_points": 3 if i < 5 else 0,
                "away_points": 0 if i < 5 else 3,
                "home_gd": 1 if i < 5 else -1,
                "away_gd": -1 if i < 5 else 1,
            }
        rows = p.build_importance(lineups, outcomes, {}, {}, min_with=5, min_without=5)
        player1 = next(row for row in rows if row["player_id"] == "1")
        self.assertEqual(player1["eligible"], "true")
        self.assertGreater(float(player1["importance_score"]), 0)
        self.assertEqual(player1["research_only"], "true")

    def test_xi_quality_uses_same_target_cutoff_for_both_memberships(self):
        cutoff1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        cutoff2 = datetime(2026, 1, 8, tzinfo=timezone.utc)
        histories = {}
        for i in range(1, 13):
            histories[str(i)] = [
                (datetime(2025, 12, 20, tzinfo=timezone.utc), float(i), 90.0, "old")
            ]
        lineups = {"10": [
            {
                "fixture_id": "1", "kickoff_utc": cutoff1.isoformat(),
                "kickoff_dt": cutoff1, "team_id": "10", "team_name": "T",
                "side": "HOME",
                "xi": [{"player_id": str(i), "player_name": ""} for i in range(1, 12)],
            },
            {
                "fixture_id": "2", "kickoff_utc": cutoff2.isoformat(),
                "kickoff_dt": cutoff2, "team_id": "10", "team_name": "T",
                "side": "HOME",
                "xi": [{"player_id": str(i), "player_name": ""} for i in range(2, 13)],
            },
        ]}
        rows = p.build_xi_quality(lineups, histories)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["covered_players"], 11)
        self.assertEqual(rows[0]["previous_covered_players"], 11)
        self.assertGreater(float(rows[0]["quality_delta_vs_previous_membership"]), 0)
        self.assertEqual(rows[0]["temporal_authority"], "RETROSPECTIVE_CHRONOLOGY_ONLY")

    def test_availability_never_claims_prematch_authority(self):
        injuries = [{
            "fixture_id": "1", "kickoff_utc": "2026-01-10T12:00:00Z",
            "home_team": "T", "away_team": "O", "team_id": "10",
            "team_name": "T", "player_id": "7", "player_name": "P",
            "reason": "injury", "retrieved_at_utc": "2026-09-01T00:00:00Z",
        }]
        outcomes = {"1": {
            "home_points": 3, "away_points": 0, "home_gd": 1, "away_gd": -1,
        }}
        rows = p.build_availability_validation(injuries, outcomes, [], {})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["temporal_authority"], "RETROSPECTIVE_ONLY")
        self.assertEqual(rows[0]["prematch_observation_time_known"], "NO")
        self.assertEqual(rows[0]["validation_authority"], "DESCRIPTIVE_ASSOCIATION_ONLY")

    def test_final_readiness_never_authorizes_betting(self):
        r = p.build_readiness(
            importance_rows=[{"eligible": "true"}],
            xi_rows=[{"quality_status": "RESEARCH_COMPONENT"}],
            rotation_rows=[{"x": 1}],
            availability_rows=[{"x": 1}],
            return_rows=[{"x": 1}],
            form_rows=[{"x": 1}],
            international_rows=[{"x": 1}],
            player_meta={"remaining_unattempted_or_retryable": 10},
            availability_meta={"remaining_candidate_tasks": 20},
        )
        self.assertEqual(r["checklist_item_10_data_engineering_foundation"], "COMPLETE")
        self.assertEqual(r["checklist_item_10_predictive_authority"], "NOT_AUTHORIZED")
        self.assertFalse(r["operational_betting_authority"])
        self.assertIn("HISTORICAL_PLAYER_BACKFILL_INCOMPLETE", r["hard_blockers"])
        self.assertIn("HISTORICAL_LINEUP_INJURY_BACKFILL_INCOMPLETE", r["hard_blockers"])


if __name__ == "__main__":
    unittest.main()
