import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "config" / "pbk_venue_evidence.csv"
OVERRIDES = ROOT / "config" / "pbk_venue_overrides.csv"

SHARED_IDS = {"907", "910", "176", "150", "2612", "22763"}
PROJECTABLE = {
    "roof_type",
    "roof_state_default",
    "enclosure_class",
    "wind_exposure_class",
    "acoustic_enclosure_class",
}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class SharedVenueEvidenceTests(unittest.TestCase):

    def test_shared_batch_evidence_contract(self):
        rows = read_csv(EVIDENCE)
        overrides = read_csv(OVERRIDES)

        ids = {r["venue_id"] for r in rows}
        self.assertTrue(SHARED_IDS <= ids)

        self.assertTrue(all(r["source_url"].startswith("https://") for r in rows))
        self.assertTrue(all(r["evidence_status"] for r in rows))
        self.assertTrue(all(r["source_checked_at_utc"] for r in rows))

        projected = [
            r for r in rows
            if r["projection_allowed"].strip().lower() == "true"
        ]

        self.assertTrue(projected)
        self.assertTrue(all(r["projection_field"] in PROJECTABLE for r in projected))
        self.assertTrue(all(r["captured_value"] not in {"", "UNKNOWN"} for r in projected))

        self.assertFalse(any(
            r["projection_field"] in {"operational_capacity", "pitch_orientation_deg"}
            for r in projected
        ))

        override_by_venue = {
            r["venue_id"]: r
            for r in overrides
            if r["venue_id"]
        }

        for r in projected:
            o = override_by_venue[r["venue_id"]]
            self.assertEqual(
                o[r["projection_field"]],
                r["captured_value"],
            )

        for venue_id in SHARED_IDS:
            o = override_by_venue.get(venue_id)
            if o:
                self.assertEqual(o["operational_capacity"], "")
                self.assertEqual(o["pitch_orientation_deg"], "")

        conflicts = {
            r["evidence_field"]
            for r in rows
            if r["evidence_status"] == "NEEDS_REVIEW"
        }

        self.assertIn("provider_capacity_conflict", conflicts)
        self.assertIn("surface_provider_conflict", conflicts)


if __name__ == "__main__":
    unittest.main()
