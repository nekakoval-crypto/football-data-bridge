import json
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import match_card_v2 as card


class MatchCardLiveFtAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        c = self.conn
        c.execute("CREATE TABLE pbk_meta (key TEXT PRIMARY KEY, value TEXT)")
        c.executemany("INSERT INTO pbk_meta VALUES (?,?)", [
            ("schema_version", "14"), ("built_at_utc", "2026-09-14T17:05:00Z")])
        c.execute("CREATE TABLE current_round_leagues (provider_league_id TEXT, league_name TEXT, country TEXT, country_flag_url TEXT, league_logo_url TEXT, season TEXT, round TEXT)")
        c.execute("INSERT INTO current_round_leagues VALUES (?,?,?,?,?,?,?)", ("39", "Premier League", "England", "flag", "league", "2026", "Round 5"))
        c.execute("CREATE TABLE current_round_matches (fixture_id TEXT, provider_league_id TEXT, league_name TEXT, country TEXT, country_flag_url TEXT, league_logo_url TEXT, season TEXT, round TEXT, kickoff_utc TEXT, home_team TEXT, home_team_logo_url TEXT, away_team TEXT, away_team_logo_url TEXT, status TEXT, source_status TEXT, score_home TEXT, score_away TEXT, observed_at_utc TEXT, live_observed_at_utc TEXT, live_freshness_status TEXT, elapsed TEXT, red_cards_home TEXT, red_cards_away TEXT)")
        c.execute("INSERT INTO current_round_matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "999", "39", "Premier League", "England", "flag", "league", "2026", "Round 5",
            "2026-09-14T16:30:00Z", "Alpha", "alpha", "Beta", "beta", "live", "2H",
            "1", "0", "2026-09-14T17:00:00Z", "2026-09-14T17:00:00Z", "fresh", "65", "1", "0"))

        motivation = {
            "fixture_id": "999", "available": True, "no_lookahead": True,
            "standings_context": {"snapshot_id": "s1", "snapshot_observed_at_utc": "2026-09-14T15:30:00Z", "requested_as_of_utc": "2026-09-14T16:30:00Z", "no_lookahead": True},
            "coverage": {"available": True, "status": "AVAILABLE", "limitations": []},
            "home": {"primary_context": "TITLE", "pressure": "MEDIUM"},
            "away": {"primary_context": "SURVIVAL", "pressure": "HIGH"},
        }
        c.execute("CREATE TABLE fixture_motivation (fixture_id TEXT, payload_json TEXT)")
        c.execute("INSERT INTO fixture_motivation VALUES (?,?)", ("999", json.dumps(motivation)))

        c.execute("CREATE TABLE probability_predictions (prediction_id TEXT, model_version TEXT, rule TEXT, api_fixture_id TEXT, selection TEXT, trigger_captured_at_utc TEXT, trigger_b365_home TEXT, trigger_b365_draw TEXT, trigger_b365_away TEXT, p_market_no_vig TEXT, p_pbk TEXT, model_alpha TEXT, created_at_utc TEXT, status TEXT)")
        c.execute("INSERT INTO probability_predictions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "p1", "m1", "R1", "999", "Away", "2026-09-14T15:00:00Z", "5.0", "4.0", "1.6", "0.60", "0.67", "0.30", "2026-09-14T15:01:00Z", "FROZEN_PREMATCH"))

        c.execute("CREATE TABLE match_result_snapshots (api_fixture_id TEXT, captured_at_utc TEXT, b365_home TEXT, b365_draw TEXT, b365_away TEXT, p_home TEXT, p_draw TEXT, p_away TEXT, user_bookmaker TEXT, user_home TEXT, user_draw TEXT, user_away TEXT)")
        c.execute("INSERT INTO match_result_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            "999", "2026-09-14T15:00:00Z", "2.10", "3.40", "3.60", "0.45", "0.28", "0.27", "Marathonbet", "2.12", "3.45", "3.65"))
        # Deliberately live/post-kickoff: Match Card market board must never substitute it for prematch.
        c.execute("INSERT INTO match_result_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            "999", "2026-09-14T17:00:00Z", "1.01", "50", "90", "0.97", "0.02", "0.01", "Marathonbet", "1.01", "50", "90"))

        c.execute("CREATE TABLE odds_snapshots (forward_id TEXT, rule TEXT, api_fixture_id TEXT, captured_at_utc TEXT, fixture_status TEXT, current_kickoff_utc TEXT, minutes_to_kickoff TEXT, selection TEXT, best_odds TEXT, best_book TEXT, bet365_odds TEXT, user_best_odds TEXT, user_best_book TEXT, user_allowlist_configured TEXT, api_odds_update_utc TEXT)")
        c.execute("INSERT INTO odds_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "f1", "R1", "999", "2026-09-14T15:20:00Z", "NS", "2026-09-14T16:30:00Z", "70", "Away", "1.65", "Book B", "1.60", "1.62", "Marathonbet", "YES", "2026-09-14T15:19:00Z"))

        c.execute("CREATE TABLE value_radar_events (radar_id TEXT, radar_kind TEXT, api_fixture_id TEXT, primary_rule TEXT, selection TEXT, first_crossed_at_utc TEXT, model_version TEXT, p_market_no_vig TEXT, p_market_pct TEXT, p_pbk TEXT, p_pbk_pct TEXT, edge_pp TEXT, executable_odds TEXT, executable_bookmaker TEXT, ev TEXT, ev_pct TEXT, probability_status TEXT, status TEXT, source TEXT, creates_signal TEXT, stake_changes TEXT, source_rules TEXT)")
        c.execute("INSERT INTO value_radar_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "r1", "STRONG_VALUE", "999", "R1", "Away", "2026-09-14T15:25:00Z", "m1", "0.60", "60", "0.67", "67", "7", "1.62", "Marathonbet", "0.085", "8.5", "VALIDATED", "FIRST_CROSSING_FROZEN", "STAGE75_FROZEN_PREMATCH", "false", "false", '["R1"]'))
        c.commit()

    def tearDown(self):
        self.conn.close()

    def build(self):
        status, payload = card.build_match_card(self.conn, "999")
        self.assertEqual(status, 200)
        return payload

    def test_live_to_ft_changes_only_dynamic_fixture_state_for_prematch_analysis(self):
        live = self.build()
        self.assertEqual(live["fixture"]["status"], "live")
        self.assertEqual(live["fixture"]["score"], {"home": 1, "away": 0})
        self.assertEqual(live["fixture"]["elapsed"], 65)
        self.assertEqual(live["fixture"]["home"]["red_cards"], 1)

        self.conn.execute("UPDATE current_round_matches SET status='finished', source_status='FT', score_home='2', score_away='1', elapsed='90', red_cards_away='1', observed_at_utc='2026-09-14T18:25:00Z', live_observed_at_utc='2026-09-14T18:25:00Z' WHERE fixture_id='999'")
        self.conn.commit()
        ft = self.build()

        self.assertEqual(ft["fixture"]["status"], "finished")
        self.assertEqual(ft["fixture"]["source_status"], "FT")
        self.assertEqual(ft["fixture"]["score"], {"home": 2, "away": 1})
        self.assertEqual(ft["fixture"]["away"]["red_cards"], 1)
        for section in ("motivation", "prediction", "markets", "odds", "value_radar"):
            self.assertEqual(ft[section], live[section], section)

    def test_live_market_board_stays_on_prematch_snapshot(self):
        payload = self.build()
        result = next(f for f in payload["markets"]["families"] if f["id"] == "MATCH_RESULT_1X2")
        self.assertEqual(result["observed_at_utc"], "2026-09-14T15:00:00Z")
        self.assertEqual(result["items"][0]["bet365_odds"], "2.10")
        self.assertNotEqual(result["items"][0]["bet365_odds"], "1.01")
        self.assertTrue(result["pre_match_frozen"])

    def test_elapsed_never_infers_ft(self):
        self.conn.execute("UPDATE current_round_matches SET status='live', source_status='2H', elapsed='120', score_home='3', score_away='3' WHERE fixture_id='999'")
        self.conn.commit()
        payload = self.build()
        self.assertEqual(payload["fixture"]["status"], "live")
        self.assertEqual(payload["fixture"]["source_status"], "2H")
        self.assertEqual(payload["fixture"]["elapsed"], 120)

    def test_stale_live_freshness_is_preserved_honestly(self):
        self.conn.execute("UPDATE current_round_matches SET live_freshness_status='stale', live_observed_at_utc='2026-09-14T16:40:00Z' WHERE fixture_id='999'")
        self.conn.commit()
        payload = self.build()
        self.assertEqual(payload["fixture"]["live_freshness_status"], "stale")
        self.assertEqual(payload["fixture"]["live_observed_at_utc"], "2026-09-14T16:40:00Z")

    def test_contract_remains_read_only_and_provider_free_through_ft(self):
        self.conn.execute("UPDATE current_round_matches SET status='finished', source_status='FT' WHERE fixture_id='999'")
        self.conn.commit()
        payload = self.build()
        self.assertTrue(payload["read_only"])
        self.assertFalse(payload["provider_polling"])
        self.assertFalse(payload["eligibility_mutation"])
        self.assertFalse(payload["model_mutation"])


if __name__ == "__main__":
    unittest.main()
