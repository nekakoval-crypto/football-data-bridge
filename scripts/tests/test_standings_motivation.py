import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import standings_format_registry as format_registry
import standings_motivation as motivation


def srow(team_id, name, rank, points, played=37, description='', group='League', snapshot='s1', observed='2026-05-01T10:00:00Z'):
    return {
        'snapshot_id': snapshot, 'provider_league_id': '39', 'league_name': 'Test League',
        'season': '2026', 'observed_at_utc': observed, 'team_id': str(team_id),
        'team_name': name, 'rank': str(rank), 'points': str(points), 'played': str(played),
        'win': '', 'draw': '', 'lose': '', 'goals_for': '', 'goals_against': '',
        'goals_diff': '', 'form': '', 'group_name': group, 'description': description,
        'source': 'test',
    }


def fixture(home_id='1', away_id='2', kickoff='2026-05-01T12:00:00Z'):
    return {
        'fixture_id': '999', 'provider_league_id': '39', 'season': '2026',
        'kickoff_utc': kickoff, 'home_team_id': str(home_id), 'away_team_id': str(away_id),
        'home_team': f'Team {home_id}', 'away_team': f'Team {away_id}',
    }


class StandingsMotivationTests(unittest.TestCase):
    def test_post_kickoff_snapshot_is_rejected(self):
        rows = [srow(1, 'Team 1', 1, 80, observed='2026-05-01T13:00:00Z'),
                srow(2, 'Team 2', 2, 75, observed='2026-05-01T13:00:00Z')]
        payload = motivation.analyze_fixture(fixture(), rows, {'status': 'VERIFIED', 'total_games': 38})
        self.assertFalse(payload['coverage']['available'])
        self.assertFalse(payload['available'])
        self.assertTrue(payload['no_lookahead'])
        self.assertEqual(payload['coverage']['limitations'], ['LOOKAHEAD_FORBIDDEN'])
        self.assertTrue(payload['standings_context']['no_lookahead'])

    def test_pre_match_snapshot_is_frozen_and_auditable(self):
        rows = [srow(1, 'Team 1', 1, 80), srow(2, 'Team 2', 2, 75)]
        payload = motivation.analyze_fixture(fixture(), rows, {'status': 'VERIFIED', 'total_games': 38})
        self.assertTrue(payload['coverage']['available'])
        self.assertTrue(payload['available'])
        self.assertTrue(payload['no_lookahead'])
        self.assertEqual(payload['standings_context']['snapshot_id'], 's1')
        self.assertEqual(payload['standings_context']['age_seconds_at_cutoff'], 7200)
        self.assertTrue(payload['standings_context']['no_lookahead'])

    def test_title_clinch_requires_strict_points_separation(self):
        rows = [srow(1, 'Team 1', 1, 80), srow(2, 'Team 2', 2, 77)]
        payload = motivation.analyze_fixture(fixture(), rows, {'status': 'VERIFIED', 'total_games': 38})
        title = next(obj for obj in payload['home']['objectives'] if obj['type'] == 'TITLE')
        self.assertEqual(title['status'], 'LEADING')
        rows[1]['points'] = '76'
        payload = motivation.analyze_fixture(fixture(), rows, {'status': 'VERIFIED', 'total_games': 38})
        title = next(obj for obj in payload['home']['objectives'] if obj['type'] == 'TITLE')
        self.assertEqual(title['status'], 'POINTS_CLINCHED')
        self.assertNotEqual(payload['home']['primary_context'], 'TITLE')
        self.assertNotEqual(payload['home']['pressure'], 'HIGH')

    def test_title_elimination_uses_max_points_only_when_format_known(self):
        rows = [srow(1, 'Team 1', 1, 80, 37), srow(2, 'Team 2', 2, 70, 37)]
        known = motivation.analyze_fixture(fixture(), rows, {'status': 'VERIFIED', 'total_games': 38})
        away_title = next(obj for obj in known['away']['objectives'] if obj['type'] == 'TITLE')
        self.assertEqual(away_title['status'], 'ELIMINATED')
        unknown = motivation.analyze_fixture(fixture(), rows, {'status': 'UNKNOWN', 'total_games': None})
        away_title = next(obj for obj in unknown['away']['objectives'] if obj['type'] == 'TITLE')
        self.assertEqual(away_title['status'], 'UNKNOWN')
        self.assertIn('FORMAT_UNKNOWN', unknown['coverage']['limitations'])

    def test_registry_is_season_scoped_and_conservative(self):
        premier = format_registry.get_format('39', '2026')
        self.assertEqual(premier['status'], 'VERIFIED')
        self.assertEqual(premier['total_games'], 38)
        split = format_registry.get_format('179', '2026')
        self.assertEqual(split['status'], 'UNKNOWN')
        self.assertIsNone(split['total_games'])
        future = format_registry.get_format('39', '2027')
        self.assertEqual(future['status'], 'UNKNOWN')

    def test_default_registry_enables_safe_math_for_verified_league(self):
        rows = [srow(1, 'Team 1', 1, 80, 37), srow(2, 'Team 2', 2, 70, 37)]
        payload = motivation.analyze_fixture(fixture(), rows)
        self.assertEqual(payload['home']['format']['format_status'], 'VERIFIED')
        self.assertEqual(payload['home']['format']['total_games'], 38)
        self.assertNotIn('FORMAT_UNKNOWN', payload['coverage']['limitations'])
        away_title = next(obj for obj in payload['away']['objectives'] if obj['type'] == 'TITLE')
        self.assertEqual(away_title['status'], 'ELIMINATED')

    def test_europe_and_relegation_descriptions_are_conservative(self):
        rows = [
            srow(1, 'Team 1', 1, 80, description='Champions League'),
            srow(2, 'Team 2', 2, 74, description='Europa League'),
            srow(3, 'Team 3', 3, 70, description=''),
            srow(4, 'Team 4', 4, 66, description='Relegation Play-off'),
            srow(5, 'Team 5', 5, 60, description='Relegation'),
        ]
        payload = motivation.analyze_fixture(fixture('2', '5'), rows, {'status': 'VERIFIED', 'total_games': 38})
        self.assertTrue(any(obj['type'] == 'EUROPA_LEAGUE' for obj in payload['home']['objectives']))
        relegation = next(obj for obj in payload['away']['objectives'] if obj['type'] == 'RELEGATION')
        self.assertIn(relegation['status'], {'CAN_ESCAPE', 'RELEGATED_ON_POINTS'})
        self.assertEqual(relegation['zone_state'], 'IN_RELEGATION_ZONE')
        self.assertIn('IN_RELEGATION_ZONE', payload['away']['reason_codes'])

    def test_championship_playoff_is_preserved_as_distinct_context(self):
        rows = [
            srow(1, 'Team 1', 1, 70, description='Championship Play-off'),
            srow(2, 'Team 2', 2, 68, description='Championship Play-off'),
            srow(3, 'Team 3', 3, 66, description=''),
        ]
        payload = motivation.analyze_fixture(fixture('2', '3'), rows, {'status': 'VERIFIED', 'total_games': 38})
        home = next(obj for obj in payload['home']['objectives'] if obj['type'] == 'CHAMPIONSHIP_PLAYOFF')
        away = next(obj for obj in payload['away']['objectives'] if obj['type'] == 'CHAMPIONSHIP_PLAYOFF')
        self.assertIn(home['status'], {'IN_ZONE', 'POINTS_SECURED'})
        self.assertIn(away['status'], {'IN_RACE', 'ELIMINATED'})
        self.assertIsNotNone(payload['away']['standings']['points_to_playoff_boundary'])

    def test_neighbor_and_boundary_distances_are_directional(self):
        rows = [
            srow(1, 'Team 1', 1, 80, description='Champions League'),
            srow(2, 'Team 2', 2, 75, description=''),
            srow(3, 'Team 3', 3, 72, description='Relegation Play-off'),
            srow(4, 'Team 4', 4, 68, description='Relegation'),
        ]
        payload = motivation.analyze_fixture(fixture('2', '3'), rows, {'status': 'VERIFIED', 'total_games': 38})
        facts = payload['home']['standings']
        self.assertEqual(facts['points_to_first'], 5)
        self.assertEqual(facts['points_to_previous_rank'], 5)
        self.assertEqual(facts['points_to_next_rank'], 3)
        self.assertIsNotNone(facts['points_to_relevant_boundary'])

    def test_unknown_description_does_not_invent_zone(self):
        self.assertEqual(motivation.description_objectives('Mid table'), [])
        self.assertEqual(motivation.description_objectives(''), [])

    def test_same_gap_early_is_not_high_but_late_can_be_high(self):
        rows_early = [
            srow(1, 'Team 1', 1, 30, played=10, description='Champions League'),
            srow(2, 'Team 2', 2, 28, played=10, description=''),
        ]
        early = motivation.analyze_fixture(fixture(), rows_early, {'status': 'VERIFIED', 'total_games': 38})
        self.assertNotEqual(early['away']['pressure'], 'HIGH')
        rows_late = [
            srow(1, 'Team 1', 1, 80, played=35, description='Champions League'),
            srow(2, 'Team 2', 2, 78, played=35, description=''),
        ]
        late = motivation.analyze_fixture(fixture(), rows_late, {'status': 'VERIFIED', 'total_games': 38})
        self.assertEqual(late['away']['season_phase'], 'RUN_IN')
        self.assertEqual(late['away']['pressure'], 'HIGH')

    def test_groups_are_never_compared_across_each_other(self):
        rows = [srow(1, 'Team 1', 1, 10, group='A'), srow(2, 'Team 2', 1, 10, group='B')]
        payload = motivation.analyze_fixture(fixture(), rows)
        self.assertFalse(payload['coverage']['available'])
        self.assertEqual(payload['coverage']['limitations'], ['GROUP_AMBIGUOUS'])

    def test_exact_name_fallback_is_explicitly_partial(self):
        rows = [srow(1, 'Alpha', 1, 20), srow(2, 'Beta', 2, 18)]
        f = fixture('', '')
        f['home_team'], f['away_team'] = 'Alpha', 'Beta'
        payload = motivation.analyze_fixture(f, rows)
        self.assertTrue(payload['coverage']['available'])
        self.assertEqual(payload['coverage']['status'], 'PARTIAL')
        self.assertIn('TEAM_ID_MISSING_NAME_MATCH', payload['coverage']['limitations'])

    def test_none_verified_never_claims_unmotivated(self):
        rows = [srow(1, 'Team 1', 1, 20, played=5), srow(2, 'Team 2', 8, 10, played=5)]
        payload = motivation.analyze_fixture(fixture(), rows)
        self.assertNotIn('unmotivated', str(payload).lower())
        self.assertIn(payload['away']['pressure'], {'NONE_VERIFIED', 'LOW', 'MEDIUM'})


if __name__ == '__main__':
    unittest.main()
