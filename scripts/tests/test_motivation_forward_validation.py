import csv
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)

import motivation_forward_validation as rail


class MotivationForwardValidationTests(
    unittest.TestCase
):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_csv(
        self,
        name,
        fields,
        rows,
    ):
        path = self.ops / name

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fields,
            )
            writer.writeheader()
            writer.writerows(rows)

        return path

    def fixture(
        self,
        *,
        status="NS",
        score_home="",
        score_away="",
    ):
        return {
            "fixture_id": "999",
            "provider_league_id": "39",
            "season": "2026",
            "kickoff_utc": (
                "2026-09-24T18:00:00Z"
            ),
            "home_team": "Alpha",
            "away_team": "Beta",
            "status": status,
            "score_home": score_home,
            "score_away": score_away,
        }

    def standings(self):
        common = {
            "snapshot_id": "snap-1",
            "provider_league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "observed_at_utc": (
                "2026-09-24T17:00:00Z"
            ),
            "played": "20",
            "group_name": "Premier League",
            "source": "test",
        }

        return [
            {
                **common,
                "team_id": "1",
                "team_name": "Alpha",
                "rank": "1",
                "points": "45",
                "description": (
                    "Champions League"
                ),
            },
            {
                **common,
                "team_id": "2",
                "team_name": "Beta",
                "rank": "2",
                "points": "42",
                "description": "",
            },
        ]

    def materialize_inputs(
        self,
        fixture,
    ):
        self.write_csv(
            "current_round_fixtures.csv",
            list(fixture),
            [fixture],
        )

        rows = self.standings()

        fields = sorted(
            {
                key
                for row in rows
                for key in row
            }
        )

        self.write_csv(
            "standings_snapshots.csv",
            fields,
            rows,
        )

    def test_prematch_capture_is_prospective_and_immutable(self):
        fixture = self.fixture()
        self.materialize_inputs(fixture)

        before = datetime(
            2026,
            9,
            24,
            17,
            30,
            tzinfo=timezone.utc,
        )

        result = rail.run(
            observed_at=before,
            ops=self.ops,
        )

        self.assertEqual(
            result[
                "prematch_events_created"
            ],
            1,
        )

        raw_before = (
            self.ops
            / "motivation_forward_prematch.jsonl"
        ).read_bytes()

        again = rail.run(
            observed_at=datetime(
                2026,
                9,
                24,
                17,
                40,
                tzinfo=timezone.utc,
            ),
            ops=self.ops,
        )

        raw_after = (
            self.ops
            / "motivation_forward_prematch.jsonl"
        ).read_bytes()

        self.assertEqual(
            again[
                "prematch_events_created"
            ],
            0,
        )
        self.assertEqual(
            raw_before,
            raw_after,
        )

    def test_no_historical_backfill_after_kickoff(self):
        fixture = self.fixture()
        self.materialize_inputs(fixture)

        result = rail.run(
            observed_at=datetime(
                2026,
                9,
                24,
                19,
                0,
                tzinfo=timezone.utc,
            ),
            ops=self.ops,
        )

        self.assertEqual(
            result["prematch_events"],
            0,
        )
        self.assertEqual(
            result[
                "skipped_after_kickoff_no_backfill"
            ],
            1,
        )

    def test_postmatch_label_never_mutates_prematch(self):
        fixture = self.fixture()
        self.materialize_inputs(fixture)

        rail.run(
            observed_at=datetime(
                2026,
                9,
                24,
                17,
                30,
                tzinfo=timezone.utc,
            ),
            ops=self.ops,
        )

        prematch_path = (
            self.ops
            / "motivation_forward_prematch.jsonl"
        )

        frozen = prematch_path.read_bytes()

        settled = self.fixture(
            status="FT",
            score_home="2",
            score_away="1",
        )

        self.write_csv(
            "current_round_fixtures.csv",
            list(settled),
            [settled],
        )

        result = rail.run(
            observed_at=datetime(
                2026,
                9,
                24,
                20,
                0,
                tzinfo=timezone.utc,
            ),
            ops=self.ops,
        )

        self.assertEqual(
            result["labels_created"],
            1,
        )
        self.assertEqual(
            prematch_path.read_bytes(),
            frozen,
        )

        _, labels = rail.read_jsonl(
            self.ops
            / "motivation_forward_labels.jsonl"
        )

        self.assertEqual(
            labels[0]["payload"][
                "match_result"
            ],
            "HOME_WIN",
        )

        self.assertFalse(
            labels[0]["payload"][
                "prematch_evidence_mutated"
            ]
        )

    def test_engineering_readiness_does_not_grant_predictive_authority(self):
        readiness = (
            rail.engineering_readiness()
        )

        self.assertEqual(
            readiness[
                "engineering_status"
            ],
            "COMPLETE",
        )
        self.assertTrue(
            readiness[
                "forward_validation_rail"
            ]
        )
        self.assertEqual(
            readiness[
                "historical_backfill"
            ],
            "FORBIDDEN",
        )
        self.assertTrue(
            readiness["no_lookahead"]
        )
        self.assertEqual(
            readiness[
                "predictive_authority"
            ],
            "NOT_AUTHORIZED",
        )
        self.assertFalse(
            readiness[
                "operational_betting_authority"
            ]
        )
        self.assertFalse(
            readiness[
                "probability_mutation"
            ]
        )


if __name__ == "__main__":
    unittest.main()
