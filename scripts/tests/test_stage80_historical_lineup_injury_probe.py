#!/usr/bin/env python3
import unittest

from scripts.stage80_historical_lineup_injury_probe import (
    classify_payload,
    deterministic_sample,
)


def row(fid, country, season, kickoff, role="DOMESTIC_LEAGUE", status="FT"):
    return {
        "fixture_id": str(fid),
        "country": country,
        "season": str(season),
        "kickoff_utc": kickoff,
        "competition_role": role,
        "status": status,
        "provider_competition_id": "1",
        "competition_name": f"{country} League",
        "round": "1",
        "home_team": "A",
        "away_team": "B",
    }


class HistoricalLineupInjuryProbeTests(unittest.TestCase):
    def test_classify_payload(self):
        self.assertEqual(
            classify_payload({"response": [{"team": {"id": 1}}]}),
            ("CAPTURED", 1),
        )
        self.assertEqual(
            classify_payload({"response": []}),
            ("NO_DATA", 0),
        )
        self.assertEqual(
            classify_payload({"foo": []}),
            ("ERROR", 0),
        )

    def test_deterministic_sample_balances_countries_and_seasons(self):
        rows = []
        fid = 1
        for country in ("England", "Spain"):
            for season in (2025, 2024):
                for day in range(1, 7):
                    rows.append(
                        row(
                            fid,
                            country,
                            season,
                            f"{season}-01-{day:02d}T12:00:00Z",
                        )
                    )
                    fid += 1

        sample = deterministic_sample(
            rows,
            expected_leagues=2,
            per_league=4,
            seasons_per_league=2,
        )

        self.assertEqual(len(sample), 8)
        self.assertEqual(
            sum(item["country"] == "England" for item in sample),
            4,
        )
        self.assertEqual(
            sum(item["country"] == "Spain" for item in sample),
            4,
        )
        self.assertEqual(
            {item["season"] for item in sample},
            {"2025", "2024"},
        )

    def test_deterministic_sample_excludes_nonterminal_and_cups(self):
        rows = [
            row(1, "England", 2025, "2025-01-01T12:00:00Z"),
            row(2, "England", 2025, "2025-01-02T12:00:00Z"),
            row(
                3,
                "England",
                2025,
                "2025-01-03T12:00:00Z",
                role="DOMESTIC_CUP",
            ),
            row(
                4,
                "England",
                2025,
                "2025-01-04T12:00:00Z",
                status="NS",
            ),
        ]

        sample = deterministic_sample(
            rows,
            expected_leagues=1,
            per_league=2,
            seasons_per_league=1,
        )
        self.assertEqual(
            [item["fixture_id"] for item in sample],
            ["1", "2"],
        )


if __name__ == "__main__":
    unittest.main()
