import unittest

from scripts.stage90_team_style_population_history import (
    history_row,
    profile_state_key,
    select_forward_candidates,
)


class Stage92StylePopulationIntegrityTests(unittest.TestCase):

    def row(
        self,
        *,
        profile_before_utc,
        fixture_ids,
        value=10.0,
        metric_status="KNOWN",
    ):
        return {
            "schema_version": (
                "PBK_STAGE84_TEAM_STYLE_METRIC_OBSERVATIONS_V1"
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
            "window_actual_matches": len(fixture_ids),
            "window_complete": len(fixture_ids) >= 5,
            "window_fixture_ids": list(fixture_ids),
        }

    def test_same_fixture_composition_is_not_new_sample(self):
        first = self.row(
            profile_before_utc="2026-09-17T10:00:00Z",
            fixture_ids=[101, 102, 103, 104, 105],
        )

        repeated = self.row(
            profile_before_utc="2026-09-18T10:00:00Z",
            fixture_ids=[101, 102, 103, 104, 105],
        )

        existing = [history_row(first)]

        selected = select_forward_candidates(
            [repeated],
            existing,
        )

        self.assertEqual(selected, [])
        self.assertEqual(
            profile_state_key(first),
            profile_state_key(repeated),
        )

    def test_new_fixture_composition_creates_new_sample(self):
        first = self.row(
            profile_before_utc="2026-09-17T10:00:00Z",
            fixture_ids=[101, 102, 103, 104, 105],
        )

        changed = self.row(
            profile_before_utc="2026-09-18T10:00:00Z",
            fixture_ids=[106, 101, 102, 103, 104],
        )

        existing = [history_row(first)]

        selected = select_forward_candidates(
            [changed],
            existing,
        )

        self.assertEqual(len(selected), 1)
        self.assertEqual(
            selected[0]["window_fixture_ids"],
            [106, 101, 102, 103, 104],
        )
        self.assertNotEqual(
            profile_state_key(first),
            profile_state_key(changed),
        )

    def test_unknown_is_preserved_without_zero_fill(self):
        source = self.row(
            profile_before_utc="2026-09-17T10:00:00Z",
            fixture_ids=[101, 102, 103],
            value=None,
            metric_status="UNKNOWN",
        )

        result = history_row(source)

        self.assertEqual(
            result["metric_status"],
            "UNKNOWN",
        )
        self.assertIsNone(result["value"])
        self.assertEqual(
            result["population_sample_unit"],
            "DISTINCT_ROLLING_WINDOW_FIXTURE_COMPOSITION",
        )
        self.assertFalse(
            result[
                "repeated_pipeline_snapshot_counts_as_new_sample"
            ]
        )


if __name__ == "__main__":
    unittest.main()
