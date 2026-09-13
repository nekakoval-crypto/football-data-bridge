import csv
import gc
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage72_build_data_layer as builder
import stage73_internal_api as api


class TodayLiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Path(self.temp.name)
        self.addCleanup(gc.collect)
        self.addCleanup(self.temp.cleanup)

    def write_csv(self, name, fields, rows):
        with (self.ops / name).open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_api_football_statuses_are_normalized_without_loss(self):
        expected = {
            'TBD': 'scheduled', 'NS': 'scheduled', 'SCHEDULED': 'scheduled',
            '1H': 'live', 'HT': 'live', '2H': 'live', 'ET': 'live',
            'BT': 'live', 'P': 'live', 'LIVE': 'live',
            'FT': 'finished', 'AET': 'finished', 'PEN': 'finished',
            'SETTLED': 'finished', 'PST': 'postponed', 'POSTPONED': 'postponed',
            'CANC': 'cancelled', 'CANCELLED': 'cancelled',
            'SUSP': 'suspended', 'INT': 'interrupted', 'ABD': 'abandoned',
            'AWD': 'awarded', 'WO': 'walkover',
        }
        for raw, normalized in expected.items():
            with self.subTest(raw=raw):
                self.assertEqual(builder.today_status(raw), normalized)
        self.assertEqual(builder.today_status('PROVIDER_ADDED_STATUS'), 'unknown')

    def test_unknown_source_status_is_preserved_in_projection(self):
        fields = ['api_fixture_id', 'match_date', 'kickoff_time', 'league',
                  'home_team', 'away_team', 'fixture_status', 'screened_at_utc']
        self.write_csv('latest_screen.csv', fields, [{
            'api_fixture_id': '77', 'match_date': '2026-09-13',
            'kickoff_time': '15:00', 'league': 'A', 'home_team': 'Home',
            'away_team': 'Away', 'fixture_status': 'PROVIDER_ADDED_STATUS',
            'screened_at_utc': '2026-09-13T14:00:00Z'}])
        row = builder.today_projection(self.ops, '2026-09-13')[0]
        self.assertEqual(row['status'], 'unknown')
        self.assertEqual(row['source_status'], 'PROVIDER_ADDED_STATUS')

    def test_projection_preserves_states_and_optional_unknowns(self):
        fields = ['api_fixture_id', 'match_date', 'kickoff_time', 'league',
                  'home_team', 'away_team', 'fixture_status', 'home_goals', 'away_goals',
                  'screened_at_utc']
        rows = [
            {'api_fixture_id': '1', 'match_date': '2026-09-13', 'kickoff_time': '10:00',
             'league': 'A', 'home_team': 'Home 1', 'away_team': 'Away 1',
             'fixture_status': 'NS', 'screened_at_utc': '2026-09-13T09:00:00Z'},
            {'api_fixture_id': '2', 'match_date': '2026-09-13', 'kickoff_time': '11:00',
             'league': 'A', 'home_team': 'Home 2', 'away_team': 'Away 2',
             'fixture_status': '1H', 'screened_at_utc': '2026-09-13T10:00:00Z'},
            {'api_fixture_id': '3', 'match_date': '2026-09-13', 'kickoff_time': '12:00',
             'league': 'A', 'home_team': 'Home 3', 'away_team': 'Away 3',
             'fixture_status': 'FT', 'home_goals': '2', 'away_goals': '1',
             'screened_at_utc': '2026-09-13T13:00:00Z'},
            {'api_fixture_id': '4', 'match_date': '2026-09-13', 'kickoff_time': '13:00',
             'league': 'A', 'home_team': 'Home 4', 'away_team': 'Away 4',
             'fixture_status': 'SOMETHING_NEW'},
            {'api_fixture_id': '5', 'match_date': '2026-09-13', 'kickoff_time': '14:00',
             'league': '', 'home_team': '', 'away_team': ''},
        ]
        self.write_csv('latest_screen.csv', fields, rows)
        event_fields = ['event_id', 'api_fixture_id', 'observed_at_utc',
                        'event_type', 'old_value', 'new_value', 'details']
        self.write_csv('fixture_events.csv', event_fields, [
            {'event_id': '4|STATUS', 'api_fixture_id': '4',
             'observed_at_utc': '2026-09-13T13:30:00Z',
             'event_type': 'STATUS_CHANGE', 'old_value': 'NS', 'new_value': 'PST'},
            {'event_id': '5|STATUS', 'api_fixture_id': '5',
             'observed_at_utc': '2026-09-13T13:31:00Z',
             'event_type': 'STATUS_CHANGE', 'old_value': 'NS', 'new_value': 'CANC'},
        ])
        projected = builder.today_projection(self.ops, '2026-09-13')
        statuses = {row['fixture_id']: row['status'] for row in projected}
        self.assertEqual(statuses, {'1': 'scheduled', '2': 'live', '3': 'finished',
                                    '4': 'postponed', '5': 'cancelled'})
        finished = next(row for row in projected if row['fixture_id'] == '3')
        self.assertEqual(finished['score'], {'home': '2', 'away': '1'})
        self.assertIsNone(next(row for row in projected if row['fixture_id'] == '5')['competition'])

    def test_api_contract_is_read_only_deterministic_and_has_freshness_coverage(self):
        db = self.ops / 'db.sqlite'
        conn = sqlite3.connect(db)
        try:
            conn.execute('CREATE TABLE pbk_meta (key TEXT, value TEXT)')
            conn.executemany('INSERT INTO pbk_meta VALUES (?, ?)', [
                ('built_at_utc', '2026-09-13T15:00:00Z'), ('schema_version', '8')])
            conn.execute('''CREATE TABLE today_matches (
                fixture_id TEXT, competition TEXT, home_team TEXT, away_team TEXT,
                kickoff_utc TEXT, status TEXT, source_status TEXT, score TEXT,
                observed_at_utc TEXT, source TEXT
            )''')
            conn.execute('''INSERT INTO today_matches VALUES
                ('1','A','Home','Away','2026-09-13T10:00:00Z','live',
                 '1H','null','2026-09-13T14:00:00Z','stage53_stage72_projection')''')
            conn.commit()
        finally:
            conn.close()
        with patch.object(api, 'DB', db):
            with patch('urllib.request.urlopen', side_effect=AssertionError('provider polling forbidden')):
                first = api.dispatch('/v1/today')
                second = api.dispatch('/v1/today')
        self.assertEqual(first[0], 200)
        self.assertEqual(first, second)
        payload = first[1]
        self.assertFalse(payload['coverage']['live_completeness_guaranteed'])
        self.assertFalse(payload['provider_polling'])
        self.assertEqual(payload['matches'][0]['freshness_status'], 'fresh')
        self.assertIn('observed_at_utc', payload['matches'][0])
        self.assertEqual(payload['matches'][0]['source_status'], '1H')
        self.assertIsNone(payload['matches'][0]['score'])
        self.assertEqual(payload['day_basis'], 'UTC')

    def test_duplicate_fixture_uses_newest_observation_and_event_retention(self):
        fields = ['api_fixture_id', 'match_date', 'kickoff_time', 'league',
                  'home_team', 'away_team', 'fixture_status', 'screened_at_utc']
        self.write_csv('latest_screen.csv', fields, [{
            'api_fixture_id': '123', 'match_date': '2026-09-13',
            'kickoff_time': '15:00', 'league': 'A', 'home_team': 'Home',
            'away_team': 'Away', 'fixture_status': 'NS',
            'screened_at_utc': '2026-09-13T14:00:00Z'}])
        self.write_csv('user_forward_view.csv', fields, [{
            'api_fixture_id': '123', 'match_date': '2026-09-13',
            'kickoff_time': '15:00', 'league': 'A', 'home_team': 'Home',
            'away_team': 'Away', 'fixture_status': 'NS',
            'screened_at_utc': '2026-09-13T15:05:00Z'}])
        event_fields = ['event_id', 'api_fixture_id', 'observed_at_utc',
                        'event_type', 'old_value', 'new_value', 'details']
        self.write_csv('fixture_events.csv', event_fields, [{
            'event_id': '123|STATUS', 'api_fixture_id': '123',
            'observed_at_utc': '2026-09-13T15:10:00Z',
            'event_type': 'STATUS_CHANGE', 'old_value': 'NS',
            'new_value': 'PST', 'details': ''}])
        rows = builder.today_projection(self.ops, '2026-09-13')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'postponed')
        self.assertEqual(rows[0]['observed_at_utc'], '2026-09-13T15:10:00Z')
        (self.ops / 'latest_screen.csv').unlink()
        rows = builder.today_projection(self.ops, '2026-09-13')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'postponed')

    def test_stale_scheduled_record_cannot_resurrect_finished_fixture(self):
        fields = ['api_fixture_id', 'match_date', 'kickoff_time', 'league',
                  'home_team', 'away_team', 'fixture_status', 'screened_at_utc']
        self.write_csv('latest_screen.csv', fields, [{
            'api_fixture_id': '9', 'match_date': '2026-09-13',
            'kickoff_time': '15:00', 'league': 'A', 'home_team': 'Home',
            'away_team': 'Away', 'fixture_status': 'NS',
            'screened_at_utc': '2026-09-13T14:00:00Z'}])
        event_fields = ['event_id', 'api_fixture_id', 'observed_at_utc',
                        'event_type', 'old_value', 'new_value', 'details']
        self.write_csv('fixture_events.csv', event_fields, [{
            'event_id': '9|STATUS', 'api_fixture_id': '9',
            'observed_at_utc': '2026-09-13T16:00:00Z',
            'event_type': 'STATUS_CHANGE', 'old_value': 'NS',
            'new_value': 'FT', 'details': ''}])
        rows = builder.today_projection(self.ops, '2026-09-13')
        self.assertEqual(rows[0]['status'], 'finished')


if __name__ == '__main__':
    unittest.main()
