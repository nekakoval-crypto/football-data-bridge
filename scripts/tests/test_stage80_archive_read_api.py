import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import stage73_internal_api as api


class Stage80ArchiveReadApiTests(unittest.TestCase):
    def build_db(self, path):
        conn=sqlite3.connect(path)
        conn.execute("CREATE TABLE pbk_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO pbk_meta VALUES ('schema_version','test')")
        conn.execute("CREATE TABLE raw_historical_fixtures (fixture_id TEXT, home_team TEXT, away_team TEXT, terminal_observed TEXT)")
        conn.execute("INSERT INTO raw_historical_fixtures VALUES ('100','Alpha','Beta','YES')")
        conn.execute("CREATE TABLE raw_fixture_history_snapshots (fixture_id TEXT, observed_at_utc TEXT, status TEXT)")
        conn.execute("INSERT INTO raw_fixture_history_snapshots VALUES ('100','2026-09-18T10:00:00Z','FINISHED')")
        conn.execute("CREATE TABLE raw_lineup_snapshots (fixture_id TEXT, captured_at_utc TEXT, team_id TEXT, team_name TEXT)")
        conn.execute("INSERT INTO raw_lineup_snapshots VALUES ('100','2026-09-18T09:00:00Z','1','Alpha')")
        conn.execute("CREATE TABLE raw_injury_snapshots (fixture_id TEXT, captured_at_utc TEXT, team_id TEXT, player_id TEXT)")
        conn.execute("INSERT INTO raw_injury_snapshots VALUES ('100','2026-09-18T08:00:00Z','1','11')")
        conn.execute("CREATE TABLE raw_match_event_snapshots (fixture_id TEXT, elapsed TEXT, extra TEXT, event_id TEXT, event_type TEXT)")
        conn.execute("INSERT INTO raw_match_event_snapshots VALUES ('100','10','','e1','Goal')")
        conn.execute("CREATE TABLE raw_team_match_statistics (fixture_id TEXT, team_id TEXT, shots_total TEXT)")
        conn.execute("INSERT INTO raw_team_match_statistics VALUES ('100','1','12')")
        conn.execute("CREATE TABLE raw_player_stats_snapshots (fixture_id TEXT, observed_at_utc TEXT, team_id TEXT, player_id TEXT, player_name TEXT)")
        conn.execute("INSERT INTO raw_player_stats_snapshots VALUES ('100','2026-09-18T10:05:00Z','1','11','Player One')")
        conn.execute("CREATE TABLE raw_historical_players (player_id TEXT, latest_observed_name TEXT)")
        conn.execute("INSERT INTO raw_historical_players VALUES ('11','Player One')")
        conn.execute("INSERT INTO raw_historical_players VALUES ('12','Player Two')")
        conn.execute("CREATE TABLE raw_historical_transfer_events (transfer_event_id TEXT, pbk_player_id TEXT, transfermarkt_player_id TEXT, transfer_date TEXT, transfer_fee TEXT)")
        conn.execute("INSERT INTO raw_historical_transfer_events VALUES ('evt-1','11','900','2024-07-01','')")
        conn.execute("CREATE TABLE raw_pbk_player_xg_xa_research (pbk_player_id TEXT, match_date TEXT, statsbomb_match_id TEXT, xg_total TEXT, xa TEXT, mapping_confidence TEXT, research_only TEXT, operational_betting_authority TEXT)")
        conn.execute("INSERT INTO raw_pbk_player_xg_xa_research VALUES ('11','2024-06-18','sb100','0.42','0.18','HIGH','true','false')")
        conn.execute("CREATE TABLE raw_team_roster_history (player_id TEXT, captured_at_utc TEXT, team_id TEXT, team_name TEXT)")
        conn.execute("INSERT INTO raw_team_roster_history VALUES ('11','2026-09-17T10:00:00Z','1','Alpha')")
        conn.execute("CREATE TABLE raw_team_membership_intervals (player_id TEXT, first_seen_at_utc TEXT, team_id TEXT, interval_status TEXT)")
        conn.execute("INSERT INTO raw_team_membership_intervals VALUES ('11','2026-09-17T10:00:00Z','1','OPEN_LATEST')")
        conn.execute("CREATE TABLE raw_player_grade_snapshots (player_id TEXT, observed_at_utc TEXT, fixture_id TEXT, overall_grade TEXT)")
        conn.execute("INSERT INTO raw_player_grade_snapshots VALUES ('11','2026-09-18T10:05:00Z','100','7.1')")
        conn.execute("CREATE TABLE raw_epl_referee_profiles_research (referee TEXT, matches TEXT, draw_pct TEXT, total_yellows_per_observed_match TEXT, source_scope TEXT, penalties_available TEXT, research_only TEXT, operational_betting_authority TEXT)")
        conn.execute("INSERT INTO raw_epl_referee_profiles_research VALUES ('A Taylor','265','24.91','3.551','EPL_ONLY','false','true','false')")
        conn.execute("CREATE TABLE raw_epl_referee_team_splits_research (referee TEXT, team TEXT, matches TEXT, wins TEXT, draws TEXT, losses TEXT, points_per_match TEXT, source_scope TEXT, penalties_available TEXT, research_only TEXT, operational_betting_authority TEXT)")
        conn.execute("INSERT INTO raw_epl_referee_team_splits_research VALUES ('A Taylor','Arsenal','12','7','3','2','2.0','EPL_ONLY','false','true','false')")
        conn.execute("INSERT INTO raw_epl_referee_team_splits_research VALUES ('A Taylor','Chelsea','10','4','2','4','1.4','EPL_ONLY','false','true','false')")
        conn.execute("CREATE TABLE raw_top5_referee_profiles_research (provider_league_id TEXT, league_name TEXT, country TEXT, referee TEXT, matches TEXT, draw_pct TEXT, source_scope TEXT, cards_available TEXT, fouls_available TEXT, penalties_available TEXT, research_only TEXT, operational_betting_authority TEXT)")
        conn.execute("INSERT INTO raw_top5_referee_profiles_research VALUES ('39','Premier League','England','A Taylor','270','25.0','TOP5_9_SEASONS_API_FOOTBALL','false','false','false','true','false')")
        conn.execute("INSERT INTO raw_top5_referee_profiles_research VALUES ('39','Premier League','England','Shared Ref','10','20.0','TOP5_9_SEASONS_API_FOOTBALL','false','false','false','true','false')")
        conn.execute("INSERT INTO raw_top5_referee_profiles_research VALUES ('140','La Liga','Spain','Shared Ref','12','25.0','TOP5_9_SEASONS_API_FOOTBALL','false','false','false','true','false')")
        conn.execute("CREATE TABLE raw_top5_referee_team_splits_research (provider_league_id TEXT, league_name TEXT, country TEXT, referee TEXT, team_id TEXT, team TEXT, matches TEXT, wins TEXT, draws TEXT, losses TEXT, points_per_match TEXT, source_scope TEXT, cards_available TEXT, fouls_available TEXT, penalties_available TEXT, research_only TEXT, operational_betting_authority TEXT)")
        conn.execute("INSERT INTO raw_top5_referee_team_splits_research VALUES ('39','Premier League','England','A Taylor','42','Arsenal','12','7','3','2','2.0','TOP5_9_SEASONS_API_FOOTBALL','false','false','false','true','false')")
        conn.execute("INSERT INTO raw_top5_referee_team_splits_research VALUES ('39','Premier League','England','A Taylor','49','Chelsea','10','4','2','4','1.4','TOP5_9_SEASONS_API_FOOTBALL','false','false','false','true','false')")
        conn.execute("CREATE TABLE raw_stage80_top5_referee_backfill_state (provider_league_id TEXT, season TEXT, status TEXT)")
        for league_id in ('39','61','78','135','140'):
            for season in range(2017,2026):
                conn.execute("INSERT INTO raw_stage80_top5_referee_backfill_state VALUES (?,?,?)",(league_id,str(season),'CAPTURED'))
        conn.execute("CREATE TABLE raw_top5_referee_fixture_history (fixture_id TEXT, provider_league_id TEXT, referee TEXT)")
        conn.execute("INSERT INTO raw_top5_referee_fixture_history VALUES ('r1','39','A Taylor')")
        conn.execute("INSERT INTO raw_top5_referee_fixture_history VALUES ('r2','61','')")
        conn.commit(); conn.close()

    def test_fixture_archive_endpoint_is_provider_free(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"pbk.sqlite"
            self.build_db(db)
            with patch.object(api,"DB",db):
                status,payload=api.dispatch("/v1/archive/fixture?fixture_id=100")
        self.assertEqual(status,200)
        self.assertEqual(payload["fixture"]["home_team"],"Alpha")
        self.assertEqual(payload["coverage"]["event_rows"],1)
        self.assertEqual(payload["coverage"]["team_stat_rows"],1)
        self.assertEqual(payload["coverage"]["player_stat_rows"],1)
        self.assertFalse(payload["provider_polling"])
        self.assertFalse(payload["creates_signal"])
        self.assertFalse(payload["probability_mutation"])

    def test_player_archive_endpoint_returns_persisted_history(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"pbk.sqlite"
            self.build_db(db)
            with patch.object(api,"DB",db):
                status,payload=api.dispatch("/v1/archive/player?player_id=11")
        self.assertEqual(status,200)
        self.assertEqual(payload["player"]["latest_observed_name"],"Player One")
        self.assertEqual(payload["coverage"]["roster_rows"],1)
        self.assertEqual(payload["coverage"]["membership_intervals"],1)
        self.assertEqual(payload["coverage"]["match_stat_rows"],1)
        self.assertEqual(payload["coverage"]["grade_rows"],1)
        self.assertEqual(payload["coverage"]["transfer_rows"],1)
        self.assertTrue(payload["coverage"]["verified_transfer_history"])
        self.assertEqual(payload["historical_transfers"][0]["transfermarkt_player_id"],"900")
        self.assertEqual(payload["coverage"]["research_xg_xa_rows"],1)
        self.assertTrue(payload["coverage"]["research_xg_xa_available"])
        self.assertFalse(payload["coverage"]["research_xg_xa_operational_authority"])
        self.assertEqual(payload["research_xg_xa"][0]["xg_total"],"0.42")
        self.assertEqual(payload["research_xg_xa"][0]["xa"],"0.18")
        self.assertFalse(payload["provider_polling"])

    def test_player_archive_reports_explicit_empty_transfer_history(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"pbk.sqlite"
            self.build_db(db)
            with patch.object(api,"DB",db):
                status,payload=api.dispatch("/v1/archive/player?player_id=12")
        self.assertEqual(status,200)
        self.assertEqual(payload["historical_transfers"],[])
        self.assertEqual(payload["research_xg_xa"],[])
        self.assertEqual(payload["coverage"]["research_xg_xa_rows"],0)
        self.assertFalse(payload["coverage"]["research_xg_xa_available"])
        self.assertEqual(payload["coverage"]["transfer_rows"],0)
        self.assertFalse(payload["coverage"]["verified_transfer_history"])
        self.assertTrue(payload["coverage"]["partial_sources_possible"])

    def test_referee_archive_endpoint_returns_top5_profile_and_epl_rich_supplement(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"pbk.sqlite"
            self.build_db(db)
            with patch.object(api,"DB",db):
                status,payload=api.dispatch("/v1/archive/referee?referee=A%20Taylor")
        self.assertEqual(status,200)
        self.assertEqual(payload["referee"],"A Taylor")
        self.assertEqual(payload["provider_league_id"],"39")
        self.assertEqual(payload["profile"]["matches"],"270")
        self.assertEqual(payload["coverage"]["team_split_rows"],2)
        self.assertEqual(payload["coverage"]["source_scope"],"TOP5_9_SEASONS_API_FOOTBALL")
        self.assertTrue(payload["coverage"]["top5_matrix_complete"])
        self.assertFalse(payload["coverage"]["partial_top5_history"])
        self.assertEqual(payload["coverage"]["top5_matrix_captured_league_seasons"],45)
        self.assertEqual(payload["coverage"]["provider_referee_coverage_pct"],50.0)
        self.assertTrue(payload["coverage"]["provider_referee_field_partial"])
        self.assertTrue(payload["coverage"]["epl_rich_profile_available"])
        self.assertTrue(payload["coverage"]["cards_available"])
        self.assertTrue(payload["coverage"]["fouls_available"])
        self.assertEqual(payload["epl_rich_profile"]["matches"],"265")
        self.assertFalse(payload["coverage"]["penalties_available"])
        self.assertFalse(payload["coverage"]["operational_betting_authority"])
        self.assertFalse(payload["provider_polling"])
        self.assertFalse(payload["creates_signal"])
        self.assertFalse(payload["probability_mutation"])

    def test_referee_archive_team_filter_is_case_insensitive(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"pbk.sqlite"
            self.build_db(db)
            with patch.object(api,"DB",db):
                status,payload=api.dispatch("/v1/archive/referee?referee=A%20Taylor&provider_league_id=39&team=arsenal")
        self.assertEqual(status,200)
        self.assertEqual(payload["team_filter"],"arsenal")
        self.assertEqual(len(payload["team_splits"]),1)
        self.assertEqual(payload["team_splits"][0]["team"],"Arsenal")

    def test_referee_archive_team_id_filter_is_exact(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"pbk.sqlite"
            self.build_db(db)
            with patch.object(api,"DB",db):
                status,payload=api.dispatch("/v1/archive/referee?referee=A%20Taylor&provider_league_id=39&team_id=49")
        self.assertEqual(status,200)
        self.assertEqual(payload["team_id_filter"],"49")
        self.assertEqual(len(payload["team_splits"]),1)
        self.assertEqual(payload["team_splits"][0]["team"],"Chelsea")

    def test_referee_archive_requires_league_when_name_is_cross_league_ambiguous(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"pbk.sqlite"
            self.build_db(db)
            with patch.object(api,"DB",db):
                status,payload=api.dispatch("/v1/archive/referee?referee=Shared%20Ref")
                resolved_status,resolved=api.dispatch("/v1/archive/referee?referee=Shared%20Ref&provider_league_id=140")
        self.assertEqual(status,409)
        self.assertEqual(payload["error"],"AMBIGUOUS_REFEREE_LEAGUE")
        self.assertEqual([x["provider_league_id"] for x in payload["available_leagues"]],["39","140"])
        self.assertEqual(resolved_status,200)
        self.assertEqual(resolved["provider_league_id"],"140")
        self.assertEqual(resolved["profile"]["matches"],"12")
        self.assertFalse(resolved["coverage"]["epl_rich_profile_available"])
        self.assertFalse(resolved["coverage"]["cards_available"])
        self.assertFalse(resolved["coverage"]["fouls_available"])

    def test_referee_archive_falls_back_to_epl_when_top5_tables_are_absent(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"pbk.sqlite"
            self.build_db(db)
            conn=sqlite3.connect(db)
            for table in ('raw_top5_referee_profiles_research','raw_top5_referee_team_splits_research','raw_stage80_top5_referee_backfill_state','raw_top5_referee_fixture_history'):
                conn.execute(f'DROP TABLE {table}')
            conn.commit(); conn.close()
            with patch.object(api,"DB",db):
                status,payload=api.dispatch("/v1/archive/referee?referee=A%20Taylor")
        self.assertEqual(status,200)
        self.assertEqual(payload["coverage"]["source_scope"],"EPL_ONLY")
        self.assertTrue(payload["coverage"]["partial_top5_history"])
        self.assertEqual(payload["profile"]["matches"],"265")

    def test_referee_archive_missing_and_unknown_are_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"pbk.sqlite"
            self.build_db(db)
            with patch.object(api,"DB",db):
                missing_status,missing=api.dispatch("/v1/archive/referee")
                unknown_status,unknown=api.dispatch("/v1/archive/referee?referee=Unknown")
        self.assertEqual(missing_status,400)
        self.assertEqual(missing["error"],"MISSING_REFEREE")
        self.assertEqual(unknown_status,404)
        self.assertEqual(unknown["error"],"ARCHIVE_REFEREE_NOT_FOUND")

    def test_missing_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"pbk.sqlite"
            self.build_db(db)
            with patch.object(api,"DB",db):
                status,payload=api.dispatch("/v1/archive/fixture")
        self.assertEqual(status,400)
        self.assertEqual(payload["error"],"MISSING_FIXTURE_ID")

    def test_unknown_archive_entity_is_404(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"pbk.sqlite"
            self.build_db(db)
            with patch.object(api,"DB",db):
                status,payload=api.dispatch("/v1/archive/player?player_id=999")
        self.assertEqual(status,404)
        self.assertEqual(payload["error"],"ARCHIVE_PLAYER_NOT_FOUND")


if __name__=="__main__":
    unittest.main()
