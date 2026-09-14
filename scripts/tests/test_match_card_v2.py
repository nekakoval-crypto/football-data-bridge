import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import match_card_v2 as card
import stage73_internal_api as api


class MatchCardV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'pbk.sqlite'
        self.conn = sqlite3.connect(self.db)
        self.conn.row_factory = sqlite3.Row
        self._base_schema()

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def _base_schema(self):
        c = self.conn
        c.execute('CREATE TABLE pbk_meta (key TEXT PRIMARY KEY, value TEXT)')
        c.executemany('INSERT INTO pbk_meta VALUES (?,?)', [
            ('schema_version', '13'), ('built_at_utc', '2026-09-14T12:00:00Z')])
        c.execute('CREATE TABLE current_round_leagues ('
                  'provider_league_id TEXT, league_name TEXT, country TEXT, country_flag_url TEXT, '
                  'league_logo_url TEXT, season TEXT, round TEXT)')
        c.execute('INSERT INTO current_round_leagues VALUES (?,?,?,?,?,?,?)',
                  ('39', 'Premier League', 'England', 'flag', 'league-logo', '2026', 'Round 5'))
        c.execute('CREATE TABLE current_round_matches ('
                  'fixture_id TEXT, provider_league_id TEXT, league_name TEXT, country TEXT, '
                  'country_flag_url TEXT, league_logo_url TEXT, season TEXT, round TEXT, '
                  'kickoff_utc TEXT, home_team TEXT, home_team_logo_url TEXT, away_team TEXT, '
                  'away_team_logo_url TEXT, status TEXT, source_status TEXT, score_home TEXT, '
                  'score_away TEXT, observed_at_utc TEXT, live_observed_at_utc TEXT, '
                  'live_freshness_status TEXT, elapsed TEXT, red_cards_home TEXT, red_cards_away TEXT)')
        c.execute('INSERT INTO current_round_matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
            '999', '39', 'Premier League', 'England', 'flag', 'league-logo', '2026', 'Round 5',
            '2026-09-14T16:30:00Z', 'Alpha', 'alpha-logo', 'Beta', 'beta-logo', 'live', '2H',
            '1', '0', '2026-09-14T17:00:00Z', '2026-09-14T17:00:00Z', 'fresh', '65', '1', '0'))
        c.commit()

    def _add_full_sections(self):
        c = self.conn
        motivation = {
            'fixture_id': '999', 'available': True, 'no_lookahead': True,
            'standings_context': {
                'snapshot_id': 's1', 'snapshot_observed_at_utc': '2026-09-14T15:30:00Z',
                'requested_as_of_utc': '2026-09-14T16:30:00Z', 'no_lookahead': True,
            },
            'coverage': {'available': True, 'status': 'AVAILABLE', 'limitations': []},
            'home': {'primary_context': 'TITLE', 'pressure': 'MEDIUM'},
            'away': {'primary_context': 'SURVIVAL', 'pressure': 'HIGH'},
        }
        c.execute('CREATE TABLE fixture_motivation (fixture_id TEXT, payload_json TEXT)')
        c.execute('INSERT INTO fixture_motivation VALUES (?,?)', ('999', json.dumps(motivation)))

        c.execute('CREATE TABLE context_latest ('
                  'api_fixture_id TEXT, captured_at_utc TEXT, snapshot_type TEXT, fixture_status TEXT, '
                  'referee TEXT, venue_name TEXT, venue_city TEXT, home_rest_hours TEXT, away_rest_hours TEXT, '
                  'home_prev_fixture_id TEXT, home_prev_date_utc TEXT, home_prev_opponent TEXT, '
                  'home_prev_competition TEXT, home_prev_comp_class TEXT, away_prev_fixture_id TEXT, '
                  'away_prev_date_utc TEXT, away_prev_opponent TEXT, away_prev_competition TEXT, '
                  'away_prev_comp_class TEXT, home_next_fixture_id TEXT, home_next_date_utc TEXT, '
                  'home_next_opponent TEXT, home_next_competition TEXT, home_next_comp_class TEXT, '
                  'away_next_fixture_id TEXT, away_next_date_utc TEXT, away_next_opponent TEXT, '
                  'away_next_competition TEXT, away_next_comp_class TEXT, home_hours_to_next TEXT, '
                  'away_hours_to_next TEXT, home_prev_is_uefa_or_cup TEXT, away_prev_is_uefa_or_cup TEXT, '
                  'home_next_is_uefa_or_cup TEXT, away_next_is_uefa_or_cup TEXT, injuries_count TEXT, '
                  'home_injuries_count TEXT, away_injuries_count TEXT, injuries_json TEXT, lineups_available TEXT, '
                  'home_formation TEXT, away_formation TEXT, home_coach TEXT, away_coach TEXT, '
                  'home_start_xi_json TEXT, away_start_xi_json TEXT, context_only TEXT, notes TEXT)')
        old = ['999', '2026-09-14T10:00:00Z', 'T2', 'NS', 'Old Ref', 'Old Venue', 'Old City',
               '100', '100'] + [''] * 39
        c.execute('INSERT INTO context_latest VALUES (' + ','.join('?' for _ in old) + ')', old)
        row = [
            '999', '2026-09-14T15:00:00Z', 'T3', 'NS', 'Ref A', 'Stadium', 'City', '120', '96',
            '901', '2026-09-10T16:00:00Z', 'Prev H', 'League', 'LEAGUE_OR_OTHER',
            '902', '2026-09-11T18:00:00Z', 'Prev A', 'Cup', 'CUP',
            '903', '2026-09-20T16:00:00Z', 'Next H', 'League', 'LEAGUE_OR_OTHER',
            '904', '2026-09-18T19:00:00Z', 'Next A', 'UEFA Champions League', 'UEFA',
            '96', '48', 'NO', 'YES', 'NO', 'YES', '3', '1', '2',
            json.dumps([{'player': 'X'}]), 'YES', '4-3-3', '4-2-3-1', 'Coach H', 'Coach A',
            json.dumps([{'player': 'H1'}]), json.dumps([{'player': 'A1'}]), 'YES', 'context note'
        ]
        c.execute('INSERT INTO context_latest VALUES (' + ','.join('?' for _ in row) + ')', row)

        c.execute('CREATE TABLE probability_predictions ('
                  'prediction_id TEXT, model_version TEXT, rule TEXT, api_fixture_id TEXT, selection TEXT, '
                  'trigger_captured_at_utc TEXT, trigger_b365_home TEXT, trigger_b365_draw TEXT, '
                  'trigger_b365_away TEXT, p_market_no_vig TEXT, p_pbk TEXT, model_alpha TEXT, '
                  'created_at_utc TEXT, status TEXT)')
        c.execute('INSERT INTO probability_predictions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
            'p1', 'm1', 'R1', '999', 'Away', '2026-09-14T10:00:00Z', '5.0', '4.0', '1.6',
            '0.60', '0.67', '0.30', '2026-09-14T10:05:00Z', 'FROZEN_PREMATCH'))

        c.execute('CREATE TABLE odds_snapshots ('
                  'forward_id TEXT, rule TEXT, api_fixture_id TEXT, captured_at_utc TEXT, fixture_status TEXT, '
                  'current_kickoff_utc TEXT, minutes_to_kickoff TEXT, selection TEXT, best_odds TEXT, best_book TEXT, '
                  'bet365_odds TEXT, user_best_odds TEXT, user_best_book TEXT, user_allowlist_configured TEXT, '
                  'api_odds_update_utc TEXT)')
        c.execute('INSERT INTO odds_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
            'f1', 'R1', '999', '2026-09-14T10:00:00Z', 'NS', '2026-09-14T16:30:00Z', '390',
            'Away', '1.60', 'Book A', '1.57', '1.58', 'Marathonbet', 'YES', '2026-09-14T09:55:00Z'))
        c.execute('INSERT INTO odds_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
            'f1', 'R1', '999', '2026-09-14T11:00:00Z', 'NS', '2026-09-14T16:30:00Z', '330',
            'Away', '1.65', 'Book B', '1.60', '1.62', 'Marathonbet', 'YES', '2026-09-14T10:55:00Z'))

        c.execute('CREATE TABLE value_radar_events ('
                  'radar_id TEXT, radar_kind TEXT, api_fixture_id TEXT, primary_rule TEXT, selection TEXT, '
                  'first_crossed_at_utc TEXT, model_version TEXT, p_market_no_vig TEXT, p_market_pct TEXT, '
                  'p_pbk TEXT, p_pbk_pct TEXT, edge_pp TEXT, executable_odds TEXT, executable_bookmaker TEXT, '
                  'ev TEXT, ev_pct TEXT, probability_status TEXT, status TEXT, source TEXT, creates_signal TEXT, '
                  'stake_changes TEXT, source_rules TEXT)')
        c.execute('INSERT INTO value_radar_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
            'r1', 'STRONG_VALUE', '999', 'R1', 'Away', '2026-09-14T11:00:00Z', 'm1',
            '0.60', '60', '0.67', '67', '7', '1.62', 'Marathonbet', '0.085', '8.5',
            'VALIDATED', 'FIRST_CROSSING_FROZEN', 'STAGE75_FROZEN_PREMATCH', 'false', 'false', '["R1"]'))

        c.execute('CREATE TABLE canonical_signals ('
                  'forward_id TEXT, rule TEXT, api_fixture_id TEXT, selection TEXT, stake_u TEXT, status TEXT, '
                  'result TEXT, trigger_selected_odds TEXT, market_execution_odds TEXT, market_execution_bookmaker TEXT, '
                  'paper_user_execution_odds TEXT, paper_user_execution_bookmaker TEXT, paper_user_execution_at_utc TEXT, '
                  'user_close_odds TEXT, user_close_bookmaker TEXT, user_execution_status TEXT, notes TEXT)')
        c.execute('INSERT INTO canonical_signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
            'f1', 'R1', '999', 'Away', '1.0', 'PAPER', '', '1.57', '1.65', 'Book B',
            '1.62', 'Marathonbet', '2026-09-14T11:00:00Z', '', '', 'FROZEN', 'paper only'))
        c.commit()

    def test_missing_and_unknown_fixture_are_stable(self):
        status, payload = card.build_match_card(self.conn, '')
        self.assertEqual(status, 400)
        self.assertEqual(payload['error'], 'MISSING_FIXTURE_ID')
        status, payload = card.build_match_card(self.conn, 'does-not-exist')
        self.assertEqual(status, 404)
        self.assertEqual(payload['error'], 'UNKNOWN_FIXTURE')

    def test_fixture_header_preserves_live_score_red_cards_and_media(self):
        status, payload = card.build_match_card(self.conn, '999')
        self.assertEqual(status, 200)
        fixture = payload['fixture']
        self.assertEqual(fixture['status'], 'live')
        self.assertEqual(fixture['score'], {'home': 1, 'away': 0})
        self.assertEqual(fixture['home']['red_cards'], 1)
        self.assertEqual(fixture['home']['logo_url'], 'alpha-logo')
        self.assertEqual(fixture['league_logo_url'], 'league-logo')

    def test_partial_card_is_honest_when_optional_sections_missing(self):
        status, payload = card.build_match_card(self.conn, '999')
        self.assertEqual(status, 200)
        self.assertEqual(payload['coverage']['status'], 'PARTIAL')
        self.assertFalse(payload['coverage']['sections']['motivation'])
        self.assertIn('MOTIVATION_UNAVAILABLE', payload['coverage']['limitations'])
        self.assertTrue(payload['read_only'])
        self.assertFalse(payload['provider_polling'])
        self.assertFalse(payload['model_mutation'])

    def test_full_card_composes_existing_sources_without_mutation(self):
        self._add_full_sections()
        status, payload = card.build_match_card(self.conn, '999')
        self.assertEqual(status, 200)
        self.assertEqual(payload['card_version'], 'v2')
        self.assertEqual(payload['coverage']['status'], 'AVAILABLE')
        self.assertTrue(all(payload['coverage']['sections'].values()))
        self.assertTrue(payload['motivation']['no_lookahead'])
        self.assertEqual(payload['motivation']['standings_context']['snapshot_id'], 's1')
        self.assertFalse(payload['eligibility_mutation'])
        self.assertFalse(payload['model_mutation'])

    def test_context_uses_latest_capture_and_parses_lineups(self):
        self._add_full_sections()
        _, payload = card.build_match_card(self.conn, '999')
        context = payload['context']
        self.assertEqual(context['captured_at_utc'], '2026-09-14T15:00:00Z')
        self.assertEqual(context['referee'], 'Ref A')
        self.assertEqual(context['rest_hours'], {'home': 120, 'away': 96})
        self.assertTrue(context['lineups']['available'])
        self.assertEqual(context['lineups']['home_start_xi'][0]['player'], 'H1')
        self.assertEqual(context['injuries']['total'], 3)

    def test_odds_keeps_latest_per_rule_selection(self):
        self._add_full_sections()
        _, payload = card.build_match_card(self.conn, '999')
        odds = payload['odds']['items']
        self.assertEqual(len(odds), 1)
        self.assertEqual(odds[0]['captured_at_utc'], '2026-09-14T11:00:00Z')
        self.assertEqual(odds[0]['best_odds'], '1.65')

    def test_value_radar_remains_research_only(self):
        self._add_full_sections()
        _, payload = card.build_match_card(self.conn, '999')
        radar = payload['value_radar']
        self.assertTrue(radar['available'])
        self.assertTrue(radar['research_only'])
        self.assertFalse(radar['creates_signal'])
        self.assertFalse(radar['stake_changes'])
        self.assertEqual(radar['items'][0]['source_rules'], ['R1'])

    def test_stage73_endpoint_is_read_only_and_provider_free(self):
        self._add_full_sections()
        self.conn.close()
        with patch.object(api, 'DB', self.db):
            status, payload = api.dispatch('/v1/match-card?fixture_id=999')
        self.conn = sqlite3.connect(self.db)
        self.conn.row_factory = sqlite3.Row
        self.assertEqual(status, 200)
        self.assertEqual(payload['card_version'], 'v2')
        self.assertTrue(payload['read_only'])
        self.assertFalse(payload['provider_polling'])
        self.assertEqual(payload['fixture']['fixture_id'], '999')


if __name__ == '__main__':
    unittest.main()
