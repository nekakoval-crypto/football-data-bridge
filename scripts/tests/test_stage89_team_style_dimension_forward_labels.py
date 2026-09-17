import unittest

from scripts.stage89_team_style_dimension_forward_labels import (
    build_forward_labels,
)


class Stage89TeamStyleDimensionForwardLabelsTests(unittest.TestCase):

    def observation(self):
        return {
            "version": "PBK_STAGE88_STYLE_DIMENSION_VALIDATION_DATASET_V1",
            "league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "team_id": "1",
            "split": "overall",
            "window": 5,
            "dimension": "ATTACK_VOLUME",
            "profile_before_utc": "2026-09-17T10:00:00Z",
            "observed_at_utc": "2026-09-17T10:01:00Z",
            "validation_status": "UNLABELED_FORWARD_OBSERVATION",
            "validation_result": None,
            "dimension_value": None,
        }

    def stats_row(
        self,
        *,
        fixture_id,
        team_id,
        team_name,
        side,
        shots_total="10",
        shots_on_goal="4",
        expected_goals="1.2",
        corners="5",
    ):
        return {
            "fixture_id": fixture_id,
            "provider_league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "observed_at_utc": "2026-09-18T20:00:00Z",
            "team_id": team_id,
            "team_name": team_name,
            "side": side,
            "shots_total": shots_total,
            "shots_on_goal": shots_on_goal,
            "expected_goals": expected_goals,
            "corners": corners,
            "possession_pct": "55",
            "passes_total": "500",
            "passes_accuracy_pct": "84",
        }

    def backlog_row(
        self,
        *,
        fixture_id,
        kickoff_utc,
    ):
        return {
            "fixture_id": fixture_id,
            "provider_league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "round": "5",
            "kickoff_utc": kickoff_utc,
            "home_team": "Team A",
            "away_team": "Team B",
            "backlog_status": "CAPTURED",
        }

    def test_attaches_first_next_fixture_when_stats_complete(self):
        observations = [self.observation()]

        backlog = [
            self.backlog_row(
                fixture_id="100",
                kickoff_utc="2026-09-18T18:00:00Z",
            )
        ]

        stats = [
            self.stats_row(
                fixture_id="100",
                team_id="1",
                team_name="Team A",
                side="HOME",
            ),
            self.stats_row(
                fixture_id="100",
                team_id="2",
                team_name="Team B",
                side="AWAY",
            ),
        ]

        rows, counters = build_forward_labels(
            observations,
            stats,
            backlog,
            [],
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fixture_id"], "100")
        self.assertEqual(
            rows[0]["label_status"],
            "FORWARD_MATCH_ATTACHED",
        )
        self.assertEqual(counters["labeled"], 1)

    def test_never_skips_first_next_fixture_if_its_stats_missing(self):
        observations = [self.observation()]

        backlog = [
            self.backlog_row(
                fixture_id="100",
                kickoff_utc="2026-09-18T18:00:00Z",
            ),
            self.backlog_row(
                fixture_id="101",
                kickoff_utc="2026-09-22T18:00:00Z",
            ),
        ]

        # Fixture 100 has no stats.
        # Fixture 101 is complete, but must NOT be used.
        stats = [
            self.stats_row(
                fixture_id="101",
                team_id="1",
                team_name="Team A",
                side="HOME",
            ),
            self.stats_row(
                fixture_id="101",
                team_id="2",
                team_name="Team B",
                side="AWAY",
            ),
        ]

        rows, counters = build_forward_labels(
            observations,
            stats,
            backlog,
            [],
        )

        self.assertEqual(rows, [])
        self.assertEqual(
            counters[
                "first_next_fixture_stats_pending"
            ],
            1,
        )
        self.assertEqual(counters["labeled"], 0)

    def test_existing_observation_is_not_labeled_twice(self):
        observation = self.observation()

        existing = [
            {
                **observation,
                "version": "PBK_STAGE89_STYLE_DIMENSION_FORWARD_LABELS_V1",
                "fixture_id": "100",
            }
        ]

        backlog = [
            self.backlog_row(
                fixture_id="100",
                kickoff_utc="2026-09-18T18:00:00Z",
            )
        ]

        stats = [
            self.stats_row(
                fixture_id="100",
                team_id="1",
                team_name="Team A",
                side="HOME",
            ),
            self.stats_row(
                fixture_id="100",
                team_id="2",
                team_name="Team B",
                side="AWAY",
            ),
        ]

        rows, counters = build_forward_labels(
            [observation],
            stats,
            backlog,
            existing,
        )

        self.assertEqual(rows, [])
        self.assertEqual(
            counters["already_labeled"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
