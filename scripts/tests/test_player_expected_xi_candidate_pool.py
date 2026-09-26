import json
import unittest

from scripts.player_expected_xi_candidate_pool import (
    availability_events_by_player,
    build_candidate_pool,
    documented_slot_from_grid,
    latest_roster_for_team,
)


class Point14CandidatePoolTests(unittest.TestCase):

    def test_latest_roster_snapshot_only(self):

        rows = [
            {
                "team_id": "100",
                "captured_at_utc":
                    "2026-10-01T10:00:00Z",
                "player_id": "1",
            },
            {
                "team_id": "100",
                "captured_at_utc":
                    "2026-10-05T10:00:00Z",
                "player_id": "2",
            },
        ]

        result = latest_roster_for_team(
            rows,
            team_id="100",
            before_utc="2026-10-10T10:00:00Z",
        )

        self.assertEqual(
            [
                row["player_id"]
                for row in result
            ],
            ["2"],
        )

    def test_grid_maps_four_back(self):

        self.assertEqual(
            documented_slot_from_grid(
                "4-3-3",
                "2:4",
            ),
            "RB",
        )

        self.assertEqual(
            documented_slot_from_grid(
                "4-3-3",
                "2:3",
            ),
            "CB",
        )

        self.assertEqual(
            documented_slot_from_grid(
                "4-3-3",
                "2:1",
            ),
            "LB",
        )

    def test_grid_maps_4231_attack(self):

        self.assertEqual(
            documented_slot_from_grid(
                "4-2-3-1",
                "4:3",
            ),
            "RW",
        )

        self.assertEqual(
            documented_slot_from_grid(
                "4-2-3-1",
                "4:2",
            ),
            "AM",
        )

        self.assertEqual(
            documented_slot_from_grid(
                "4-2-3-1",
                "5:1",
            ),
            "ST",
        )

    def test_questionable_journal_is_not_hard_out(self):

        availability = [
            {
                "team_id": "100",
                "player_id": "1",
                "state": "ABSENT",
                "availability_type":
                    "Questionable",
                "reason": "Muscle Injury",
                "observed_at_utc":
                    "2026-10-09T10:00:00Z",
                "source": "TEST",
            }
        ]

        grouped = (
            availability_events_by_player(
                availability,
                [],
                team_id="100",
                before_utc=(
                    "2026-10-10T10:00:00Z"
                ),
            )
        )

        self.assertEqual(
            grouped["1"][0]["status"],
            "QUESTIONABLE",
        )

    def test_discipline_ledger_is_preserved(self):

        discipline = [
            {
                "team_id": "100",
                "player_id": "1",
                "event_type": "APPEAL",
                "status":
                    "SUSPENSION_OVERTURNED",
                "competition_scope":
                    "SERIE A",
                "observed_at_utc":
                    "2026-10-09T10:00:00Z",
                "source": "TEST",
            }
        ]

        grouped = (
            availability_events_by_player(
                [],
                discipline,
                team_id="100",
                before_utc=(
                    "2026-10-10T10:00:00Z"
                ),
            )
        )

        event = grouped["1"][0]

        self.assertEqual(
            event["event_type"],
            "APPEAL",
        )

        self.assertEqual(
            event["status"],
            "SUSPENSION_OVERTURNED",
        )

    def test_candidate_pool_uses_prior_lineups_and_grades(self):

        roster = [
            {
                "team_id": "100",
                "team_name": "Test FC",
                "captured_at_utc":
                    "2026-10-09T08:00:00Z",
                "player_id": "1",
                "player_name":
                    "Natural CB",
                "position": "Defender",
            }
        ]

        lineup = [
            {
                "fixture_id": "900",
                "team_id": "100",
                "kickoff_utc":
                    "2026-10-01T18:00:00Z",
                "captured_at_utc":
                    "2026-10-01T17:00:00Z",
                "formation": "4-3-3",
                "starting_xi_json":
                    json.dumps([
                        {
                            "id": "1",
                            "name":
                                "Natural CB",
                            "pos": "D",
                            "grid": "2:3",
                        }
                    ]),
            }
        ]

        grades = [
            {
                "fixture_id": "900",
                "team_id": "100",
                "kickoff_utc":
                    "2026-10-01T18:00:00Z",
                "player_id": "1",
                "minutes": "90",
                "overall_grade": "7.1",
            }
        ]

        result = build_candidate_pool(
            team_id="100",
            before_utc="2026-10-10T18:00:00Z",
            roster_rows=roster,
            lineup_rows=lineup,
            grade_rows=grades,
            availability_rows=[],
            discipline_rows=[],
        )

        self.assertEqual(
            result["status"],
            "OK",
        )

        player = (
            result["candidates"][0]
        )

        self.assertIn(
            "CB",
            player["documented_positions"],
        )

        self.assertEqual(
            player["starts_last_5"],
            1,
        )

        self.assertEqual(
            player["minutes_last_5"],
            90.0,
        )

        self.assertEqual(
            player["form_5"],
            7.1,
        )

    def test_future_roster_is_not_used(self):

        roster = [
            {
                "team_id": "100",
                "captured_at_utc":
                    "2026-10-11T08:00:00Z",
                "player_id": "1",
                "player_name":
                    "Future Player",
                "position": "Defender",
            }
        ]

        result = build_candidate_pool(
            team_id="100",
            before_utc="2026-10-10T18:00:00Z",
            roster_rows=roster,
            lineup_rows=[],
            grade_rows=[],
            availability_rows=[],
            discipline_rows=[],
        )

        self.assertEqual(
            result["status"],
            "NO_CURRENT_ROSTER_EVIDENCE",
        )


if __name__ == "__main__":
    unittest.main()
