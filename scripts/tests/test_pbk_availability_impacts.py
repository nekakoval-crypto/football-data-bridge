import unittest

from scripts import pbk_availability_impacts as impacts


class AvailabilityImpactTests(unittest.TestCase):
    def test_absence_requires_explicit_absent_state(self):
        events = [
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-16T10:00:00Z","state":"PRESENT","source":"test"},
        ]
        result = impacts.absence_impact_components(
            events, "7", "10", "2026-09-16T12:00:00Z",
            importance_row={"eligible":"true","importance_score":"0.8"},
            player_grade=7.4,
            replacement_grade=6.5,
        )
        self.assertFalse(result["confirmed_absence"])
        self.assertIn("NO_EXPLICIT_CONFIRMED_ABSENCE", result["blockers"])
        self.assertIsNone(result["candidate_total_impact"])

    def test_absence_exposes_components_but_no_arbitrary_total(self):
        events = [
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-16T10:00:00Z","state":"ABSENT","source":"official_team_report"},
        ]
        result = impacts.absence_impact_components(
            events, "7", "10", "2026-09-16T12:00:00Z",
            importance_row={"eligible":"true","importance_score":"0.8"},
            player_grade=7.4,
            replacement_grade=6.5,
        )
        self.assertTrue(result["confirmed_absence"])
        self.assertEqual(result["replacement_quality_gap"], 0.9)
        self.assertEqual(result["status"], "COMPONENTS_AVAILABLE")
        self.assertIsNone(result["candidate_total_impact"])
        self.assertFalse(result["probability_mutation"])

    def test_confirmed_absence_with_missing_component_stays_blocked(self):
        events = [
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-16T10:00:00Z","state":"ABSENT"},
        ]
        result = impacts.absence_impact_components(
            events, "7", "10", "2026-09-16T12:00:00Z",
            importance_row={"eligible":"true","importance_score":"0.8"},
            player_grade=7.4,
            replacement_grade=None,
        )
        self.assertTrue(result["confirmed_absence"])
        self.assertEqual(result["status"], "DATA_BLOCKED")
        self.assertIn("NO_REPLACEMENT_GRADE", result["blockers"])

    def test_future_availability_evidence_is_rejected(self):
        events = [
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-16T13:00:00Z","state":"ABSENT","source":"late"},
        ]
        result = impacts.absence_impact_components(events, "7", "10", "2026-09-16T12:00:00Z")
        self.assertFalse(result["confirmed_absence"])
        self.assertIsNone(result["latest_explicit_state"])

    def test_return_requires_explicit_absence_then_presence(self):
        events = [
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-01T10:00:00Z","state":"ABSENT"},
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-10T10:00:00Z","state":"STARTER"},
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-12T10:00:00Z","state":"BENCH"},
        ]
        result = impacts.return_event(events, "7", "10", "2026-09-16T12:00:00Z")
        self.assertTrue(result["return_event"])
        self.assertEqual(result["prior_absent_events"], 1)
        self.assertEqual(result["return_observed_at_utc"], "2026-09-10T10:00:00Z")
        self.assertIsNone(result["return_impact_score"])

    def test_missing_observation_does_not_create_return(self):
        events = [
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-10T10:00:00Z","state":"STARTER"},
        ]
        result = impacts.return_event(events, "7", "10", "2026-09-16T12:00:00Z")
        self.assertFalse(result["return_event"])
        self.assertIn("NO_EXPLICIT_PRIOR_ABSENCE_RUN", result["blockers"])

    def test_unknown_breaks_absence_to_presence_chain(self):
        events = [
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-01T10:00:00Z","state":"ABSENT"},
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-05T10:00:00Z","state":"PRESENT"},
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-08T10:00:00Z","state":"UNKNOWN"},
            {"player_id":"7","team_id":"10","observed_at_utc":"2026-09-10T10:00:00Z","state":"STARTER"},
        ]
        result = impacts.return_event(events, "7", "10", "2026-09-16T12:00:00Z")
        self.assertFalse(result["return_event"])
        self.assertEqual(result["prior_absent_events"], 0)

    def test_unsupported_state_fails_closed(self):
        with self.assertRaises(ValueError):
            impacts.observed_player_timeline(
                [{"player_id":"7","observed_at_utc":"2026-09-10T10:00:00Z","state":"INJURED_GUESS"}],
                "7", "2026-09-16T12:00:00Z",
            )

    def test_rotation_quality_tracks_membership_and_delta(self):
        previous = [{"id":str(i)} for i in range(1, 12)]
        current = [{"id":str(i)} for i in range(1, 10)] + [{"id":"12"},{"id":"13"}]
        grades = {str(i): 6.0 for i in range(1, 14)}
        grades[12] = 8.0
        grades[13] = 8.0
        result = impacts.rotation_quality_components(current, previous, grades, minimum_quality_coverage=8)
        self.assertEqual(result["retained_starters"], 9)
        self.assertEqual(result["changed_starters"], 2)
        self.assertEqual(result["changed_in_player_ids"], ["12", "13"])
        self.assertEqual(result["changed_out_player_ids"], ["10", "11"])
        self.assertAlmostEqual(result["previous_xi_quality"], 6.0)
        self.assertGreater(result["quality_delta"], 0)
        self.assertIsNone(result["rotation_impact_score"])

    def test_rotation_quality_blocks_low_coverage(self):
        previous = [{"id":str(i)} for i in range(1, 12)]
        current = [{"id":str(i)} for i in range(1, 12)]
        result = impacts.rotation_quality_components(current, previous, {"1":7.0}, minimum_quality_coverage=8)
        self.assertIsNone(result["quality_delta"])
        self.assertIn("CURRENT_XI_GRADE_COVERAGE_LOW", result["blockers"])
        self.assertIn("PREVIOUS_XI_GRADE_COVERAGE_LOW", result["blockers"])

    def test_rotation_quality_requires_complete_xis(self):
        previous = [{"id":str(i)} for i in range(1, 12)]
        current = [{"id":str(i)} for i in range(1, 11)]
        grades = {str(i): 7.0 for i in range(1, 12)}
        result = impacts.rotation_quality_components(current, previous, grades, minimum_quality_coverage=8)
        self.assertIsNone(result["quality_delta"])
        self.assertIn("CURRENT_XI_NOT_COMPLETE", result["blockers"])


if __name__ == "__main__":
    unittest.main()
