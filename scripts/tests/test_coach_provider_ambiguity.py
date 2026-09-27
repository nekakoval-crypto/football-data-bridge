import unittest

from scripts.coach_provider_ambiguity import (
    assess_provider_career_ambiguity,
)


class CoachProviderAmbiguityTests(
    unittest.TestCase
):

    def test_single_active_candidate(self):

        rows = [
            {
                "coach_id": "1",
                "coach_name": "Coach A",
                "team_id": "10",
                "start": "2026-01-01",
                "end": "",
            },
            {
                "coach_id": "2",
                "coach_name": "Coach B",
                "team_id": "10",
                "start": "2025-01-01",
                "end": "2026-01-01",
            },
        ]

        result = (
            assess_provider_career_ambiguity(
                rows,
                team_id="10",
                as_of_date="2026-09-27",
            )
        )

        self.assertEqual(
            result["status"],
            (
                "PROVIDER_CAREER_SINGLE_CANDIDATE"
            ),
        )

        self.assertEqual(
            result["distinct_active_coach_count"],
            1,
        )

        self.assertFalse(
            result["automatic_promotion"]
        )

    def test_tottenham_real_v17_is_ambiguous(
        self,
    ):

        rows = [
            {
                "coach_id": "23442",
                "coach_name": "T. Frank",
                "team_id": "47",
                "start": "2025-07-01",
                "end": "",
            },
            {
                "coach_id": "1701",
                "coach_name": "R. De Zerbi",
                "team_id": "47",
                "start": "2025-09-01",
                "end": "",
            },
            {
                "coach_id": "27686",
                "coach_name": "Igor Tudor",
                "team_id": "47",
                "start": "2025-09-01",
                "end": "",
            },
            {
                "coach_id": "28389",
                "coach_name": "Bruno Saltor",
                "team_id": "47",
                "start": "2025-11-01",
                "end": "",
            },
        ]

        result = (
            assess_provider_career_ambiguity(
                rows,
                team_id="47",
                as_of_date="2026-09-27",
            )
        )

        self.assertEqual(
            result["status"],
            "PROVIDER_CAREER_AMBIGUOUS",
        )

        self.assertEqual(
            result["distinct_active_coach_count"],
            4,
        )

        self.assertIsNone(
            result["selected_candidate"]
        )

    def test_juventus_real_v17_is_ambiguous(
        self,
    ):

        rows = [
            {
                "coach_id": "2432",
                "coach_name": "I. Tudor",
                "team_id": "496",
                "start": "2025-03-01",
                "end": "",
            },
            {
                "coach_id": "4842",
                "coach_name": "T. Motta",
                "team_id": "496",
                "start": "2024-06-01",
                "end": "2025-03-01",
            },
            {
                "coach_id": "25878",
                "coach_name": "Luciano Spalletti",
                "team_id": "496",
                "start": "2025-09-01",
                "end": "",
            },
        ]

        result = (
            assess_provider_career_ambiguity(
                rows,
                team_id="496",
                as_of_date="2026-09-27",
            )
        )

        self.assertEqual(
            result["status"],
            "PROVIDER_CAREER_AMBIGUOUS",
        )

        self.assertEqual(
            result["distinct_active_coach_count"],
            2,
        )

    def test_duplicate_same_identity_not_ambiguous(
        self,
    ):

        rows = [
            {
                "coach_id": "1",
                "coach_name": "Coach A",
                "team_id": "10",
                "start": "2026-01-01",
                "end": "",
            },
            {
                "coach_id": "1",
                "coach_name": "Coach A",
                "team_id": "10",
                "start": "2026-02-01",
                "end": "",
            },
        ]

        result = (
            assess_provider_career_ambiguity(
                rows,
                team_id="10",
                as_of_date="2026-09-27",
            )
        )

        self.assertEqual(
            result["status"],
            (
                "PROVIDER_CAREER_SINGLE_CANDIDATE"
            ),
        )

        self.assertEqual(
            result["distinct_active_coach_count"],
            1,
        )

    def test_invalid_start_blocks_selection(
        self,
    ):

        rows = [
            {
                "coach_id": "1",
                "coach_name": "Coach A",
                "team_id": "10",
                "start": "",
                "end": "",
            },
        ]

        result = (
            assess_provider_career_ambiguity(
                rows,
                team_id="10",
                as_of_date="2026-09-27",
            )
        )

        self.assertEqual(
            result["status"],
            "PROVIDER_CAREER_DATE_INVALID",
        )

        self.assertIsNone(
            result["selected_candidate"]
        )


if __name__ == "__main__":
    unittest.main()
