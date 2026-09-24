import unittest
from datetime import date

from scripts.stage265_venue_registry import (
    active_override,
    pbk16_league_ids,
    registry_row,
)


class VenueRegistryTests(unittest.TestCase):

    def test_locked_pbk16_leagues(self):
        ids = pbk16_league_ids()

        self.assertEqual(
            len(ids),
            16,
        )

        self.assertEqual(
            len(set(ids)),
            16,
        )

    def test_no_fake_operational_capacity(self):
        row = registry_row(
            league_id="39",
            response_row={
                "team": {
                    "id": 1,
                    "name": "Example",
                    "country": "England",
                },
                "venue": {
                    "id": 100,
                    "name": "Example Ground",
                    "capacity": 50000,
                    "surface": "grass",
                },
            },
            override={},
        )

        self.assertEqual(
            row["nominal_capacity"],
            50000,
        )

        self.assertEqual(
            row["operational_capacity"],
            "",
        )

        self.assertEqual(
            row[
                "operational_capacity_status"
            ],
            "NOMINAL_ONLY",
        )

    def test_dated_capacity_override(self):
        rows = [
            {
                "venue_id": "100",
                "team_id": "",
                "valid_from": "2026-08-01",
                "valid_to": "2026-12-31",
                "operational_capacity":
                    "28000",
                "evidence_status":
                    "VERIFIED",
            }
        ]

        selected = active_override(
            rows,
            venue_id="100",
            team_id="1",
            as_of=date(
                2026,
                9,
                24,
            ),
        )

        self.assertEqual(
            selected[
                "operational_capacity"
            ],
            "28000",
        )

    def test_expired_override_not_used(self):
        rows = [
            {
                "venue_id": "100",
                "valid_from": "2025-01-01",
                "valid_to": "2025-12-31",
                "operational_capacity":
                    "25000",
            }
        ]

        selected = active_override(
            rows,
            venue_id="100",
            team_id="1",
            as_of=date(
                2026,
                9,
                24,
            ),
        )

        self.assertEqual(
            selected,
            {},
        )

    def test_unknown_stadium_properties_remain_unknown(self):
        row = registry_row(
            league_id="39",
            response_row={
                "team": {
                    "id": 1,
                    "name": "Example",
                },
                "venue": {
                    "id": 100,
                    "name": "Example Ground",
                    "capacity": 50000,
                },
            },
            override={},
        )

        self.assertEqual(
            row["roof_type"],
            "UNKNOWN",
        )

        self.assertEqual(
            row[
                "wind_exposure_class"
            ],
            "UNKNOWN",
        )

        self.assertEqual(
            row[
                "acoustic_enclosure_class"
            ],
            "UNKNOWN",
        )

        self.assertEqual(
            row[
                "attendance_expected_source_status"
            ],
            "NOT_CONNECTED",
        )

        self.assertEqual(
            row[
                "predictive_authority"
            ],
            "NOT_AUTHORIZED",
        )


if __name__ == "__main__":
    unittest.main()
