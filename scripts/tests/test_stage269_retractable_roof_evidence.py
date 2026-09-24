import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "config" / "pbk_venue_evidence.csv"
OVERRIDES = ROOT / "config" / "pbk_venue_overrides.csv"

RETRACTABLE = {
    "1456": "Estadio Santiago Bernabéu",
    "741": "VELTINS-Arena",
    "1117": "Johan Cruijff Arena",
}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class RetractableRoofEvidenceTests(unittest.TestCase):

    def test_retractable_roof_capability_is_verified(self):
        rows = read_csv(EVIDENCE)
        for venue_id in RETRACTABLE:
            matches = [
                r for r in rows
                if r["venue_id"] == venue_id
                and r["evidence_field"] == "roof_type"
            ]
            self.assertEqual(len(matches), 1)
            row = matches[0]
            self.assertEqual(row["captured_value"], "RETRACTABLE_FULL_PITCH_COVER")
            self.assertEqual(row["evidence_status"], "VERIFIED_DIRECT")
            self.assertEqual(row["projection_allowed"], "true")
            self.assertEqual(row["projection_field"], "roof_type")

    def test_actual_roof_state_is_prematch_dynamic(self):
        rows = read_csv(EVIDENCE)
        for venue_id in RETRACTABLE:
            state = next(
                r for r in rows
                if r["venue_id"] == venue_id
                and r["evidence_field"] == "roof_state_actual"
            )
            self.assertEqual(state["captured_value"], "PREMATCH_REQUIRED")
            self.assertEqual(state["projection_allowed"], "false")

    def test_static_overrides_do_not_infer_dynamic_state(self):
        overrides = {
            r["venue_id"]: r
            for r in read_csv(OVERRIDES)
            if r["venue_id"] in RETRACTABLE
        }
        self.assertEqual(set(overrides), set(RETRACTABLE))

        for venue_id, row in overrides.items():
            self.assertEqual(row["roof_type"], "RETRACTABLE_FULL_PITCH_COVER")
            self.assertEqual(row["roof_state_default"], "")
            self.assertEqual(row["operational_capacity"], "")
            self.assertEqual(row["pitch_orientation_deg"], "")


if __name__ == "__main__":
    unittest.main()
