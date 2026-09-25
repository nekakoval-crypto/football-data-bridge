from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stage292_r2_statistics_coverage_audit as m


class Stage292R2StatisticsCoverageAuditTests(unittest.TestCase):
    def test_pending_historical_filters_exact_scope(self):
        rows = [
            {"fixture_id": "1", "backlog_status": "PENDING", "round": "HISTORICAL_BRIDGE"},
            {"fixture_id": "1", "backlog_status": "PENDING", "round": "HISTORICAL_BRIDGE"},
            {"fixture_id": "2", "backlog_status": "CAPTURED", "round": "HISTORICAL_BRIDGE"},
            {"fixture_id": "3", "backlog_status": "PENDING", "round": "CURRENT"},
        ]
        self.assertEqual([r["fixture_id"] for r in m.pending_historical(rows)], ["1"])

    def test_request_index_key_is_exact_fixture_statistics_key(self):
        config = {"prefix": "api-football-raw"}
        a = m.request_index_key_for_fixture(config, "123")
        b = m.request_index_key_for_fixture(config, "124")
        self.assertTrue(a.startswith("api-football-raw/request-index/"))
        self.assertNotEqual(a, b)

    def test_summarize_reports_hits_misses_errors(self):
        rows = [
            {"coverage_status": "HIT", "season": "2024", "league_name": "E0"},
            {"coverage_status": "MISS", "season": "2024", "league_name": "E0"},
            {"coverage_status": "HIT", "season": "2023", "league_name": "SP1"},
            {"coverage_status": "ERROR", "season": "2023", "league_name": "SP1"},
        ]
        report = m.summarize(rows)
        self.assertEqual(report["overall"]["HIT"], 2)
        self.assertEqual(report["overall"]["MISS"], 1)
        self.assertEqual(report["overall"]["ERROR"], 1)
        self.assertEqual(report["overall"]["total"], 4)
        self.assertEqual(report["overall"]["hit_rate_pct"], 50.0)
        self.assertEqual(report["by_season"]["2024"]["HIT"], 1)
        self.assertEqual(report["by_league"]["E0"]["MISS"], 1)


if __name__ == "__main__":
    unittest.main()
