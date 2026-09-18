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
import stage71_observation_audit as audit
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

    def fixture(self, fid, status, date, goals=(None, None), metadata=True, team_logos=True):
        league = {'id': 39, 'name': 'Premier League', 'country': 'England',
                  'season': 2026, 'round': 'Regular Season - 4'}
        if metadata:
            league.update(flag='https://flag', logo='https://logo')
        teams = {'home': {'name': f'Home {fid}'}, 'away': {'name': f'Away {fid}'}}
        if team_logos:
            teams['home']['logo'] = 'https://home-logo'
            teams['away']['logo'] = 'https://away-logo'
        return {
            'fixture': {
                'id': fid, 'date': date, 'status': {'short': status},
                'referee': 'A. Referee',
                'venue': {'name': 'Test Stadium', 'city': 'London'},
            },
            'league': league,
            'teams': teams,
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
        self.assertEqual(rows[0]['home_team_logo_url'], 'https://home-logo')
        self.assertEqual(rows[0]['away_team_logo_url'], 'https://away-logo')
        self.assertEqual(rows[0]['referee'], 'A. Referee')
        self.assertEqual(rows[0]['venue_name'], 'Test Stadium')
        self.assertEqual(rows[0]['venue_city'], 'London')
        self.assertEqual(rows[0]['status'], 'finished')
        self.assertEqual(rows[0]['score_home'], 2)
        self.assertTrue(all(call[2]['force_refresh'] for call in calls))
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][1]['round'], 'Regular Season - 4')

    def test_nullable_provider_metadata_and_missing_score(self):
        row = capture.extract_fixture(
            self.fixture(2, 'NS', '2026-09-13T13:00:00Z', metadata=False, team_logos=False),
            self.league, 'Regular Season - 4', '2026-09-13T15:00:00Z')
        self.assertIsNone(row['country_flag_url'])
        self.assertIsNone(row['league_logo_url'])
        self.assertIsNone(row['home_team_logo_url'])
        self.assertIsNone(row['away_team_logo_url'])
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
             'kickoff_utc': '2026-09-13T16:00:00Z', 'home_team': 'H3',
             'home_team_logo_url': '', 'away_team': 'A3', 'away_team_logo_url': '',
             'status': 'scheduled', 'source_status': 'NS', 'score_home': '', 'score_away': '',
             'observed_at_utc': '2026-09-13T15:00:00Z'},
            {'fixture_id': '1', 'provider_league_id': '39', 'league_name': 'Premier League',
             'country': 'England', 'country_flag_url': '', 'league_logo_url': '',
             'season': '2026', 'round': 'Regular Season - 4',
             'kickoff_utc': '2026-09-13T12:00:00Z', 'home_team': 'H1',
             'home_team_logo_url': 'https://h1', 'away_team': 'A1',
             'away_team_logo_url': 'https://a1',
             'status': 'finished', 'source_status': 'FT', 'score_home': '2', 'score_away': '1',
             'observed_at_utc': '2026-09-13T15:00:00Z'},
            {'fixture_id': '2', 'provider_league_id': '39', 'league_name': 'Premier League',
             'country': 'England', 'country_flag_url': '', 'league_logo_url': '',
             'season': '2026', 'round': 'Regular Season - 4',
             'kickoff_utc': '2026-09-13T14:00:00Z', 'home_team': 'H2',
             'home_team_logo_url': '', 'away_team': 'A2', 'away_team_logo_url': '',
             'status': 'postponed', 'source_status': 'PST', 'score_home': '', 'score_away': '',
             'observed_at_utc': '2026-09-13T15:00:00Z'},
        ])
        db = self.ops / 'rounds.sqlite'
        conn = sqlite3.connect(db)
        conn.execute('CREATE TABLE pbk_meta (key TEXT, value TEXT)')
        conn.executemany('INSERT INTO pbk_meta VALUES (?,?)', [('built_at_utc', '2026-09-13T15:05:00Z')])
        builder.create_current_round_tables(conn, self.ops)
        projected = conn.execute(
            'SELECT home_team_logo_url, away_team_logo_url FROM current_round_matches '
            'WHERE fixture_id = ?', ('1',)).fetchone()
        self.assertEqual(tuple(projected), ('https://h1', 'https://a1'))
        conn.commit()
        conn.close()
        with patch.object(api, 'DB', db):
            code, payload = api.dispatch('/v1/rounds/current')
        self.assertEqual(code, 200)
        self.assertEqual([x['fixture_id'] for x in payload['leagues'][0]['matches']], ['1', '2', '3'])
        self.assertEqual(payload['leagues'][0]['matches'][0]['score'], {'home': 2, 'away': 1})
        self.assertEqual(payload['leagues'][0]['matches'][0]['home_team_logo_url'], 'https://h1')
        self.assertEqual(payload['leagues'][0]['matches'][0]['away_team_logo_url'], 'https://a1')
        self.assertIsNone(payload['leagues'][0]['matches'][1]['home_team_logo_url'])
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
             patch.object(capture, 'OPS', self.ops), \
             patch.object(capture, 'LEAGUES_OUT', self.ops / 'leagues.csv'), \
             patch.object(capture, 'FIXTURES_OUT', self.ops / 'fixtures.csv'), \
             patch.object(capture, 'META_OUT', self.ops / 'run.json'), \
             patch.object(capture.s53, 'api_get', get):
            capture.main()
        rows = capture.read_csv(self.ops / 'leagues.csv')
        self.assertEqual([row['status'] for row in rows], ['available', 'unavailable'])
        self.assertEqual(json.loads((self.ops / 'run.json').read_text())['api_calls'], 3)

    def test_empty_exact_round_is_unavailable(self):
        calls = []
        def get(path, params, **kwargs):
            calls.append((path, params, kwargs))
            return {'response': ['Regular Season - 4']} if path.endswith('rounds') else {'response': []}
        with self.assertRaisesRegex(RuntimeError, 'empty fixture list'):
            capture.capture_round(self.league, '2026-09-13T15:00:00Z', get)
        self.assertEqual(len(calls), 2)

    def test_current_round_uses_shared_daily_budget_and_persists_exhaustion(self):
        catalog = self.ops / 'catalog.csv'
        with catalog.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.league))
            writer.writeheader()
            writer.writerow(self.league)
        day = capture.datetime.now(capture.timezone.utc).date().isoformat()
        (self.ops / 'stage71_observation_state.json').write_text(
            json.dumps({'api_day': day, 'api_day_calls': 179}), encoding='utf-8')
        calls = []
        def get(path, params, **kwargs):
            calls.append((path, params, kwargs))
            return {'response': ['Regular Season - 4']} if path.endswith('rounds') else {
                'response': [self.fixture(1, 'FT', '2026-09-13T12:00:00Z', (1, 0))]
            }
        with patch.object(capture, 'CATALOG', catalog), \
             patch.object(capture, 'OPS', self.ops), \
             patch.object(capture, 'LEAGUES_OUT', self.ops / 'current_round_leagues.csv'), \
             patch.object(capture, 'FIXTURES_OUT', self.ops / 'current_round_fixtures.csv'), \
             patch.object(capture, 'META_OUT', self.ops / 'current_round_last_run.json'), \
             patch.dict(capture.os.environ, {'STAGE71_MAX_DAILY_API_CALLS': '180',
                                              'STAGE71_MAX_API_CALLS': '60'}), \
             patch.object(capture.s53, 'api_get', get):
            capture.main()
        state = json.loads((self.ops / 'stage71_observation_state.json').read_text())
        league = capture.read_csv(self.ops / 'current_round_leagues.csv')[0]
        self.assertEqual(state['api_day_calls'], 180)
        self.assertEqual(league['status'], 'unavailable')
        self.assertIn('budget exhausted', league['error'])
        self.assertEqual(len(calls), 1)

    def test_budget_exhaustion_preserves_previous_snapshot_and_stops_calls(self):
        catalog = self.ops / 'catalog.csv'
        leagues = [dict(self.league, api_league_id=str(39 + i),
                        api_league_name=f'League {i}') for i in range(3)]
        self.write('catalog.csv', leagues)
        self.write('current_round_leagues.csv', [
            {'provider_league_id': str(39 + i), 'league_name': f'League {i}',
             'country': 'England', 'country_flag_url': f'https://flag/{i}',
             'league_logo_url': f'https://logo/{i}', 'season': '2026',
             'round': 'Regular Season - 4', 'observed_at_utc': '2026-09-13T15:00:00Z',
             'status': 'available', 'error': ''}
            for i in range(3)
        ])
        self.write('current_round_fixtures.csv', [
            {'fixture_id': str(100 + i), 'provider_league_id': str(39 + i),
             'league_name': f'League {i}', 'country': 'England',
             'country_flag_url': f'https://flag/{i}', 'league_logo_url': f'https://logo/{i}',
             'season': '2026', 'round': 'Regular Season - 4',
             'kickoff_utc': f'2026-09-13T1{i}:00:00Z', 'home_team': f'H{i}',
             'home_team_logo_url': '', 'away_team': f'A{i}', 'away_team_logo_url': '',
             'status': 'finished', 'source_status': 'FT', 'score_home': '1',
             'score_away': '0', 'observed_at_utc': '2026-09-13T15:00:00Z'}
            for i in range(3)
        ])
        self.write('catalog.csv', leagues)
        calls = []
        def get(path, params, **kwargs):
            calls.append(params['league'])
            raise RuntimeError('Stage71 API budget exhausted; retry next run')
        with patch.object(capture, 'CATALOG', catalog), \
             patch.object(capture, 'OPS', self.ops), \
             patch.object(capture, 'LEAGUES_OUT', self.ops / 'current_round_leagues.csv'), \
             patch.object(capture, 'FIXTURES_OUT', self.ops / 'current_round_fixtures.csv'), \
             patch.object(capture, 'META_OUT', self.ops / 'current_round_last_run.json'), \
             patch.object(capture.s53, 'api_get', get):
            capture.main()
        served = capture.read_csv(self.ops / 'current_round_fixtures.csv')
        meta = json.loads((self.ops / 'current_round_last_run.json').read_text())
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(served), 3)
        self.assertEqual(meta['served_fixture_rows'], 3)
        self.assertTrue(meta['last_good_preserved'])
        self.assertEqual(meta['preserved_leagues'], 3)

    def test_transient_failure_preserves_only_failed_league_and_observation_time(self):
        catalog = self.ops / 'catalog.csv'
        leagues = [dict(self.league, api_league_id='39', api_league_name='Good'),
                   dict(self.league, api_league_id='140', api_league_name='Broken')]
        self.write('catalog.csv', leagues)
        self.write('current_round_leagues.csv', [
            {'provider_league_id': '39', 'league_name': 'Old Good', 'country': 'England',
             'country_flag_url': '', 'league_logo_url': '', 'season': '2026',
             'round': 'Old Round', 'observed_at_utc': '2026-09-13T15:00:00Z',
             'status': 'available', 'error': ''},
            {'provider_league_id': '140', 'league_name': 'Old Broken', 'country': 'Spain',
             'country_flag_url': '', 'league_logo_url': '', 'season': '2026',
             'round': 'Old Round', 'observed_at_utc': '2026-09-13T15:00:00Z',
             'status': 'available', 'error': ''},
        ])
        self.write('current_round_fixtures.csv', [
            {'fixture_id': '1', 'provider_league_id': '39', 'league_name': 'Old Good',
             'country': 'England', 'country_flag_url': '', 'league_logo_url': '',
             'season': '2026', 'round': 'Old Round', 'kickoff_utc': '2026-09-13T15:00:00Z',
             'home_team': 'Old H', 'home_team_logo_url': '', 'away_team': 'Old A',
             'away_team_logo_url': '', 'status': 'finished', 'source_status': 'FT',
             'score_home': '1', 'score_away': '0', 'observed_at_utc': '2026-09-13T15:00:00Z'},
            {'fixture_id': '2', 'provider_league_id': '140', 'league_name': 'Old Broken',
             'country': 'Spain', 'country_flag_url': '', 'league_logo_url': '',
             'season': '2026', 'round': 'Old Round', 'kickoff_utc': '2026-09-13T16:00:00Z',
             'home_team': 'Old H2', 'home_team_logo_url': '', 'away_team': 'Old A2',
             'away_team_logo_url': '', 'status': 'finished', 'source_status': 'FT',
             'score_home': '2', 'score_away': '0', 'observed_at_utc': '2026-09-13T15:00:00Z'},
        ])
        def get(path, params, **kwargs):
            if params['league'] == '140':
                raise RuntimeError('temporary provider failure')
            return {'response': [self.fixture(9, 'FT', '2026-09-14T12:00:00Z', (3, 2))]}
        with patch.object(capture, 'CATALOG', catalog), \
             patch.object(capture, 'OPS', self.ops), \
             patch.object(capture, 'LEAGUES_OUT', self.ops / 'current_round_leagues.csv'), \
             patch.object(capture, 'FIXTURES_OUT', self.ops / 'current_round_fixtures.csv'), \
             patch.object(capture, 'META_OUT', self.ops / 'current_round_last_run.json'), \
             patch.object(capture.s53, 'api_get', get):
            capture.main()
        served_leagues = {r['provider_league_id']: r for r in capture.read_csv(self.ops / 'current_round_leagues.csv')}
        served_fixtures = capture.read_csv(self.ops / 'current_round_fixtures.csv')
        self.assertNotEqual(served_leagues['39']['observed_at_utc'], '2026-09-13T15:00:00Z')
        self.assertEqual(
            next(row['fixture_id'] for row in served_fixtures if row['provider_league_id'] == '39'),
            '9',
        )
        self.assertEqual(served_leagues['140']['round'], 'Old Round')
        self.assertEqual({r['provider_league_id'] for r in served_fixtures}, {'39', '140'})
        self.assertEqual(served_leagues['140']['observed_at_utc'], '2026-09-13T15:00:00Z')

    def test_first_run_failure_can_serve_unavailable_league(self):
        catalog = self.ops / 'catalog.csv'
        self.write('catalog.csv', [self.league])
        def get(path, params, **kwargs):
            raise RuntimeError('provider unavailable')
        with patch.object(capture, 'CATALOG', catalog), \
             patch.object(capture, 'OPS', self.ops), \
             patch.object(capture, 'LEAGUES_OUT', self.ops / 'leagues.csv'), \
             patch.object(capture, 'FIXTURES_OUT', self.ops / 'fixtures.csv'), \
             patch.object(capture, 'META_OUT', self.ops / 'run.json'), \
             patch.object(capture.s53, 'api_get', get):
            capture.main()
        row = capture.read_csv(self.ops / 'leagues.csv')[0]
        self.assertEqual(row['status'], 'unavailable')
        self.assertEqual(capture.read_csv(self.ops / 'fixtures.csv'), [])

    def test_budget_forwards_force_refresh_kwargs(self):
        calls = []
        def get(path, params, **kwargs):
            calls.append(kwargs)
            return {'response': []}
        budget = audit.Budget(get, {}, capture.datetime.now(capture.timezone.utc))
        budget('/fixtures/rounds', {}, force_refresh=True)
        self.assertEqual(calls, [{'force_refresh': True}])


if __name__ == '__main__':
    unittest.main()
