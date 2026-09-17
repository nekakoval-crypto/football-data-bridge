import unittest

from scripts.stage90_team_style_population_history import (
    history_row,
    select_forward_candidates,
)


class Stage90TeamStylePopulationHistoryTests(unittest.TestCase):

    def row(
        self,
        *,
        profile_before_utc,
        value="10.5",
        metric_status="KNOWN",
    ):
        return {
            "schema_version": (
                "PBK_STAGE84_TEAM_STYLE_METRIC_OBSERVATIONS_V1"
            ),
            "source_profile_version": (
                "PBK_STAGE83_TEAM_STYLE_OPERATIONAL_PROFILES_V1"
            ),
            "profile_before_utc": profile_before_utc,
            "observed_at_utc": profile_before_utc,
            "league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "team_id": "1",
            "team_name": "Team A",
            "split": "overall",
            "window": 5,
            "metric": "shots_for",
            "value": value,
            "metric_status": metric_status,
            "sample_size": 5,
            "coverage": 1.0,
            "window_actual_matches": 5,
            "window_complete": True,
        }

    def history_existing(
        self,
        *,
        profile_before_utc,
    ):
        return {
            "version": (
                "PBK_STAGE90_TEAM_STYLE_POPULATION_HISTORY_V1"
            ),
            "source_version": (
                "PBK_STAGE84_TEAM_STYLE_METRIC_OBSERVATIONS_V1"
            ),
            "profile_before_utc": profile_before_utc,
            "observed_at_utc": profile_before_utc,
            "league_id": "39",
            "season": "2026",
            "team_id": "1",
            "split": "overall",
            "window": 5,
            "metric": "shots_for",
        }

    def test_first_seen_series_uses_latest_snapshot_only(self):
        source = [
            self.row(
                profile_before_utc="2026-09-15T10:00:00Z"
            ),
            self.row(
                profile_before_utc="2026-09-16T10:00:00Z"
            ),
            self.row(
                profile_before_utc="2026-09-17T10:00:00Z"
            ),
        ]

        selected = select_forward_candidates(
            source,
            [],
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(
            selected[0]["profile_before_utc"],
            "2026-09-17T10:00:00Z",
        )

    def test_existing_series_only_accepts_newer_than_watermark(self):
        source = [
            self.row(
                profile_before_utc="2026-09-15T10:00:00Z"
            ),
            self.row(
                profile_before_utc="2026-09-16T10:00:00Z"
            ),
            self.row(
                profile_before_utc="2026-09-17T10:00:00Z"
            ),
            self.row(
                profile_before_utc="2026-09-18T10:00:00Z"
            ),
        ]

        existing = [
            self.history_existing(
                profile_before_utc="2026-09-16T10:00:00Z"
            )
        ]

        selected = select_forward_candidates(
            source,
            existing,
        )

        self.assertEqual(len(selected), 2)
        self.assertEqual(
            [
                row["profile_before_utc"]
                for row in selected
            ],
            [
                "2026-09-17T10:00:00Z",
                "2026-09-18T10:00:00Z",
            ],
        )

    def test_unknown_stays_unknown_and_never_zero_filled(self):
        source = self.row(
            profile_before_utc="2026-09-17T10:00:00Z",
            value=None,
            metric_status="UNKNOWN",
        )

        result = history_row(source)

        self.assertEqual(
            result["metric_status"],
            "UNKNOWN",
        )
        self.assertIsNone(result["value"])
        self.assertFalse(
            result["historical_backfill"]
        )
        self.assertEqual(
            result["missing_data_policy"],
            "UNKNOWN_NOT_ZERO",
        )
        self.assertIsNone(
            result["style_dimension_value"]
        )


if __name__ == "__main__":
    unittest.main()
