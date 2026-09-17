import unittest

from scripts.pbk_team_style_profiles import build_team_style_profile


class TeamStyleProfileTests(unittest.TestCase):
    def _row(self, fixture_id, kickoff, observed, venue, **metrics):
        return {
            "fixture_id": fixture_id,
            "kickoff_utc": kickoff,
            "observed_at_utc": observed,
            "source": "TEST_SOURCE",
            "venue": venue,
            "formation": "4-3-3",
            "metrics": metrics,
        }

    def test_rolling_windows_and_home_away_splits(self):
        rows = []
        for idx in range(1, 7):
            rows.append(
                self._row(
                    idx,
                    f"2026-09-{idx:02d}T18:00:00+00:00",
                    f"2026-09-{idx:02d}T20:00:00+00:00",
                    "HOME" if idx % 2 else "AWAY",
                    shots_for=10 + idx,
                    corners_for=4 + idx,
                )
            )
        profile = build_team_style_profile(rows, "2026-09-16T18:00:00+00:00")
        self.assertEqual(profile["splits"]["overall"]["eligible_matches"], 6)
        self.assertEqual(profile["splits"]["home"]["eligible_matches"], 3)
        self.assertEqual(profile["splits"]["away"]["eligible_matches"], 3)
        self.assertEqual(profile["splits"]["overall"]["windows"]["5"]["actual_matches"], 5)
        self.assertEqual(profile["splits"]["overall"]["windows"]["10"]["actual_matches"], 6)
        self.assertFalse(profile["splits"]["overall"]["windows"]["10"]["window_complete"])

    def test_no_lookahead_excludes_future_kickoff_and_post_cutoff_observation(self):
        rows = [
            self._row(1, "2026-09-10T18:00:00+00:00", "2026-09-10T20:00:00+00:00", "HOME", shots_for=12),
            self._row(2, "2026-09-17T18:00:00+00:00", "2026-09-15T20:00:00+00:00", "AWAY", shots_for=99),
            self._row(3, "2026-09-09T18:00:00+00:00", "2026-09-17T20:00:00+00:00", "AWAY", shots_for=99),
        ]
        profile = build_team_style_profile(rows, "2026-09-16T18:00:00+00:00")
        self.assertEqual(profile["eligible_matches_total"], 1)
        self.assertEqual(profile["exclusions"]["kickoff_not_before_cutoff"], 1)
        self.assertEqual(profile["exclusions"]["observed_after_cutoff"], 1)
        metric = profile["splits"]["overall"]["windows"]["5"]["metrics"]["shots_for"]
        self.assertEqual(metric["mean"], 12.0)

    def test_missing_metric_is_unknown_not_zero(self):
        rows = [self._row(1, "2026-09-10T18:00:00+00:00", "2026-09-10T20:00:00+00:00", "HOME", shots_for=12)]
        profile = build_team_style_profile(rows, "2026-09-16T18:00:00+00:00")
        xg = profile["splits"]["overall"]["windows"]["5"]["metrics"]["xg_for"]
        self.assertEqual(xg["status"], "UNKNOWN")
        self.assertIsNone(xg["mean"])
        self.assertEqual(xg["sample_size"], 0)
        self.assertIn("NOT_ZERO_FILLED", xg["limitations"])

    def test_partial_coverage_is_reported(self):
        rows = [
            self._row(1, "2026-09-10T18:00:00+00:00", "2026-09-10T20:00:00+00:00", "HOME", xg_for=1.2),
            self._row(2, "2026-09-09T18:00:00+00:00", "2026-09-09T20:00:00+00:00", "AWAY", shots_for=11),
        ]
        profile = build_team_style_profile(rows, "2026-09-16T18:00:00+00:00")
        xg = profile["splits"]["overall"]["windows"]["5"]["metrics"]["xg_for"]
        self.assertEqual(xg["status"], "KNOWN")
        self.assertEqual(xg["sample_size"], 1)
        self.assertEqual(xg["window_matches"], 2)
        self.assertEqual(xg["coverage_pct"], 50.0)

    def test_formation_is_context_only_and_no_overall_score(self):
        rows = [self._row(1, "2026-09-10T18:00:00+00:00", "2026-09-10T20:00:00+00:00", "HOME", shots_for=12)]
        profile = build_team_style_profile(rows, "2026-09-16T18:00:00+00:00")
        window = profile["splits"]["overall"]["windows"]["5"]
        self.assertFalse(profile["formation_is_style"])
        self.assertFalse(window["formation_context"]["used_as_style_feature"])
        self.assertIsNone(window["overall_style_score"])
        self.assertIsNone(window["component_weights"])
        self.assertFalse(profile["creates_signal"])
        self.assertFalse(profile["probability_mutation"])

    def test_matchup_dimensions_require_calibration(self):
        rows = [
            self._row(
                1,
                "2026-09-10T18:00:00+00:00",
                "2026-09-10T20:00:00+00:00",
                "HOME",
                ppda=8.2,
                high_turnovers=6,
                corners_for=7,
            )
        ]
        profile = build_team_style_profile(rows, "2026-09-16T18:00:00+00:00")
        candidates = profile["splits"]["overall"]["windows"]["5"]["matchup_dimension_candidates"]
        self.assertEqual(candidates["PRESS_INTENSITY"]["status"], "RAW_INPUT_AVAILABLE_REQUIRES_CALIBRATION")
        self.assertEqual(candidates["PRESS_INTENSITY"]["calibration_status"], "NOT_VALIDATED")
        self.assertIsNone(candidates["PRESS_INTENSITY"]["value"])
        self.assertEqual(candidates["TRANSITION_ATTACK"]["status"], "UNKNOWN")

    def test_source_and_aware_timestamps_are_required(self):
        rows = [
            {
                "fixture_id": 1,
                "kickoff_utc": "2026-09-10T18:00:00+00:00",
                "observed_at_utc": "2026-09-10T20:00:00+00:00",
                "venue": "HOME",
                "shots_for": 10,
            },
            {
                "fixture_id": 2,
                "kickoff_utc": "2026-09-09T18:00:00+00:00",
                "observed_at_utc": "2026-09-09T20:00:00",
                "source": "TEST_SOURCE",
                "venue": "AWAY",
                "shots_for": 10,
            },
        ]
        profile = build_team_style_profile(rows, "2026-09-16T18:00:00+00:00")
        self.assertEqual(profile["eligible_matches_total"], 0)
        self.assertEqual(profile["exclusions"]["missing_source"], 1)
        self.assertEqual(profile["exclusions"]["missing_or_naive_observed_at"], 1)


if __name__ == "__main__":
    unittest.main()
