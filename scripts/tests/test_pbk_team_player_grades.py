import json
import tempfile
import unittest
from pathlib import Path

from scripts import pbk_team_player_grades as grades


def grade_row(kickoff, value, *, observed=None, minutes=90, season="2026", player_id="7"):
    return {
        "player_id": player_id,
        "kickoff_utc": kickoff,
        "observed_at_utc": observed or kickoff,
        "minutes": minutes,
        "overall_grade": value,
        "season": season,
    }


class TeamPlayerGradeTests(unittest.TestCase):
    def test_player_form_profile_has_last_3_5_10_and_season(self):
        rows = []
        for day, value in enumerate([5.0, 5.5, 6.0, 6.5, 7.0, 7.5], start=1):
            rows.append(grade_row(f"2026-09-{day:02d}T12:00:00Z", value))
        result = grades.player_form_profile(rows, "7", "2026-09-20T12:00:00Z", season="2026")
        self.assertEqual(result["last"], 7.5)
        self.assertEqual(result["sample_3"], 3)
        self.assertEqual(result["sample_5"], 5)
        self.assertEqual(result["sample_10"], 6)
        self.assertEqual(result["sample_season"], 6)
        self.assertAlmostEqual(result["form_3"], 7.0)
        self.assertAlmostEqual(result["season"], 6.25)
        self.assertTrue(result["no_lookahead"])

    def test_player_form_rejects_future_and_late_observed_rows(self):
        rows = [
            grade_row("2026-09-10T12:00:00Z", 6.0),
            grade_row("2026-09-11T12:00:00Z", 9.9, observed="2026-09-21T00:00:00Z"),
            grade_row("2026-09-25T12:00:00Z", 10.0),
        ]
        result = grades.player_form_profile(rows, "7", "2026-09-20T12:00:00Z", season="2026")
        self.assertEqual(result["last"], 6.0)
        self.assertEqual(result["sample_10"], 1)
        self.assertEqual(result["post_cutoff_excluded"], 2)

    def test_low_minutes_are_excluded_not_zeroed(self):
        rows = [
            grade_row("2026-09-10T12:00:00Z", 9.0, minutes=12),
            grade_row("2026-09-09T12:00:00Z", 6.0, minutes=90),
        ]
        result = grades.player_form_profile(rows, "7", "2026-09-20T12:00:00Z", season="2026")
        self.assertEqual(result["last"], 6.0)
        self.assertEqual(result["low_minutes_excluded"], 1)

    def test_season_is_not_inferred_when_not_requested(self):
        result = grades.player_form_profile(
            [grade_row("2026-09-10T12:00:00Z", 6.0)],
            "7",
            "2026-09-20T12:00:00Z",
        )
        self.assertIsNone(result["season"])
        self.assertEqual(result["season_status"], "SEASON_NOT_REQUESTED")

    def test_team_components_never_create_arbitrary_overall(self):
        result = grades.team_component_vector({
            "ATTACK": {"candidate_grade": 7.2, "validation_status": "VALIDATION_PENDING", "source": "test"},
            "XI_QUALITY": {"candidate_grade": 6.8, "validation_status": "PROXY_LIMITED", "source": "test"},
        })
        self.assertIsNone(result["team_overall_grade"])
        self.assertIsNone(result["component_weighting"])
        self.assertIsNone(result["components"]["ATTACK"]["official_grade"])
        self.assertIsNone(result["components"]["XI_QUALITY"]["official_grade"])

    def test_only_validated_component_can_expose_official_grade(self):
        result = grades.team_component_vector({
            "FORM": {"candidate_grade": 6.4, "validation_status": "VALIDATED", "source": "oos-test"},
        })
        self.assertEqual(result["components"]["FORM"]["official_grade"], 6.4)
        self.assertIsNone(result["team_overall_grade"])

    def test_invalid_component_grade_fails_closed(self):
        with self.assertRaises(ValueError):
            grades.team_component_vector({
                "ATTACK": {"candidate_grade": 11.0, "validation_status": "VALIDATION_PENDING"}
            })

    def test_runtime_readiness_is_honest_when_player_data_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            ops = Path(temp)
            (ops / "stage77_last_run.json").write_text(json.dumps({"status": "ATTENTION", "backlog_pending": 38}), encoding="utf-8")
            (ops / "stage78_last_run.json").write_text(json.dumps({"status": "WAITING"}), encoding="utf-8")
            result = grades.runtime_readiness(ops)
        self.assertEqual(result["status"], "PARTIAL_DATA_BLOCKED")
        self.assertIn("NO_PLAYER_GRADE_ROWS", result["blockers"])
        self.assertIsNone(result["team"]["team_overall_grade"])
        self.assertEqual(result["policy"]["provider_calls_added"], 0)

    def test_run_writes_readiness_without_side_effect_authority(self):
        with tempfile.TemporaryDirectory() as temp:
            ops = Path(temp)
            result = grades.run(ops)
            self.assertTrue((ops / "team_player_grade_readiness.json").exists())
            self.assertFalse(result["policy"]["probability_mutation"])
            self.assertFalse(result["policy"]["stake_changes"])
            self.assertFalse(result["policy"]["ui_changes"])


if __name__ == "__main__":
    unittest.main()
