import copy
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts import stage80_pbk16_international_window_context as s


CONFIG = Path("config/stage80_fifa_uefa_windows_2017_2025.json")


def domestic(
    fid,
    kickoff,
    home_id,
    away_id,
    *,
    league_id="39",
    season="2025",
):
    return {
        "fixture_id": str(fid),
        "competition_role": "DOMESTIC_LEAGUE",
        "provider_competition_id": str(league_id),
        "competition_name": "League",
        "country": "Country",
        "season": str(season),
        "round": "Round 1",
        "kickoff_utc": kickoff,
        "status": "FT",
        "home_team_id": str(home_id),
        "home_team": f"Team {home_id}",
        "away_team_id": str(away_id),
        "away_team": f"Team {away_id}",
    }


class PBK16InternationalWindowContextTests(unittest.TestCase):
    def test_real_calendar_contract_is_locked_and_conservative(self):
        cfg, windows = s.load_config(CONFIG)
        self.assertEqual(cfg["version"], s.CONFIG_VERSION)
        self.assertEqual(len(windows), 39)
        self.assertEqual(len(cfg["sources"]), 5)
        self.assertTrue(cfg["window_policy"]["uefa_relevant_only"])
        self.assertTrue(cfg["window_policy"]["final_tournaments_excluded"])
        self.assertTrue(cfg["window_policy"]["non_uefa_only_windows_excluded"])
        self.assertFalse(cfg["window_policy"]["player_callup_inference"])
        self.assertFalse(cfg["window_policy"]["travel_inference"])
        self.assertFalse(cfg["window_policy"]["appearance_inference"])

        by_id = {row["window_id"]: row for row in windows}
        self.assertEqual(
            s.iso(by_id["2020_OCT"]["end"]),
            "2020-10-14T23:59:59Z",
        )
        self.assertEqual(by_id["2020_OCT"]["max_matches"], 3)
        self.assertEqual(
            s.iso(by_id["2021_MAR"]["start"]),
            "2021-03-22T00:00:00Z",
        )
        self.assertEqual(
            s.iso(by_id["2021_MAR"]["end"]),
            "2021-03-31T23:59:59Z",
        )
        self.assertEqual(by_id["2021_MAR"]["max_matches"], 3)
        self.assertEqual(
            s.iso(by_id["2021_SEP"]["start"]),
            "2021-08-30T00:00:00Z",
        )
        self.assertEqual(
            s.iso(by_id["2021_SEP"]["end"]),
            "2021-09-08T23:59:59Z",
        )
        self.assertEqual(by_id["2021_SEP"]["max_matches"], 3)

    def test_projection_marks_before_after_and_first_domestic_match(self):
        cfg, windows = s.load_config(CONFIG)
        rows = [
            # First team-10 league fixture after the September 2025 window.
            domestic("100", "2025-09-11T12:00:00+00:00", "10", "20"),
            # Team 10 has already played after the window; team 30 has not.
            domestic("101", "2025-09-12T12:00:00+00:00", "10", "30"),
            # Close before the October 2025 window.
            domestic("102", "2025-10-03T12:00:00+00:00", "40", "50"),
            # Inside the October 2025 window; first-after flags must not reuse September.
            domestic("103", "2025-10-10T12:00:00+00:00", "60", "70"),
        ]
        domestic_rows, projected, invalid = s.project(rows, cfg, windows)
        self.assertEqual(invalid, 0)
        self.assertEqual(len(domestic_rows), 4)

        by_id = {row["domestic_fixture_id"]: row for row in projected}
        first = by_id["100"]
        self.assertEqual(first["nearest_window_id"], "2025_SEP")
        self.assertEqual(first["window_relation"], "AFTER")
        self.assertEqual(first["within_72h_after_window"], "true")
        self.assertEqual(first["within_96h_after_window"], "true")
        self.assertEqual(first["within_7d_after_window"], "true")
        self.assertEqual(first["home_first_domestic_league_match_after_window"], "true")
        self.assertEqual(first["away_first_domestic_league_match_after_window"], "true")
        self.assertEqual(first["both_first_domestic_league_match_after_window"], "true")

        second = by_id["101"]
        self.assertEqual(second["home_domestic_matches_since_window_end_before_fixture"], 1)
        self.assertEqual(second["home_first_domestic_league_match_after_window"], "false")
        self.assertEqual(second["away_first_domestic_league_match_after_window"], "true")
        self.assertEqual(second["either_first_domestic_league_match_after_window"], "true")

        before = by_id["102"]
        self.assertEqual(before["nearest_window_id"], "2025_OCT")
        self.assertEqual(before["window_relation"], "BEFORE")
        self.assertEqual(before["within_72h_before_window"], "true")
        self.assertEqual(before["within_96h_before_window"], "true")
        self.assertEqual(before["within_7d_before_window"], "true")
        self.assertEqual(before["home_domestic_matches_since_window_end_before_fixture"], "")
        self.assertEqual(before["away_domestic_matches_since_window_end_before_fixture"], "")
        self.assertEqual(before["home_first_domestic_league_match_after_window"], "false")
        self.assertEqual(before["away_first_domestic_league_match_after_window"], "false")

        inside = by_id["103"]
        self.assertEqual(inside["nearest_window_id"], "2025_OCT")
        self.assertEqual(inside["window_relation"], "INSIDE")
        self.assertEqual(inside["within_72h_before_window"], "false")
        self.assertEqual(inside["within_72h_after_window"], "false")
        self.assertEqual(inside["home_domestic_matches_since_window_end_before_fixture"], "")
        self.assertEqual(inside["away_domestic_matches_since_window_end_before_fixture"], "")
        self.assertEqual(inside["either_first_domestic_league_match_after_window"], "false")

        for row in projected:
            self.assertEqual(row["window_reference_contract"], "NEAREST_WINDOW_RELATION_GATED_V2")
            self.assertEqual(row["player_level_international_status"], "UNVERIFIED")
            self.assertEqual(row["final_tournaments_included"], "false")
            self.assertEqual(row["non_uefa_only_windows_included"], "false")
            self.assertEqual(row["calendar_level_only"], "true")
            self.assertEqual(row["as_known_calendar_reference"], "true")
            self.assertEqual(row["no_match_result_dependency"], "true")
            self.assertEqual(row["no_lookahead"], "true")
            self.assertEqual(row["provider_calls"], "0")
            self.assertEqual(row["research_only"], "true")
            self.assertEqual(row["operational_betting_authority"], "false")
            self.assertEqual(row["creates_signal"], "false")
            self.assertEqual(row["probability_mutation"], "false")
            self.assertEqual(row["eligibility_mutation"], "false")
            self.assertEqual(row["stake_changes"], "false")
            self.assertEqual(row["forward_journal_mutation"], "false")

    def test_projection_has_no_match_result_dependency(self):
        cfg, windows = s.load_config(CONFIG)
        base = domestic("200", "2025-09-12T15:00:00+00:00", "10", "20")
        with_result = copy.deepcopy(base)
        with_result.update({
            "home_goals": "7",
            "away_goals": "0",
            "result": "H",
        })
        _, projected_a, _ = s.project([base], cfg, windows)
        _, projected_b, _ = s.project([with_result], cfg, windows)
        self.assertEqual(projected_a, projected_b)

    def test_meta_rejects_duplicate_domestic_fixture_ids_even_with_16_leagues(self):
        cfg, windows = s.load_config(CONFIG)
        projected = []
        domestic_rows = []
        for i in range(16):
            row = domestic(
                str(300 + i),
                "2025-09-12T15:00:00+00:00",
                str(1000 + i * 2),
                str(1001 + i * 2),
                league_id=str(100 + i),
            )
            domestic_rows.append(row)
            _, one, _ = s.project([row], cfg, windows)
            projected.extend(one)

        duplicate = dict(projected[0])
        duplicate["provider_league_id"] = projected[1]["provider_league_id"]
        projected.append(duplicate)
        domestic_rows.append(dict(domestic_rows[0]))

        meta = s.build_meta(
            domestic_rows,
            domestic_rows,
            projected,
            0,
            cfg,
            windows,
        )
        self.assertEqual(meta["domestic_anchor_league_ids"], 16)
        self.assertEqual(meta["duplicate_domestic_fixture_ids"], 1)
        self.assertEqual(meta["status"], "ATTENTION")

    def test_parse_dt_rejects_naive_timestamp(self):
        self.assertIsNone(s.parse_dt("2025-09-12T15:00:00"))
        self.assertEqual(
            s.parse_dt("2025-09-12T15:00:00Z"),
            datetime(2025, 9, 12, 15, 0, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
