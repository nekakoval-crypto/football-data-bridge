import unittest

from scripts.stage86_team_style_operational_normalization import (
    POPULATION_SOURCE_VERSION,
    normalize_row,
    select_forward_candidates,
    valid_source_row,
)


class Stage91NormalizationFromDurableHistoryTests(unittest.TestCase):

    def population_row(
        self,
        *,
        team_id,
        profile_before_utc,
        value,
        version=POPULATION_SOURCE_VERSION,
    ):
        return {
            "version": version,
            "source_version": (
                "PBK_STAGE84_TEAM_STYLE_METRIC_OBSERVATIONS_V1"
            ),
            "league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "team_id": str(team_id),
            "team_name": f"Team {team_id}",
            "split": "overall",
            "window": 5,
            "metric": "shots_for",
            "profile_before_utc": profile_before_utc,
            "observed_at_utc": profile_before_utc,
            "value": value,
            "metric_status": "KNOWN",
            "historical_backfill": False,
        }

    def normalized_existing(
        self,
        *,
        team_id,
        profile_before_utc,
    ):
        return {
            "version": (
                "PBK_STAGE86_OPERATIONAL_NORMALIZED_STYLE_METRICS_V1"
            ),
            "league_id": "39",
            "season": "2026",
            "team_id": str(team_id),
            "split": "overall",
            "window": 5,
            "metric": "shots_for",
            "profile_before_utc": profile_before_utc,
        }

    def test_accepts_stage90_population_rows_only(self):
        valid = self.population_row(
            team_id=1,
            profile_before_utc="2026-09-17T10:00:00Z",
            value=10.0,
        )

        wrong_version = self.population_row(
            team_id=2,
            profile_before_utc="2026-09-17T10:00:00Z",
            value=11.0,
            version="PBK_STAGE84_TEAM_STYLE_METRIC_OBSERVATIONS_V1",
        )

        self.assertTrue(valid_source_row(valid))
        self.assertFalse(valid_source_row(wrong_version))

        selected = select_forward_candidates(
            [valid, wrong_version],
            [],
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(
            selected[0]["team_id"],
            "1",
        )

    def test_existing_normalized_observation_is_not_selected_again(self):
        source = [
            self.population_row(
                team_id=1,
                profile_before_utc="2026-09-17T10:00:00Z",
                value=10.0,
            ),
            self.population_row(
                team_id=1,
                profile_before_utc="2026-09-18T10:00:00Z",
                value=11.0,
            ),
        ]

        existing = [
            self.normalized_existing(
                team_id=1,
                profile_before_utc="2026-09-17T10:00:00Z",
            )
        ]

        selected = select_forward_candidates(
            source,
            existing,
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(
            selected[0]["profile_before_utc"],
            "2026-09-18T10:00:00Z",
        )

    def test_normalization_uses_durable_history_population(self):
        source = []

        for team_number in range(1, 31):
            source.append(
                self.population_row(
                    team_id=team_number,
                    profile_before_utc="2026-09-17T10:00:00Z",
                    value=float(team_number),
                )
            )

        target = source[-1]

        result = normalize_row(
            target,
            source,
        )

        self.assertEqual(
            result["population_source_version"],
            POPULATION_SOURCE_VERSION,
        )
        self.assertEqual(
            result["normalization_status"],
            "NORMALIZED",
        )
        self.assertEqual(
            result["population_n"],
            30,
        )
        self.assertIsNotNone(
            result["percentile"]
        )
        self.assertIsNotNone(
            result["z_score"]
        )


if __name__ == "__main__":
    unittest.main()
