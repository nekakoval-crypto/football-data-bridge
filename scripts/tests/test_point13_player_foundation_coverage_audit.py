from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import point13_player_foundation_coverage_audit as m


class Point13PlayerFoundationCoverageAuditTests(unittest.TestCase):
    def test_summarize_core_coverage(self):
        history = [
            {"fixture_id":"1","status":"FT","country":"England","competition_name":"Premier League","season":"2025"},
            {"fixture_id":"2","status":"FT","country":"England","competition_name":"Premier League","season":"2025"},
            {"fixture_id":"3","status":"NS","country":"England","competition_name":"Premier League","season":"2025"},
        ]
        stats = [
            {"fixture_id":"1","player_id":"10"},
            {"fixture_id":"2","player_id":"20"},
        ]
        grades = [
            {"fixture_id":"1","player_id":"10"},
        ]
        form = [
            {"sample_3":"3","sample_5":"5","sample_10":"10"},
            {"sample_3":"2","sample_5":"4","sample_10":"9"},
        ]
        players = [
            {"player_id":"10","has_match_stats_evidence":"YES"},
            {"player_id":"20","has_match_stats_evidence":"NO"},
        ]
        xgxa = [{"pbk_player_id":"10"}]
        mapping = [
            {"match_status":"AUTO_MATCH"},
            {"match_status":"REVIEW"},
            {"match_status":"UNMATCHED"},
        ]

        report = m.summarize(history, stats, grades, form, players, xgxa, mapping)
        fx = report["historical_fixture_coverage"]
        self.assertEqual(fx["terminal_historical_fixtures"], 2)
        self.assertEqual(fx["normalized_player_fixtures"], 1)
        self.assertEqual(fx["fixture_coverage_pct"], 50.0)

        pc = report["player_catalog_coverage"]
        self.assertEqual(pc["catalog_players"], 2)
        self.assertEqual(pc["players_with_match_stats_evidence"], 1)

        fc = report["form_coverage"]
        self.assertEqual(fc["form3_full_window_rows"], 1)
        self.assertEqual(fc["form5_full_window_rows"], 1)
        self.assertEqual(fc["form10_full_window_rows"], 1)

        xg = report["xg_xa_coverage"]
        self.assertEqual(xg["mapped_pbk_players"], 1)
        self.assertEqual(xg["auto_match_high"], 1)
        self.assertEqual(xg["review"], 1)
        self.assertEqual(xg["unmatched"], 1)

    def test_normalized_fixture_requires_stats_and_grades(self):
        history = [{"fixture_id":"1","status":"FT","country":"X","competition_name":"L","season":"2025"}]
        report = m.summarize(
            history,
            [{"fixture_id":"1","player_id":"10"}],
            [],
            [],
            [],
            [],
            [],
        )
        self.assertEqual(
            report["historical_fixture_coverage"]["normalized_player_fixtures"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
