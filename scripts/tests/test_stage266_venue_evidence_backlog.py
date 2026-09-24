import tempfile
import unittest
from pathlib import Path

from scripts.stage266_venue_evidence_backlog import (
    EVIDENCE_FIELDS,
    build_backlog,
    run,
    venue_priority,
)


def base_row(**overrides):
    row = {
        "provider_league_id": "39",
        "venue_id": "100",
        "venue_name": "Example Stadium",
        "venue_city": "Example City",
        "team_name": "Example FC",
        "nominal_capacity": "60000",
        "surface_provider": "grass",

        "operational_capacity": "",
        "roof_type": "UNKNOWN",
        "roof_state_default": "UNKNOWN",
        "enclosure_class": "UNKNOWN",
        "wind_exposure_class": "UNKNOWN",
        "acoustic_enclosure_class": "UNKNOWN",
        "pitch_orientation_deg": "",

        "context_only": "YES",
        "predictive_authority": "NOT_AUTHORIZED",
        "betting_authority": "NOT_AUTHORIZED",
    }

    row.update(overrides)
    return row


class VenueEvidenceBacklogTests(unittest.TestCase):

    def test_one_task_per_missing_field(self):
        tasks, venues = build_backlog(
            [base_row()],
            [],
        )

        self.assertEqual(
            len(venues),
            1,
        )

        self.assertEqual(
            len(tasks),
            len(EVIDENCE_FIELDS),
        )

        self.assertEqual(
            {
                row["evidence_field"]
                for row in tasks
            },
            set(EVIDENCE_FIELDS),
        )

    def test_existing_verified_value_is_not_queued(self):
        tasks, _ = build_backlog(
            [
                base_row(
                    roof_type="OPEN"
                )
            ],
            [],
        )

        self.assertNotIn(
            "roof_type",
            {
                row["evidence_field"]
                for row in tasks
            },
        )

    def test_shared_venue_is_aggregated_once(self):
        tasks, venues = build_backlog(
            [
                base_row(
                    team_name="A"
                ),
                base_row(
                    team_name="B"
                ),
            ],
            [],
        )

        self.assertEqual(
            len(venues),
            1,
        )

        self.assertEqual(
            len(tasks),
            len(EVIDENCE_FIELDS),
        )

        self.assertTrue(
            all(
                row["team_count"] == "2"
                for row in tasks
            )
        )

        self.assertTrue(
            all(
                row["shared_venue"] == "true"
                for row in tasks
            )
        )

    def test_priority_is_collection_only(self):
        shared, _ = venue_priority(
            nominal_capacity="60000",
            team_count=2,
            surface="grass",
        )

        small, _ = venue_priority(
            nominal_capacity="8000",
            team_count=1,
            surface="grass",
        )

        self.assertLess(
            shared,
            small,
        )

    def test_existing_queue_state_is_preserved(self):
        existing = [{
            "venue_id": "100",
            "evidence_field": "roof_type",
            "backlog_status": "NEEDS_REVIEW",
            "first_queued_at_utc":
                "2026-09-01T00:00:00Z",
            "notes": "check official source",
        }]

        tasks, _ = build_backlog(
            [base_row()],
            existing,
        )

        roof = next(
            row
            for row in tasks
            if row["evidence_field"]
            == "roof_type"
        )

        self.assertEqual(
            roof["backlog_status"],
            "NEEDS_REVIEW",
        )

        self.assertEqual(
            roof["first_queued_at_utc"],
            "2026-09-01T00:00:00Z",
        )

        self.assertEqual(
            roof["notes"],
            "check official source",
        )


if __name__ == "__main__":
    unittest.main()
