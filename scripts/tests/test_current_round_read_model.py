import csv
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage71_current_round_capture as capture
import stage72_build_data_layer as builder
import stage73_internal_api as api


class CurrentRoundTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Path(self.temp.name)
        self.league = {
            'country': 'England', 'league': 'Premier League',
            'api_league_id': '39', 'api_league_name': 'Premier League', 'season': '2026',
        }

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, fid, status, date, goals=(None, None), metadata=True):
        league = {'id': 39, 'name': 'Premier League', 'country': 'England',
                  'season': 2026, 'round': 'Regular Season - 4'}
        if metadata:
            league.update(flag='https://flag', logo='https://logo')
        return {
            'fixture': {'id': fid, 'date': date, 'status': {'short': status}},
            'league': league,
            'teams': {'home': {'name': f'Home {fid}'}, 'away': {'name': f'Away {fid}'}},
            'goals': {'home': goals[0], 'away': goals[1]},
        }

    def test_provider_metadata_and_exact_round_resolution(self):
        calls = []
        def get(path, params, **kwargs):
            calls.append((path, params, kwargs))
            if path == '/fixtures/rounds':
                return {'response': ['Regular Season - 4']}
            return {'response': [self.fixture(1, 'FT', '2026-09-13T12:00:00Z', (2, 1))]}
        round_name, rows = capture.capture_round(self.league, '2026-09-13T15:00:00Z', get)
        self.assertEqual(round_name, 'Regular Season - 4')
        self.assertEqual(rows[0]['country_flag_url'], 'https://flag')
        self.assertEqual(rows[0]['league_logo_url'], 'https://logo')
        self.assertEqual(rows[0]['status'], 'finished')
        self.assertEqual(rows[0]['score_home'], 2)
        self.assertTrue(all(call[2]['force_refresh'] for call in calls))
        self.assertEqual(calls[1][1]['round'], 'Regular Season - 4')

    def test_nullable_provider_metadata_and_missing_score(self):
        row = capture.extract_fixture(
            self.fixture(2, 'NS', '2026-09-13T13:00:00Z', metadata=False),
            self.league, 'Regular Season - 4', '2026-09-13T15:00:00Z')
        self.assertIsNone(row['country_flag_url'])
        self.assertIsNone(row['league_logo_url'])
        self.assertIsNone(row['score_home'])
        self.assertIsNone(row['score_away'])
        self.assertEqual(row['status'], 'scheduled')

    def write(self, name, rows):
        with (self.ops / name).open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_stage72_and_api_keep_complete_chronological_round_and_broken_league(self):
        self.write('current_round_leagues.csv', [
            {'provider_league_id': '39', 'league_name': 'Premier League', 'country': 'England',
             'country_flag_url': '', 'league_logo_url': '', 'season': '2026',
             'round': 'Regular Season - 4', 'observed_at_utc': '2026-09-13T15:00:00Z',
             'status': 'available', 'error': ''},
            {'provider_league_id': '140', 'league_name': 'La Liga', 'country': 'Spain',
             'country_flag_url': '', 'league_logo_url': '', 'season': '2026',
             'round': '', 'observed_at_utc': '2026-09-13T15:00:00Z',
             'status': 'unavailable', 'error': 'provider did not return a current round'},
        ])
        self.write('current_round_fixtures.csv', [
            {'fixture_id': '3', 'provider_league_id': '39', 'league_name': 'Premier League',
             'country': 'England', 'country_flag_url': '', 'league_logo_url': '',
             'season': '2026', 'round': 'Regular Season - 4',
             'kickoff_utc': '2026-09-13T16:00:00Z', 'home_team': 'H3', 'away_team': 'A3',
             'status': 'scheduled', 'source_status': 'NS', 'score_home': '', 'score_away': '',
             'observed_at_utc': '2026-09-13T15:00:00Z'},
            {'fixture_id': '1', 'provider_league_id': '39', 'league_name': 'Premier League',
             'country': 'England', 'country_flag_url': '', 'league_logo_url': '',
             'season': '2026', 'round': 'Regular Season - 4',
             'kickoff_utc': '2026-09-13T12:00:00Z', 'home_team': 'H1', 'away_team': 'A1',
             'status': 'finished', 'source_status': 'FT', 'score_home': '2', 'score_away': '1',
             'observed_at_utc': '2026-09-13T15:00:00Z'},
            {'fixture_id': '2', 'provider_league_id': '39', 'league_name': 'Premier League',
             'country': 'England', 'country_flag_url': '', 'league_logo_url': '',
             'season': '2026', 'round': 'Regular Season - 4',
             'kickoff_utc': '2026-09-13T14:00:00Z', 'home_team': 'H2', 'away_team': 'A2',
             'status': 'postponed', 'source_status': 'PST', 'score_home': '', 'score_away': '',
             'observed_at_utc': '2026-09-13T15:00:00Z'},
        ])
        db = self.ops / 'rounds.sqlite'
        conn = sqlite3.connect(db)
        conn.execute('CREATE TABLE pbk_meta (key TEXT, value TEXT)')
        conn.executemany('INSERT INTO pbk_meta VALUES (?,?)', [('built_at_utc', '2026-09-13T15:05:00Z')])
        builder.create_current_round_tables(conn, self.ops)
        conn.commit()
        conn.close()
        with patch.object(api, 'DB', db):
            code, payload = api.dispatch('/v1/rounds/current')
        self.assertEqual(code, 200)
        self.assertEqual([x['fixture_id'] for x in payload['leagues'][0]['matches']], ['1', '2', '3'])
        self.assertEqual(payload['leagues'][0]['matches'][0]['score'], {'home': '2', 'away': '1'})
        self.assertIsNone(payload['leagues'][0]['matches'][1]['score'])
        self.assertEqual(payload['leagues'][1]['status'], 'unavailable')
        self.assertTrue(payload['coverage']['partial_leagues_possible'])
        self.assertTrue(payload['read_only'])
        self.assertFalse(payload['provider_polling'])

    def test_capture_keeps_unavailable_league_visible(self):
        catalog = self.ops / 'catalog.csv'
        with catalog.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.league))
            writer.writeheader()
            writer.writerow(self.league)
            broken = dict(self.league, api_league_id='140', api_league_name='La Liga')
            writer.writerow(broken)
        def get(path, params, **kwargs):
            if params['league'] == '140':
                raise RuntimeError('provider unavailable')
            return {'response': ['Regular Season - 4']} if path.endswith('rounds') else {
                'response': [self.fixture(1, 'FT', '2026-09-13T12:00:00Z', (1, 0))]
            }
        with patch.object(capture, 'CATALOG', catalog), \
             patch.object(capture, 'LEAGUES_OUT', self.ops / 'leagues.csv'), \
             patch.object(capture, 'FIXTURES_OUT', self.ops / 'fixtures.csv'), \
             patch.object(capture, 'META_OUT', self.ops / 'run.json'), \
             patch.object(capture.s53, 'api_get', get):
            capture.main()
        rows = capture.read_csv(self.ops / 'leagues.csv')
        self.assertEqual([row['status'] for row in rows], ['available', 'unavailable'])
        self.assertEqual(json.loads((self.ops / 'run.json').read_text())['api_calls'], 3)


if __name__ == '__main__':
    unittest.main()
