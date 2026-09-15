import json
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import player_grade_context as context


def xi(prefix):
    return [
        {'id': f'{prefix}{i}', 'name': f'{prefix} Player {i}', 'number': i, 'pos': 'G' if i == 1 else ('D' if i <= 5 else 'M')}
        for i in range(1, 12)
    ]


class PlayerGradeContextTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.execute('''CREATE TABLE current_round_matches (
            fixture_id TEXT, kickoff_utc TEXT, home_team TEXT, away_team TEXT,
            home_team_logo_url TEXT, away_team_logo_url TEXT
        )''')
        self.conn.execute("""INSERT INTO current_round_matches VALUES (
            '999','2026-09-20T18:00:00Z','Home','Away',
            'https://media.api-sports.io/football/teams/10.png',
            'https://media.api-sports.io/football/teams/20.png')""")
        self.conn.execute('''CREATE TABLE player_grade_snapshots (
            fixture_id TEXT, player_id TEXT, player_name TEXT, team_id TEXT,
            kickoff_utc TEXT, observed_at_utc TEXT, overall_grade TEXT, source TEXT
        )''')
        for i, value in enumerate((6.0, 7.0, 8.0), start=1):
            self.conn.execute('INSERT INTO player_grade_snapshots VALUES (?,?,?,?,?,?,?,?)',
                              (f'h{i}', 'H2', 'H Player 2', '10', f'2026-09-0{i}T18:00:00Z',
                               f'2026-09-0{i}T20:00:00Z', str(value), 'TEST'))
        self.conn.execute("INSERT INTO player_grade_snapshots VALUES ('future','H2','H Player 2','10','2026-09-21T18:00:00Z','2026-09-21T20:00:00Z','10.0','TEST')")
        self.conn.execute("INSERT INTO player_grade_snapshots VALUES ('late_capture','H2','H Player 2','10','2026-09-10T18:00:00Z','2026-09-20T20:00:00Z','9.9','TEST')")
        self.conn.execute('''CREATE TABLE raw_rotation_snapshots (
            captured_at_utc TEXT, home_team_id TEXT, away_team_id TEXT,
            home_current_xi_json TEXT, away_current_xi_json TEXT
        )''')
        old = [{'id': 'H12', 'name': 'Known Reserve', 'number': 22, 'pos': 'M'}]
        self.conn.execute('INSERT INTO raw_rotation_snapshots VALUES (?,?,?,?,?)',
                          ('2026-09-10T10:00:00Z', '10', '20', json.dumps(old), '[]'))
        future = [{'id': 'H99', 'name': 'Future Leak', 'number': 99, 'pos': 'F'}]
        self.conn.execute('INSERT INTO raw_rotation_snapshots VALUES (?,?,?,?,?)',
                          ('2026-09-21T10:00:00Z', '10', '20', json.dumps(future), '[]'))
        self.conn.execute('''CREATE TABLE raw_team_rosters (
            team_id TEXT, team_name TEXT, captured_at_utc TEXT, player_id TEXT,
            player_name TEXT, age TEXT, number TEXT, position TEXT, photo_url TEXT, source TEXT
        )''')
        self.conn.execute("INSERT INTO raw_team_rosters VALUES ('10','Home','2026-09-15T10:00:00Z','H13','Roster Defender','24','13','Defender','','TEST')")
        self.conn.execute("INSERT INTO raw_team_rosters VALUES ('20','Away','2026-09-15T10:00:00Z','A13','Roster Attacker','22','19','Attacker','','TEST')")
        # Captured after target kickoff: must not leak into this pre-match card.
        self.conn.execute("INSERT INTO raw_team_rosters VALUES ('10','Home','2026-09-20T20:00:00Z','H98','Late Roster Leak','20','98','Attacker','','TEST')")

    def lineup(self):
        return {
            'available': True,
            'home': {'team_id': '10', 'team_name': 'Home', 'status': 'EXPECTED', 'formation': '4-3-3', 'starting_xi': xi('H')},
            'away': {'team_id': '20', 'team_name': 'Away', 'status': 'EXPECTED', 'formation': '4-2-3-1', 'starting_xi': xi('A')},
        }

    def test_form_grade_strictly_uses_prior_matches_and_available_capture_time(self):
        payload = context.build_player_grade_context(self.conn, '999', self.lineup())
        grade = payload['home']['grades_by_player']['H2']
        self.assertEqual(grade['form_5'], 7.0)
        self.assertEqual(grade['sample_5'], 3)
        self.assertNotEqual(grade['current_grade'], 10.0)
        self.assertNotEqual(grade['current_grade'], 9.9)
        self.assertLessEqual(grade['last_grade_observed_at_utc'], '2026-09-20T18:00:00Z')
        self.assertTrue(payload['no_lookahead'])
        self.assertTrue(payload['available'])

    def test_known_player_pool_combines_roster_and_pre_kickoff_rotation(self):
        payload = context.build_player_grade_context(self.conn, '999', self.lineup())
        ids = {row['id'] for row in payload['home']['player_pool']}
        self.assertIn('H12', ids)
        self.assertIn('H13', ids)
        self.assertNotIn('H99', ids)
        self.assertNotIn('H98', ids)
        self.assertTrue(payload['home']['roster_available'])
        self.assertGreaterEqual(payload['home']['pool_size'], 13)

    def test_roster_pool_works_without_expected_or_official_xi_using_logo_team_ids(self):
        no_lineup = {
            'available': False,
            'home': {'team_name': 'Home', 'status': 'UNKNOWN', 'starting_xi': []},
            'away': {'team_name': 'Away', 'status': 'UNKNOWN', 'starting_xi': []},
        }
        payload = context.build_player_grade_context(self.conn, '999', no_lineup)
        self.assertEqual(payload['home']['team_id'], '10')
        self.assertEqual(payload['away']['team_id'], '20')
        self.assertIn('H13', {row['id'] for row in payload['home']['player_pool']})
        self.assertIn('A13', {row['id'] for row in payload['away']['player_pool']})
        self.assertTrue(payload['coverage']['roster_available'])

    def test_missing_grade_history_is_honest_and_does_not_zero_players(self):
        self.conn.execute('DELETE FROM player_grade_snapshots')
        payload = context.build_player_grade_context(self.conn, '999', self.lineup())
        self.assertFalse(payload['available'])
        self.assertEqual(payload['home']['xi_quality']['covered_players'], 0)
        self.assertIsNone(payload['home']['xi_quality']['xi_quality'])
        self.assertIn('PLAYER_GRADE_HISTORY_UNAVAILABLE', payload['coverage']['limitations'])
        self.assertNotIn('TEAM_ROSTER_UNAVAILABLE', payload['coverage']['limitations'])
        self.assertFalse(payload['probability_mutation'])
        self.assertFalse(payload['eligibility_mutation'])
        self.assertFalse(payload['stake_changes'])


if __name__ == '__main__':
    unittest.main()
