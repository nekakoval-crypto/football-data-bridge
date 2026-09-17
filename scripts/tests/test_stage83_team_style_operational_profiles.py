from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage83_team_style_operational_profiles import (
    VERSION,
    build_operational_profiles,
    group_team_rows,
)


def evidence(
    *,
    fixture_id: int,
    team_id: int,
    team_name: str,
    venue: str,
    kickoff: str,
    observed: str,
    shots_for=None,
    shots_against=None,
    xg_for=None,
    xg_against=None,
):
    return {
        "schema_version": "PBK_TEAM_STYLE_EVIDENCE_V1",
        "source": "PBK_STAGE81_TEAM_MATCH_STATISTICS",
        "source_observation_id": f"stage81:{fixture_id}:{observed}",
        "fixture_id": fixture_id,
        "kickoff_utc": kickoff,
        "observed_at_utc": observed,
        "team_id": team_id,
        "team_name": team_name,
        "venue": venue,
        "metrics": {
            "shots_for": shots_for,
            "shots_against": shots_against,
            "xg_for": xg_for,
            "xg_against": xg_against,
        },
    }


class Stage83OperationalProfilesTests(unittest.TestCase):
    def test_builds_last5_10_20_profile_without_provider_calls(self):
        rows = []

        for idx in range(1, 7):
            rows.append(
                evidence(
                    fixture_id=100 + idx,
                    team_id=1,
                    team_name="Alpha",
                    venue="HOME" if idx % 2 else "AWAY",
                    kickoff=f"2026-08-{idx:02d}T15:00:00+00:00",
                    observed=f"2026-08-{idx:02d}T18:00:00+00:00",
                    shots_for=10 + idx,
                    shots_against=8 + idx,
                    xg_for=1.0 + idx / 10,
                    xg_against=0.7 + idx / 10,
                )
            )

        result = build_operational_profiles(
            rows,
            "2026-09-01T00:00:00+00:00",
        )

        self.assertEqual(result["version"], VERSION)
        self.assertEqual(result["provider_calls_added"], 0)
        self.assertEqual(result["missing_evidence_policy"], "UNKNOWN_NOT_ZERO")
        self.assertEqual(result["style_scale_calibrated"], False)
        self.assertEqual(result["creates_signal"], False)

        profile = result["teams"]["1"]["profile"]

        self.assertEqual(profile["eligible_matches_total"], 6)
        self.assertEqual(profile["splits"]["overall"]["windows"]["5"]["actual_matches"], 5)
        self.assertEqual(profile["splits"]["overall"]["windows"]["10"]["actual_matches"], 6)
        self.assertEqual(profile["splits"]["overall"]["windows"]["20"]["actual_matches"], 6)

        self.assertTrue(profile["splits"]["overall"]["windows"]["5"]["window_complete"])
        self.assertFalse(profile["splits"]["overall"]["windows"]["10"]["window_complete"])
        self.assertFalse(profile["splits"]["overall"]["windows"]["20"]["window_complete"])

    def test_future_observation_is_excluded_by_foundation(self):
        rows = [
            evidence(
                fixture_id=1,
                team_id=10,
                team_name="Future FC",
                venue="HOME",
                kickoff="2026-08-20T15:00:00+00:00",
                observed="2026-09-05T12:00:00+00:00",
                shots_for=15,
            )
        ]

        result = build_operational_profiles(
            rows,
            "2026-09-01T00:00:00+00:00",
        )

        profile = result["teams"]["10"]["profile"]

        self.assertEqual(profile["eligible_matches_total"], 0)
        self.assertEqual(profile["exclusions"]["observed_after_cutoff"], 1)

    def test_future_kickoff_is_excluded(self):
        rows = [
            evidence(
                fixture_id=2,
                team_id=11,
                team_name="Future Kickoff",
                venue="AWAY",
                kickoff="2026-09-10T15:00:00+00:00",
                observed="2026-08-31T12:00:00+00:00",
                shots_for=7,
            )
        ]

        result = build_operational_profiles(
            rows,
            "2026-09-01T00:00:00+00:00",
        )

        profile = result["teams"]["11"]["profile"]

        self.assertEqual(profile["eligible_matches_total"], 0)
        self.assertEqual(profile["exclusions"]["kickoff_not_before_cutoff"], 1)

    def test_missing_metric_stays_unknown_not_zero(self):
        rows = [
            evidence(
                fixture_id=3,
                team_id=12,
                team_name="Unknown Metrics",
                venue="HOME",
                kickoff="2026-08-20T15:00:00+00:00",
                observed="2026-08-20T18:00:00+00:00",
                shots_for=None,
                xg_for=None,
            )
        ]

        result = build_operational_profiles(
            rows,
            "2026-09-01T00:00:00+00:00",
        )

        metric = (
            result["teams"]["12"]["profile"]
            ["splits"]["overall"]["windows"]["5"]["metrics"]["shots_for"]
        )

        self.assertEqual(metric["status"], "UNKNOWN")
        self.assertIsNone(metric["mean"])
        self.assertEqual(metric["sample_size"], 0)

    def test_home_and_away_splits_remain_separate(self):
        rows = [
            evidence(
                fixture_id=10,
                team_id=20,
                team_name="Split FC",
                venue="HOME",
                kickoff="2026-08-01T15:00:00+00:00",
                observed="2026-08-01T18:00:00+00:00",
                shots_for=20,
            ),
            evidence(
                fixture_id=11,
                team_id=20,
                team_name="Split FC",
                venue="AWAY",
                kickoff="2026-08-02T15:00:00+00:00",
                observed="2026-08-02T18:00:00+00:00",
                shots_for=6,
            ),
        ]

        result = build_operational_profiles(
            rows,
            "2026-09-01T00:00:00+00:00",
        )

        profile = result["teams"]["20"]["profile"]

        home = profile["splits"]["home"]["windows"]["5"]
        away = profile["splits"]["away"]["windows"]["5"]

        self.assertEqual(home["actual_matches"], 1)
        self.assertEqual(away["actual_matches"], 1)
        self.assertEqual(home["metrics"]["shots_for"]["mean"], 20.0)
        self.assertEqual(away["metrics"]["shots_for"]["mean"], 6.0)

    def test_grouping_rejects_bad_identity_time_and_venue(self):
        rows = [
            {"team_id": "", "source": "x"},
            {
                "team_id": 1,
                "source": "",
                "observed_at_utc": "2026-08-01T10:00:00+00:00",
                "kickoff_utc": "2026-08-01T09:00:00+00:00",
                "venue": "HOME",
            },
            {
                "team_id": 2,
                "source": "x",
                "observed_at_utc": "2026-08-01T10:00:00",
                "kickoff_utc": "2026-08-01T09:00:00+00:00",
                "venue": "HOME",
            },
            {
                "team_id": 3,
                "source": "x",
                "observed_at_utc": "2026-08-01T10:00:00+00:00",
                "kickoff_utc": "2026-08-01T09:00:00",
                "venue": "HOME",
            },
            {
                "team_id": 4,
                "source": "x",
                "observed_at_utc": "2026-08-01T10:00:00+00:00",
                "kickoff_utc": "2026-08-01T09:00:00+00:00",
                "venue": "NEUTRAL",
            },
        ]

        grouped, exclusions = group_team_rows(rows)

        self.assertEqual(grouped, {})
        self.assertEqual(exclusions["missing_team_id"], 1)
        self.assertEqual(exclusions["missing_source"], 1)
        self.assertEqual(exclusions["missing_or_naive_observed_at"], 1)
        self.assertEqual(exclusions["missing_or_naive_kickoff"], 1)
        self.assertEqual(exclusions["unknown_venue"], 1)

    def test_preserves_single_league_and_season_provenance(self):
        rows = [
            evidence(
                fixture_id=501,
                team_id=77,
                team_name="Provenance FC",
                venue="HOME",
                kickoff="2026-08-20T15:00:00+00:00",
                observed="2026-08-20T18:00:00+00:00",
                shots_for=12,
            )
        ]

        rows[0]["league_id"] = "140"
        rows[0]["league_name"] = "La Liga"
        rows[0]["season"] = "2026"

        result = build_operational_profiles(
            rows,
            "2026-09-01T00:00:00+00:00",
        )

        team = result["teams"]["77"]

        self.assertEqual(team["league_id"], "140")
        self.assertEqual(team["league_name"], "La Liga")
        self.assertEqual(team["season"], "2026")
if __name__ == "__main__":
    unittest.main()
