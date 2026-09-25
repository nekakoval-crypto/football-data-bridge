import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage79_team_roster_capture as s79


class Stage79RosterTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 15, 14, 0, tzinfo=timezone.utc)

    def fixtures(self):
        return [
            {
                'fixture_id': '1', 'provider_league_id': '140',
                'kickoff_utc': '2026-09-15T19:30:00Z',
                'home_team': 'Elche', 'away_team': 'Real Madrid',
                'home_team_logo_url': 'https://media.api-sports.io/football/teams/797.png',
                'away_team_logo_url': 'https://media.api-sports.io/football/teams/541.png',
            },
            {
                'fixture_id': '2', 'provider_league_id': '103',
                'kickoff_utc': '2026-09-16T18:00:00Z',
                'home_team': 'Other Home', 'away_team': 'Other Away',
                'home_team_logo_url': 'https://media.api-sports.io/football/teams/1001.png',
                'away_team_logo_url': 'https://media.api-sports.io/football/teams/1002.png',
            },
        ]

    def test_team_id_falls_back_to_logo_url(self):
        row = self.fixtures()[0]
        self.assertEqual(s79.team_id_from_fixture(row, 'home'), '797')
        self.assertEqual(s79.team_id_from_fixture(row, 'away'), '541')

    def test_big5_upcoming_teams_are_prioritized_and_fresh_roster_is_skipped(self):
        existing = [{
            'team_id': '797', 'captured_at_utc': '2026-09-14T12:00:00Z',
            'player_id': 'p1', 'player_name': 'Fresh Player'
        }]
        rows = s79.candidate_teams(self.fixtures(), existing, self.now, 3)
        self.assertEqual(rows[0]['team_id'], '541')
        self.assertNotIn('797', {x['team_id'] for x in rows})
        self.assertIn('1001', {x['team_id'] for x in rows})

    def test_priority_ids_override_normal_order(self):
        rows = s79.candidate_teams(self.fixtures(), [], self.now, 2, priority_team_ids=['1002'])
        self.assertEqual(rows[0]['team_id'], '1002')

    def test_normalize_and_replace_team_snapshot(self):
        payload = {
            'response': [{
                'team': {'id': 541, 'name': 'Real Madrid'},
                'players': [
                    {'id': 10, 'name': 'A Player', 'age': 25, 'number': 7, 'position': 'Attacker', 'photo': 'x'},
                    {'id': 11, 'name': 'B Player', 'age': 28, 'number': 1, 'position': 'Goalkeeper', 'photo': 'y'},
                ],
            }]
        }
        incoming = s79.normalize_squad(payload, '541', 'Real Madrid', '2026-09-15T14:00:00Z')
        self.assertEqual(len(incoming), 2)
        self.assertEqual(incoming[0]['source'], 'api-football:/players/squads')
        existing = [
            {'team_id': '541', 'player_id': 'old', 'player_name': 'Old'},
            {'team_id': '797', 'player_id': 'keep', 'player_name': 'Keep'},
        ]
        merged = s79.replace_team_rosters(existing, incoming)
        self.assertNotIn('old', {x.get('player_id') for x in merged})
        self.assertIn('keep', {x.get('player_id') for x in merged})
        self.assertEqual(sum(x.get('team_id') == '541' for x in merged), 2)

    def test_transfer_aware_roster_ttl(self):
        stable_now = datetime(2026, 9, 15, 14, 0, tzinfo=timezone.utc)
        winter_now = datetime(2026, 1, 20, 14, 0, tzinfo=timezone.utc)
        self.assertFalse(s79.transfer_sensitive(stable_now))
        self.assertTrue(s79.transfer_sensitive(winter_now))
        self.assertEqual(
            s79.effective_roster_ttl_days(
                stable_now,
                stable_days=28,
                sensitive_days=3,
            ),
            28,
        )
        self.assertEqual(
            s79.effective_roster_ttl_days(
                winter_now,
                stable_days=28,
                sensitive_days=3,
            ),
            3,
        )

    def test_capture_is_idempotent_and_uses_passed_ttl(self):
        calls = []
        def get(path, params, **kwargs):
            calls.append((path, params, kwargs))
            tid = params['team']
            return {'response': [{'team': {'id': int(tid), 'name': f'Team {tid}'}, 'players': [
                {'id': int(tid) * 10 + 1, 'name': 'Player', 'position': 'Defender'}
            ]}], 'paging': {'current': 1, 'total': 1}, 'errors': []}
        first = s79.capture(self.fixtures(), [], get, self.now, 4, ttl_days=28)
        self.assertEqual(len(first['captured_teams']), 4)
        self.assertEqual(calls[0][0], '/players/squads')
        self.assertEqual(calls[0][2]['ttl_seconds'], 28 * 24 * 3600)
        second = s79.capture(self.fixtures(), first['rows'], get, self.now, 4, ttl_days=28)
        self.assertEqual(second['candidate_teams'], 0)
        self.assertEqual(len(calls), 4)


if __name__ == '__main__':
    unittest.main()
