import unittest

from scripts.stage86_team_style_operational_normalization import (
    select_forward_candidates,
)


class Stage86OperationalNormalizationTests(unittest.TestCase):

    def row(
        self,
        *,
        team_id="1",
        metric="shots_for",
        profile_before_utc="2026-09-17T10:00:00Z",
    ):
        return {
            "league_id": "39",
            "league_name": "Premier League",
            "season": "2026",
            "team_id": team_id,
            "split": "overall",
            "window": 5,
            "metric": metric,
            "metric_status": "KNOWN",
            "value": 10.0,
            "profile_before_utc": profile_before_utc,
            "observed_at_utc": profile_before_utc,
        }

    def test_first_seen_series_bootstraps_latest_snapshot_only(self):
        source = [
            self.row(profile_before_utc="2026-09-15T10:00:00Z"),
            self.row(profile_before_utc="2026-09-16T10:00:00Z"),
            self.row(profile_before_utc="2026-09-17T10:00:00Z"),
        ]

        candidates = select_forward_candidates(source, [])

        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0]["profile_before_utc"],
            "2026-09-17T10:00:00Z",
        )

    def test_existing_series_accepts_only_newer_than_watermark(self):
        existing = [
            self.row(profile_before_utc="2026-09-16T10:00:00Z")
        ]

        source = [
            self.row(profile_before_utc="2026-09-15T10:00:00Z"),
            self.row(profile_before_utc="2026-09-16T10:00:00Z"),
            self.row(profile_before_utc="2026-09-17T10:00:00Z"),
        ]

        candidates = select_forward_candidates(source, existing)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0]["profile_before_utc"],
            "2026-09-17T10:00:00Z",
        )

    def test_multiple_new_forward_snapshots_are_preserved(self):
        existing = [
            self.row(profile_before_utc="2026-09-15T10:00:00Z")
        ]

        source = [
            self.row(profile_before_utc="2026-09-16T10:00:00Z"),
            self.row(profile_before_utc="2026-09-17T10:00:00Z"),
        ]

        candidates = select_forward_candidates(source, existing)

        self.assertEqual(
            [
                row["profile_before_utc"]
                for row in candidates
            ],
            [
                "2026-09-16T10:00:00Z",
                "2026-09-17T10:00:00Z",
            ],
        )


if __name__ == "__main__":
    unittest.main()
