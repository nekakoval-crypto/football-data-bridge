import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage71_observation_audit as audit
import stage77_player_stats_capture as stage77


NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


def fixture(fid='100', status='finished', source='FT', kickoff='2026-09-15T09:00:00Z'):
    return {
        'fixture_id': fid,
        'status': status,
        'source_status': source,
        'kickoff_utc': kickoff,
    }


def provider_payload(player_id=7):
    return {
        'paging': {'current': 1, 'total': 1},
        'errors': [],
        'response': [{
            'team': {'id': 10, 'name': 'Alpha'},
            'players': [{
                'player': {'id': player_id, 'name': 'A Player'},
                'statistics': [{
                    'games': {'minutes': 90, 'position': 'M', 'rating': '7.5'},
                    'shots': {'total': 2, 'on': 1},
                    'goals': {'total': 1, 'assists': 1},
                    'passes': {'total': 55, 'key': 3, 'accuracy': '88%'},
                    'tackles': {'total': 2, 'blocks': 0, 'interceptions': 1},
                    'duels': {'total': 8, 'won': 5},
                    'dribbles': {'attempts': 3, 'success': 2},
                    'fouls': {'drawn': 2, 'committed': 1},
                    'cards': {'yellow': 0, 'red': 0},
                    'penalty': {'won': 0, 'commited': 0, 'scored': 0, 'missed': 0},
                }],
            }],
        }],
    }


class Stage77Tests(unittest.TestCase):
    def test_candidates_are_terminal_past_and_not_already_captured(self):
        rows = [
            fixture('100'),
            fixture('101', status='live', source='2H'),
            fixture('102', kickoff='2026-09-15T15:00:00Z'),
            fixture('103', status='finished', source='AET'),
        ]
        selected = stage77.candidate_fixtures(rows, {'100'}, NOW, 10)
        self.assertEqual([x['fixture_id'] for x in selected], ['103'])

    def test_provider_payload_normalizes_stats_and_grade_with_research_contract(self):
        stats, grades = stage77.normalize_fixture_players(provider_payload(), fixture(), stage77.iso(NOW))
        self.assertEqual(len(stats), 1)
        self.assertEqual(len(grades), 1)
        self.assertEqual(stats[0]['fixture_id'], '100')
        self.assertEqual(stats[0]['team_id'], '10')
        self.assertEqual(stats[0]['player_id'], '7')
        self.assertEqual(stats[0]['source'], 'API_FOOTBALL_FIXTURES_PLAYERS')
        self.assertIsNotNone(grades[0]['overall_grade'])
        self.assertEqual(grades[0]['research_only'], 'true')
        self.assertEqual(grades[0]['probability_mutation'], 'false')
        self.assertEqual(grades[0]['eligibility_mutation'], 'false')
        self.assertEqual(grades[0]['stake_changes'], 'false')

    def test_capture_is_idempotent_and_skips_already_completed_fixture(self):
        calls = []
        def get(path, params=None, **kwargs):
            calls.append((path, params, kwargs))
            return provider_payload()
        first = stage77.capture([fixture()], [], [], get, NOW, 4)
        self.assertEqual(first['captured_fixtures'], 1)
        self.assertEqual(len(first['stats']), 1)
        self.assertEqual(len(first['grades']), 1)
        second = stage77.capture([fixture()], first['stats'], first['grades'], get, NOW, 4)
        self.assertEqual(second['candidate_fixtures'], 0)
        self.assertEqual(second['captured_fixtures'], 0)
        self.assertEqual(len(second['stats']), 1)
        self.assertEqual(len(second['grades']), 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], '/fixtures/players')
        self.assertFalse(calls[0][2]['force_refresh'])

    def test_protected_budget_defers_before_provider_call(self):
        state = {'api_day': '2026-09-15', 'api_day_calls': 170}
        real_calls = []
        def underlying(path, params=None, **kwargs):
            real_calls.append(path)
            return provider_payload()
        budget = audit.Budget(underlying, state, NOW, limit=4, daily_limit=180, protected_calls=12)
        result = stage77.capture([fixture()], [], [], budget, NOW, 4)
        self.assertEqual(result['captured_fixtures'], 0)
        self.assertEqual(result['deferred_fixtures'], 1)
        self.assertTrue(any('protected API reserve' in x for x in result['warnings']))
        self.assertEqual(real_calls, [])
        self.assertEqual(state['api_day_calls'], 170)

    def test_merge_rows_replaces_same_fixture_team_player_instead_of_duplicating(self):
        old = [{'fixture_id': '100', 'team_id': '10', 'player_id': '7', 'overall_grade': '6.0'}]
        new = [{'fixture_id': '100', 'team_id': '10', 'player_id': '7', 'overall_grade': '7.2'}]
        merged = stage77.merge_rows(old, new)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['overall_grade'], '7.2')

    def test_atomic_csv_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'grades.csv'
            row = {field: '' for field in stage77.GRADE_FIELDS}
            row.update({'fixture_id': '100', 'team_id': '10', 'player_id': '7', 'overall_grade': '7.1'})
            stage77.write_csv_atomic(path, stage77.GRADE_FIELDS, [row])
            loaded = stage77.read_csv(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]['player_id'], '7')
            self.assertFalse(path.with_suffix('.csv.tmp').exists())

    def test_protected_call_plan_includes_live_round_standings_and_safety(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(audit, 'live_forecast', return_value={'status':'OPEN','reserved_live_calls':9}), \
             patch.object(audit, 'current_round_forecast', return_value=32), \
             patch.dict(os.environ, {'STAGE77_STANDINGS_RESERVE_CALLS':'16','STAGE77_SAFETY_RESERVE_CALLS':'8'}):
            result = stage77.protected_calls(Path(temp), NOW)
        self.assertEqual(result['total'], 65)
        self.assertEqual(result['live'], 9)
        self.assertEqual(result['current_round'], 32)
        self.assertEqual(result['standings'], 16)
        self.assertEqual(result['safety'], 8)

    def test_no_data_retry_uses_exponential_cooldown(self):
        row = fixture('200')
        row.update({
            'attempt_count': '2',
            'last_attempt_result': 'NO_DATA',
            'last_attempt_at_utc': '2026-09-15T05:00:00Z',
        })
        self.assertEqual(stage77.retry_cooldown_hours(row), 12.0)
        blocked = stage77.candidate_fixtures([row], set(), NOW, 10)
        self.assertEqual(blocked, [])
        later = datetime(2026, 9, 15, 17, 1, tzinfo=timezone.utc)
        ready = stage77.candidate_fixtures([row], set(), later, 10)
        self.assertEqual([x['fixture_id'] for x in ready], ['200'])

    def test_error_retry_uses_shorter_cooldown(self):
        row = fixture('201')
        row.update({
            'attempt_count': '2',
            'last_attempt_result': 'ERROR',
            'last_attempt_at_utc': '2026-09-15T10:30:00Z',
        })
        self.assertEqual(stage77.retry_cooldown_hours(row), 2.0)
        self.assertEqual(stage77.candidate_fixtures([row], set(), NOW, 10), [])


if __name__ == '__main__':
    unittest.main()
