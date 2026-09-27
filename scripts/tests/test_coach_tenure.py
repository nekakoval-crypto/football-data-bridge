import unittest

from scripts.coach_tenure import (
    compare_candidate_to_verified,
    resolve_coach_at,
)


def row(
    coach,
    *,
    start,
    end="",
    authority="HISTORICAL_VERIFIED",
    precision="DATETIME",
):
    return {
        "team_id": "33",
        "team_name": "Manchester United",
        "coach_id": coach,
        "coach_name": coach,
        "valid_from_utc": start,
        "valid_to_utc": end,
        "effective_precision": precision,
        "source_type": "TEST",
        "source_ref": "TEST",
        "observed_at_utc": "2026-09-26",
        "temporal_authority": authority,
        "evidence_quality": "HIGH",
        "notes": "",
    }


class CoachTenureTests(
    unittest.TestCase
):

    def test_resolves_verified_datetime_tenure(
        self,
    ):

        rows = [
            row(
                "Coach A",
                start=(
                    "2026-01-13T10:00:00Z"
                ),
            )
        ]

        result = resolve_coach_at(
            rows,
            team_id="33",
            as_of_utc=(
                "2026-02-01T12:00:00Z"
            ),
        )

        self.assertEqual(
            result["status"],
            "COACH_RESOLVED",
        )

    def test_does_not_leak_before_start(
        self,
    ):

        rows = [
            row(
                "Coach A",
                start=(
                    "2026-01-13T10:00:00Z"
                ),
            )
        ]

        result = resolve_coach_at(
            rows,
            team_id="33",
            as_of_utc=(
                "2025-12-30T20:15:00Z"
            ),
        )

        self.assertEqual(
            result["status"],
            "COACH_UNKNOWN",
        )

    def test_datetime_end_is_exclusive(
        self,
    ):

        rows = [
            row(
                "Coach A",
                start=(
                    "2025-01-01T00:00:00Z"
                ),
                end=(
                    "2026-01-13T10:00:00Z"
                ),
            ),
            row(
                "Coach B",
                start=(
                    "2026-01-13T10:00:00Z"
                ),
            ),
        ]

        result = resolve_coach_at(
            rows,
            team_id="33",
            as_of_utc=(
                "2026-01-13T10:00:00Z"
            ),
        )

        self.assertEqual(
            result["coach"][
                "coach_name"
            ],
            "Coach B",
        )

    def test_retro_lineup_metadata_rejected(
        self,
    ):

        rows = [
            row(
                "Wrong Retrospective Coach",
                start=(
                    "2025-01-01T00:00:00Z"
                ),
                authority=(
                    "RETROSPECTIVE_ONLY"
                ),
            )
        ]

        result = resolve_coach_at(
            rows,
            team_id="33",
            as_of_utc=(
                "2025-12-30T20:15:00Z"
            ),
        )

        self.assertEqual(
            result["status"],
            "COACH_UNKNOWN",
        )

        self.assertEqual(
            result[
                "rejected_non_authoritative"
            ],
            1,
        )

    def test_provider_candidate_rejected_by_resolver(
        self,
    ):

        rows = [
            row(
                "Michael Carrick",
                start="2025-08-01",
                authority=(
                    "PROVIDER_CAREER_CANDIDATE"
                ),
                precision="DATE",
            )
        ]

        result = resolve_coach_at(
            rows,
            team_id="33",
            as_of_utc=(
                "2026-02-01T12:00:00Z"
            ),
        )

        self.assertEqual(
            result["status"],
            "COACH_UNKNOWN",
        )

        self.assertEqual(
            result[
                "rejected_non_authoritative"
            ],
            1,
        )

    def test_date_precision_start_day_uncertain(
        self,
    ):

        rows = [
            row(
                "Coach A",
                start="2026-01-13",
                precision="DATE",
            )
        ]

        result = resolve_coach_at(
            rows,
            team_id="33",
            as_of_utc=(
                "2026-01-13T20:00:00Z"
            ),
        )

        self.assertEqual(
            result["status"],
            (
                "COACH_TENURE_DATE_BOUNDARY_UNCERTAIN"
            ),
        )

    def test_date_precision_resolves_after_start_day(
        self,
    ):

        rows = [
            row(
                "Coach A",
                start="2026-01-13",
                precision="DATE",
            )
        ]

        result = resolve_coach_at(
            rows,
            team_id="33",
            as_of_utc=(
                "2026-01-14T00:00:01Z"
            ),
        )

        self.assertEqual(
            result["status"],
            "COACH_RESOLVED",
        )

    def test_overlap_is_ambiguous(
        self,
    ):

        rows = [
            row(
                "Coach A",
                start=(
                    "2026-01-01T00:00:00Z"
                ),
            ),
            row(
                "Coach B",
                start=(
                    "2026-01-10T00:00:00Z"
                ),
            ),
        ]

        result = resolve_coach_at(
            rows,
            team_id="33",
            as_of_utc=(
                "2026-02-01T12:00:00Z"
            ),
        )

        self.assertEqual(
            result["status"],
            "COACH_TENURE_AMBIGUOUS",
        )

    def test_provider_verified_conflict_detected(
        self,
    ):

        candidate = row(
            "Michael Carrick",
            start="2025-08-01",
            authority=(
                "PROVIDER_CAREER_CANDIDATE"
            ),
            precision="DATE",
        )

        verified = row(
            "Michael Carrick",
            start="2026-01-13",
            authority=(
                "HISTORICAL_VERIFIED"
            ),
            precision="DATE",
        )

        result = (
            compare_candidate_to_verified(
                candidate,
                [verified],
            )
        )

        self.assertEqual(
            result["status"],
            "PROVIDER_VERIFIED_CONFLICT",
        )

        self.assertFalse(
            result["automatic_promotion"]
        )

        self.assertFalse(
            result[
                "historical_verified_created"
            ]
        )

    def test_provider_match_still_not_promoted(
        self,
    ):

        candidate = row(
            "Coach A",
            start="2026-01-13",
            authority=(
                "PROVIDER_CAREER_CANDIDATE"
            ),
            precision="DATE",
        )

        verified = row(
            "Coach A",
            start="2026-01-13",
            authority=(
                "HISTORICAL_VERIFIED"
            ),
            precision="DATE",
        )

        result = (
            compare_candidate_to_verified(
                candidate,
                [verified],
            )
        )

        self.assertEqual(
            result["status"],
            (
                "PROVIDER_CORROBORATES_VERIFIED"
            ),
        )

        self.assertFalse(
            result["automatic_promotion"]
        )


if __name__ == "__main__":
    unittest.main()
