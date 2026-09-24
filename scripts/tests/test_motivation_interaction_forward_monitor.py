import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import motivation_interaction_forward_monitor as m


class MotivationInteractionForwardMonitorTests(
    unittest.TestCase
):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Path(self.temp.name)

        self.write_json(
            "motivation_interaction_specialist_v1.json",
            {
                "selected_interactions": list(m.SELECTED),
                "frozen_candidate": {
                    "interactions": list(m.SELECTED),
                    "beta": dict(m.EXPECTED_BETA),
                    "parameters_may_change_after_freeze": False,
                },
                "authorization": {
                    "forward_review_allowed": True,
                    "predictive_authority": "NOT_AUTHORIZED",
                },
            },
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, name, payload):
        (
            self.ops / name
        ).write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def write_jsonl(self, name, rows):
        (
            self.ops / name
        ).write_text(
            "".join(
                json.dumps(row) + "\n"
                for row in rows
            ),
            encoding="utf-8",
        )

    def sources(self):
        motivation = {
            "event_id": "mot-1",
            "event_type": "MOTIVATION_PREMATCH_FROZEN",
            "fixture_id": "999",
            "frozen_at_utc": "2026-09-24T17:20:00Z",
            "payload": {
                "fixture_id": "999",
                "kickoff_utc": "2026-09-24T18:00:00Z",
                "home_team": "Alpha",
                "away_team": "Beta",
                "comparison": {
                    "home_pressure": "HIGH",
                    "away_pressure": "LOW",
                },
                "home": {
                    "standings": {
                        "rank": 10,
                        "form": "WWWWW",
                    }
                },
                "away": {
                    "standings": {
                        "rank": 1,
                        "form": "LLLLL",
                    }
                },
            },
        }

        market = {
            "event_id": "market-1",
            "event_type": "GENERIC_1X2_V1_PREMATCH_FROZEN",
            "fixture_id": "999",
            "frozen_at_utc": "2026-09-24T16:00:00Z",
            "payload": {
                "fixture_id": "999",
                "kickoff_utc": "2026-09-24T18:00:00Z",
                "observed_at_utc": "2026-09-24T15:55:00Z",
                "p_market": {
                    "H": 0.50,
                    "D": 0.30,
                    "A": 0.20,
                },
            },
        }

        self.write_jsonl(
            "motivation_forward_prematch.jsonl",
            [motivation],
        )

        self.write_jsonl(
            "generic_1x2_v1_forward_prematch.jsonl",
            [market],
        )

        return motivation, market

    def before(self):
        return datetime(
            2026, 9, 24, 17, 30,
            tzinfo=timezone.utc,
        )

    def after(self):
        return datetime(
            2026, 9, 24, 20, 0,
            tzinfo=timezone.utc,
        )

    def test_exact_frozen_candidate_is_used(self):
        self.sources()

        result = m.run(
            observed_at=self.before(),
            ops=self.ops,
        )

        self.assertEqual(
            result["prematch_events_created"],
            1,
        )

        _, rows = m.read_jsonl(
            self.ops
            / "motivation_interaction_v1_forward_prematch.jsonl"
        )

        payload = rows[0]["payload"]

        self.assertEqual(
            payload["interactions"],
            {
                "HIGH_PRESSURE_X_FORM_ALIGNMENT": 1.0,
                "HIGH_PRESSURE_X_LARGE_RANK_DISADVANTAGE": 1.0,
            },
        )

        self.assertEqual(
            payload["beta"],
            m.EXPECTED_BETA,
        )

        self.assertFalse(
            payload["parameters_refit"]
        )

        self.assertEqual(
            payload["predictive_authority"],
            "NOT_AUTHORIZED",
        )

    def test_first_capture_is_immutable(self):
        self.sources()

        m.run(
            observed_at=self.before(),
            ops=self.ops,
        )

        path = (
            self.ops
            / "motivation_interaction_v1_forward_prematch.jsonl"
        )

        frozen = path.read_bytes()

        result = m.run(
            observed_at=datetime(
                2026, 9, 24, 17, 40,
                tzinfo=timezone.utc,
            ),
            ops=self.ops,
        )

        self.assertEqual(
            result["prematch_events_created"],
            0,
        )

        self.assertEqual(
            path.read_bytes(),
            frozen,
        )

    def test_missed_match_cannot_be_backfilled(self):
        self.sources()

        result = m.run(
            observed_at=self.after(),
            ops=self.ops,
        )

        self.assertEqual(
            result["prematch_events_created"],
            0,
        )

        self.assertEqual(
            result[
                "skipped_after_kickoff_no_backfill"
            ],
            1,
        )

    def test_postmatch_review_is_separate(self):
        self.sources()

        m.run(
            observed_at=self.before(),
            ops=self.ops,
        )

        prematch_path = (
            self.ops
            / "motivation_interaction_v1_forward_prematch.jsonl"
        )

        frozen = prematch_path.read_bytes()

        self.write_jsonl(
            "motivation_forward_labels.jsonl",
            [{
                "event_id": "label-1",
                "event_type": "MOTIVATION_POSTMATCH_LABEL",
                "fixture_id": "999",
                "payload": {
                    "fixture_id": "999",
                    "match_result": "HOME_WIN",
                    "prematch_evidence_mutated": False,
                },
            }],
        )

        result = m.run(
            observed_at=self.after(),
            ops=self.ops,
        )

        self.assertEqual(
            result["postmatch_reviews_created"],
            1,
        )

        self.assertEqual(
            prematch_path.read_bytes(),
            frozen,
        )

        _, reviews = m.read_jsonl(
            self.ops
            / "motivation_interaction_v1_forward_labels.jsonl"
        )

        payload = reviews[0]["payload"]

        self.assertEqual(
            payload["result"],
            "H",
        )

        self.assertFalse(
            payload["prematch_evidence_mutated"]
        )

        self.assertEqual(
            payload["predictive_authority"],
            "NOT_AUTHORIZED",
        )

    def test_spec_drift_fails_closed(self):
        broken = {
            "selected_interactions": [
                "HIGH_PRESSURE_X_FORM_ALIGNMENT"
            ],
            "frozen_candidate": {
                "interactions": [
                    "HIGH_PRESSURE_X_FORM_ALIGNMENT"
                ],
                "beta": {
                    "HIGH_PRESSURE_X_FORM_ALIGNMENT":
                        -0.08139028122268811
                },
                "parameters_may_change_after_freeze": False,
            },
            "authorization": {
                "forward_review_allowed": True,
                "predictive_authority": "NOT_AUTHORIZED",
            },
        }

        with self.assertRaises(ValueError):
            m.validate_spec(broken)


if __name__ == "__main__":
    unittest.main()
