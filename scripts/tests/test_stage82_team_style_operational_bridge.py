import csv
import tempfile
import unittest
from pathlib import Path

from scripts.stage82_team_style_operational_bridge import (
    build_evidence,
    fixture_pairs,
    metrics_from_pair,
)


class Stage82TeamStyleOperationalBridgeTests(unittest.TestCase):

    def _row(self, fixture_id, team_id, team_name, side, observed, **stats):
        row = {
            "fixture_id": str(fixture_id),
            "kickoff_utc": "2026-09-10T18:00:00+00:00",
            "observed_at_utc": observed,
            "team_id": str(team_id),
            "team_name": team_name,
            "side": side,
        }
        row.update(stats)
        return row

    def test_complete_pair_becomes_two_evidence_rows(self):
        rows = [
            self._row(
                101, 1, "Home FC", "HOME",
                "2026-09-10T20:00:00Z",
                shots_total="14",
                shots_on_goal="6",
                possession_pct="61",
                corners="7",
                passes_total="510",
                passes_accuracy_pct="88",
                expected_goals="1.82",
            ),
            self._row(
                101, 2, "Away FC", "AWAY",
                "2026-09-10T20:00:00Z",
                shots_total="8",
                shots_on_goal="3",
                possession_pct="39",
                corners="2",
                passes_total="330",
                passes_accuracy_pct="76",
                expected_goals="0.71",
            ),
        ]

        evidence, meta = build_evidence(rows)

        self.assertEqual(meta["complete_fixture_pairs"], 1)
        self.assertEqual(len(evidence), 2)

        home = next(row for row in evidence if row["team_id"] == 1)

        self.assertEqual(home["venue"], "HOME")
        self.assertEqual(home["opponent_team_id"], 2)
        self.assertEqual(home["metrics"]["shots_for"], 14.0)
        self.assertEqual(home["metrics"]["shots_against"], 8.0)
        self.assertEqual(home["metrics"]["shots_on_target_for"], 6.0)
        self.assertEqual(home["metrics"]["shots_on_target_against"], 3.0)
        self.assertEqual(home["metrics"]["corners_for"], 7.0)
        self.assertEqual(home["metrics"]["corners_against"], 2.0)
        self.assertEqual(home["metrics"]["xg_for"], 1.82)
        self.assertEqual(home["metrics"]["xg_against"], 0.71)

    def test_missing_metric_is_not_zero_filled(self):
        home = self._row(
            101, 1, "Home FC", "HOME",
            "2026-09-10T20:00:00Z",
            shots_total="14",
        )
        away = self._row(
            101, 2, "Away FC", "AWAY",
            "2026-09-10T20:00:00Z",
        )

        metrics = metrics_from_pair(home, away)

        self.assertEqual(metrics["shots_for"], 14.0)
        self.assertNotIn("xg_for", metrics)
        self.assertNotIn("xg_against", metrics)
        self.assertNotIn("shots_against", metrics)

    def test_incomplete_fixture_is_not_promoted(self):
        rows = [
            self._row(
                101, 1, "Home FC", "HOME",
                "2026-09-10T20:00:00Z",
                shots_total="14",
            )
        ]

        pairs, exclusions = fixture_pairs(rows)

        self.assertEqual(pairs, [])
        self.assertEqual(exclusions["incomplete_fixture_pair"], 1)

    def test_aware_observed_at_is_required(self):
        rows = [
            self._row(
                101, 1, "Home FC", "HOME",
                "2026-09-10T20:00:00",
                shots_total="14",
            ),
            self._row(
                101, 2, "Away FC", "AWAY",
                "2026-09-10T20:00:00Z",
                shots_total="8",
            ),
        ]

        evidence, meta = build_evidence(rows)

        self.assertEqual(len(evidence), 1)
        self.assertEqual(meta["validation"]["invalid_observed_at"], 1)

    def test_duplicate_side_does_not_create_extra_pair_member(self):
        rows = [
            self._row(101, 1, "Home FC", "HOME", "2026-09-10T20:00:00Z"),
            self._row(101, 9, "Wrong Home", "HOME", "2026-09-10T20:00:00Z"),
            self._row(101, 2, "Away FC", "AWAY", "2026-09-10T20:00:00Z"),
        ]

        pairs, exclusions = fixture_pairs(rows)

        self.assertEqual(len(pairs), 1)
        self.assertEqual(exclusions["duplicate_side"], 1)


if __name__ == "__main__":
    unittest.main()
