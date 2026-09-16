import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from full_market_scanner import (  # noqa: E402
    load_config,
    materialize_from_stage71j_cache,
    scan_fixture_odds,
)


def bet(bid, name, values):
    return {"id": bid, "name": name, "values": values}


def v(value, odd, handicap=""):
    row = {"value": value, "odd": str(odd)}
    if handicap != "":
        row["handicap"] = str(handicap)
    return row


def synthetic_payload():
    bet365 = [
        bet(1, "Match Winner", [v("Home", 2.00), v("Draw", 3.40), v("Away", 3.80)]),
        bet(12, "Double Chance", [v("Home/Draw", 1.25), v("Draw/Away", 1.75), v("Home/Away", 1.30)]),
        bet(4, "Asian Handicap", [
            v("Home -0.5", 1.95), v("Away +0.5", 1.95),
            v("Home -0.25", 1.90), v("Away +0.25", 2.00),
            v("Home 0", 1.45), v("Away 0", 2.65),
        ]),
        bet(9, "Handicap Result", [v("Home -1", 3.20), v("Draw -1", 3.60), v("Away -1", 1.95)]),
        bet(5, "Goals Over/Under", [v("Over 2.5", 1.85), v("Under 2.5", 2.00)]),
        bet(8, "Both Teams To Score", [v("Yes", 1.72), v("No", 2.05)]),
        bet(16, "Total - Home", [v("Over 1.5", 1.90), v("Under 1.5", 1.90)]),
        bet(17, "Total - Away", [v("Over 0.5", 1.70), v("Under 0.5", 2.10)]),
    ]
    marathon = [
        bet(1, "Match Winner", [v("Home", 2.10), v("Draw", 3.30), v("Away", 3.70)]),
        bet(12, "Double Chance", [v("1X", 1.27), v("X2", 1.78), v("12", 1.31)]),
        bet(4, "Asian Handicap", [
            v("Home -0.5", 2.00), v("Away +0.5", 1.90),
            v("Home -0.25", 1.92), v("Away +0.25", 1.98),
            v("Home 0", 1.50), v("Away 0", 2.55),
        ]),
        bet(9, "Handicap Result", [v("Home -1", 3.25), v("Draw -1", 3.55), v("Away -1", 1.97)]),
        bet(5, "Goals Over/Under", [v("Over", 1.88, "2.5"), v("Under", 1.98, "2.5")]),
        bet(8, "Both Teams To Score", [v("Yes", 1.75), v("No", 2.02)]),
        bet(16, "Total - Home", [v("Over", 1.93, "1.5"), v("Under", 1.87, "1.5")]),
        bet(17, "Total - Away", [v("Over", 1.72, "0.5"), v("Under", 2.08, "0.5")]),
    ]
    pinnacle = [
        bet(1, "Match Winner", [v("Home", 2.20), v("Draw", 3.25), v("Away", 3.60)]),
    ]
    return {
        "response": [
            {
                "league": {"id": 39, "name": "Premier League"},
                "fixture": {"id": 1001, "date": "2026-09-20T15:00:00+00:00"},
                "update": "2026-09-16T18:00:00+00:00",
                "bookmakers": [
                    {"name": "Bet365", "bets": bet365},
                    {"name": "Marathonbet", "bets": marathon},
                    {"name": "Pinnacle", "bets": pinnacle},
                ],
            }
        ]
    }


class FullMarketScannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()
        cls.meta = {
            "api_fixture_id": "1001",
            "league": "Premier League",
            "league_id": 39,
            "kickoff_utc": "2026-09-20T15:00:00Z",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
        }

    def scan(self):
        return scan_fixture_odds(synthetic_payload(), self.meta, self.cfg)

    def row(self, report, label):
        return next(x for x in report["options"] if x["selection_label"] == label)

    def test_scans_all_requested_market_families(self):
        report = self.scan()
        expected = set(self.cfg["target_market_families"])
        self.assertEqual(set(report["coverage"]), expected)
        self.assertTrue(all(report["coverage"][family]["status"] != "MISSING" for family in expected))

    def test_fixed_1x2_double_chance_dnb_and_btts(self):
        report = self.scan()
        labels = {row["selection_label"] for row in report["options"]}
        for label in ("P1", "X", "P2", "1X", "X2", "12", "F1(0)", "F2(0)", "YES", "NO"):
            self.assertIn(label, labels)
        self.assertEqual(report["coverage"]["MATCH_RESULT_1X2"]["available_selection_count"], 3)
        self.assertEqual(report["coverage"]["DOUBLE_CHANCE"]["available_selection_count"], 3)
        self.assertEqual(report["coverage"]["DRAW_NO_BET"]["available_selection_count"], 2)
        self.assertEqual(report["coverage"]["BTTS"]["available_selection_count"], 2)

    def test_totals_and_team_totals_are_line_specific(self):
        report = self.scan()
        for label in ("TB(2.5)", "TM(2.5)", "ITB1(1.5)", "ITM1(1.5)", "ITB2(0.5)", "ITM2(0.5)"):
            row = self.row(report, label)
            self.assertTrue(row["executable"])
            self.assertEqual(row["probability_status"], "NOT_EVALUATED_BY_SCANNER")

    def test_half_grid_handicap_is_executable_and_quarter_is_blocked(self):
        report = self.scan()
        half_home = self.row(report, "F1(-0.5)")
        half_away = self.row(report, "F2(0.5)")
        quarter_home = self.row(report, "F1(-0.25)")
        quarter_away = self.row(report, "F2(0.25)")
        self.assertTrue(half_home["executable"])
        self.assertTrue(half_away["executable"])
        self.assertFalse(quarter_home["executable"])
        self.assertFalse(quarter_away["executable"])
        self.assertEqual(quarter_home["availability_status"], "BLOCKED_QUARTER_ASIAN_HANDICAP")
        self.assertEqual(quarter_away["availability_status"], "BLOCKED_QUARTER_ASIAN_HANDICAP")

    def test_european_handicap_triplet_is_exposed(self):
        report = self.scan()
        for label in ("EH1(-1)", "EHX(-1)", "EH2(-1)"):
            self.assertTrue(self.row(report, label)["executable"])

    def test_best_price_is_only_for_same_exact_selection(self):
        report = self.scan()
        home = self.row(report, "P1")
        self.assertEqual(home["reference_price"], 2.00)
        self.assertEqual(home["executable_price"], 2.10)
        self.assertEqual(home["best_observed_price"], 2.20)
        self.assertEqual(home["best_observed_bookmaker"], "Pinnacle")
        self.assertEqual(home["best_alternative_scope"], "EXACT_MARKET_LINE_SELECTION_PRICE_ONLY")
        self.assertFalse(report["policy"]["cross_market_best_bet"])

    def test_missing_fixed_markets_are_explicit(self):
        payload = {
            "response": [{
                "fixture": {"id": 1001},
                "update": "2026-09-16T18:00:00Z",
                "bookmakers": [{"name": "Bet365", "bets": [
                    bet(1, "Match Winner", [v("Home", 2.0), v("Draw", 3.4), v("Away", 3.8)])
                ]}],
            }]
        }
        report = scan_fixture_odds(payload, self.meta, self.cfg)
        self.assertEqual(report["coverage"]["DOUBLE_CHANCE"]["status"], "MISSING")
        self.assertEqual(report["coverage"]["DRAW_NO_BET"]["status"], "MISSING")
        self.assertEqual(report["coverage"]["BTTS"]["status"], "MISSING")
        self.assertEqual(self.row(report, "1X")["availability_status"], "MISSING")
        self.assertEqual(self.row(report, "YES")["availability_status"], "MISSING")

    def test_scanner_never_emits_probability_ev_signal_or_stake_authority(self):
        report = self.scan()
        raw = json.dumps(report, ensure_ascii=False).lower()
        for forbidden in ('"p_pbk"', '"ev"', '"stake"', '"signal":', '"canonical":'):
            self.assertNotIn(forbidden, raw)
        self.assertFalse(report["policy"]["pbk_probability_calculated"])
        self.assertFalse(report["policy"]["ev_calculated"])
        self.assertEqual(report["policy"]["signals_created"], 0)
        self.assertFalse(report["policy"]["stake_changes"])
        self.assertFalse(report["policy"]["canonical_changes"])

    def test_stage71j_cache_materializer_adds_no_provider_calls(self):
        payload = synthetic_payload()
        cache = {
            ("/fixtures", (("league", "39"), ("next", "10"), ("season", "2026"), ("timezone", "UTC"))): {
                "response": [{
                    "fixture": {"id": 1001, "date": "2026-09-20T15:00:00Z"},
                    "league": {"id": 39, "name": "Premier League"},
                    "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}},
                }]
            },
            ("/odds", (("fixture", "1001"),)): payload,
        }
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "scanner.json"
            meta = materialize_from_stage71j_cache(cache, ["1001"], out)
            saved = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(meta["api_calls_added"], 0)
        self.assertEqual(meta["signals_created"], 0)
        self.assertEqual(meta["fixture_reports"], 1)
        self.assertEqual(saved["reports"][0]["fixture"]["home_team"], "Arsenal")
        self.assertEqual(saved["reports"][0]["fixture"]["away_team"], "Chelsea")


if __name__ == "__main__":
    unittest.main()
