import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import manual_lineup_scenario as scenario
import player_grade as grade


def xi(prefix, formation_pos='M'):
    return [
        {'id': f'{prefix}{i}', 'name': f'{prefix}{i}', 'number': i, 'pos': 'G' if i == 1 else formation_pos}
        for i in range(1, 12)
    ]


def lineup_context():
    return {
        'home': {'official': None, 'expected': {'formation':'4-3-3','xi':xi('H'),'source':'history'}},
        'away': {'official': {'formation':'4-2-3-1','xi':xi('A'),'source':'provider'}, 'expected': None},
    }


class PlayerGradeTests(unittest.TestCase):
    def test_api_football_normalization(self):
        row = grade.normalize_api_football_player(
            {'id': 7, 'name': 'Seven'},
            {'games': {'minutes': 90, 'position': 'M', 'rating': '7.2'},
             'shots': {'total': 2, 'on': 1}, 'goals': {'total': 0, 'assists': 1},
             'passes': {'total': 55, 'key': 3, 'accuracy': '86%'},
             'tackles': {'total': 2, 'blocks': 1, 'interceptions': 1},
             'duels': {'total': 8, 'won': 5}, 'dribbles': {'attempts': 3, 'success': 2},
             'fouls': {'drawn': 1, 'committed': 1}, 'cards': {'yellow': 0, 'red': 0},
             'penalty': {'won': 0, 'commited': 0, 'scored': 0, 'missed': 0}},
        )
        self.assertEqual(row['player_id'], '7')
        self.assertEqual(row['passes_key'], 3)
        self.assertEqual(row['source'], 'API_FOOTBALL_FIXTURES_PLAYERS')

    def test_aggregate_grade_is_research_only(self):
        stats = {
            'player_id':'7','player_name':'Seven','position':'M','minutes':90,'passes_total':55,
            'passes_accuracy':'86%','passes_key':3,'assists':1,'shots_on':1,'dribbles_success':2,
            'tackles_total':2,'interceptions':1,'tackles_blocks':1,'duels_total':8,'duels_won':5,
            'fouls_committed':1,'yellow':0,'red':0,'source':'API_FOOTBALL_FIXTURES_PLAYERS',
        }
        result = grade.grade_aggregate(stats)
        self.assertTrue(result['available'])
        self.assertGreaterEqual(result['overall_grade'], 0)
        self.assertLessEqual(result['overall_grade'], 10)
        self.assertIsNone(result['components']['pressing'])
        self.assertTrue(result['research_only'])
        self.assertFalse(result['probability_mutation'])
        self.assertFalse(result['eligibility_mutation'])
        self.assertFalse(result['stake_changes'])

    def test_zero_minutes_is_unavailable(self):
        result = grade.grade_aggregate({'player_id':'1','minutes':0})
        self.assertFalse(result['available'])
        self.assertIn('NO_MINUTES', result['limitations'])

    def test_statsbomb_event_actions_use_half_step_scale(self):
        events = [
            {'id':'p1','player':{'id':9},'type':{'name':'Pass'},'location':[40,40],
             'pass':{'end_location':[70,40]},'under_pressure':True},
            {'id':'s1','player':{'id':9},'type':{'name':'Shot'},
             'shot':{'statsbomb_xg':0.4,'outcome':{'name':'Goal'}}},
            {'id':'f1','player':{'id':9},'type':{'name':'Foul Committed'}},
        ]
        result = grade.grade_statsbomb_events(events, 9, 'F')
        self.assertEqual(result['action_count'], 3)
        for action in result['actions']:
            self.assertEqual((action['score'] * 2) % 1, 0)
            self.assertGreaterEqual(action['score'], -2)
            self.assertLessEqual(action['score'], 2)
        self.assertEqual(result['source'], 'STATSBOMB_OPEN_DATA_EVENTS')

    def test_rolling_form_obeys_cutoff(self):
        rows = [
            {'kickoff_utc':'2026-09-01T10:00:00Z','overall_grade':6},
            {'kickoff_utc':'2026-09-05T10:00:00Z','overall_grade':8},
            {'kickoff_utc':'2026-09-20T10:00:00Z','overall_grade':10},
        ]
        result = grade.rolling_form(rows, before_utc='2026-09-10T00:00:00Z')
        self.assertEqual(result['form_5'], 7)
        self.assertEqual(result['sample_5'], 2)

    def test_xi_quality_reports_missing_coverage(self):
        players = xi('P')
        grades = {'P1': {'overall_grade':7.0}, 'P2': {'overall_grade':8.0}}
        result = grade.xi_quality(players, grades)
        self.assertEqual(result['covered_players'], 2)
        self.assertEqual(len(result['missing_player_ids']), 9)
        self.assertAlmostEqual(result['xi_quality'], 7.5)


class ManualScenarioTests(unittest.TestCase):
    def test_ready_scenario_uses_official_over_expected_baseline(self):
        manual = {'home': {'formation':'4-3-3','xi':xi('H')}, 'away': {'formation':'4-4-2','xi':xi('A')}}
        result = scenario.build_scenario('99', lineup_context(), manual, created_at_utc='2026-09-15T08:00:00Z')
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(result['home']['baseline']['status'], 'EXPECTED')
        self.assertEqual(result['away']['baseline']['status'], 'OFFICIAL')
        self.assertTrue(result['away']['formation_changed'])
        self.assertTrue(result['what_if_only'])
        self.assertFalse(result['provider_data_overwrite'])
        self.assertFalse(result['forward_journal_mutation'])

    def test_exactly_eleven_required_for_ready(self):
        manual = {'home': {'formation':'4-3-3','xi':xi('H')[:-1]}, 'away': {'formation':'4-2-3-1','xi':xi('A')}}
        result = scenario.build_scenario('99', lineup_context(), manual, created_at_utc='2026-09-15T08:00:00Z')
        self.assertEqual(result['status'], 'INVALID')
        self.assertIn('HOME:STARTING_XI_MUST_HAVE_11_PLAYERS', result['errors'])

    def test_manual_change_reports_quality_delta(self):
        home = xi('H')
        replacement = {'id':'NEW','name':'New','number':20,'pos':'M'}
        home[-1] = replacement
        manual = {'home': {'formation':'4-3-3','xi':home}, 'away': {'formation':'4-2-3-1','xi':xi('A')}}
        grades = {f'H{i}': {'overall_grade':7} for i in range(1,12)}
        grades.update({f'A{i}': {'overall_grade':7} for i in range(1,12)})
        grades['NEW'] = {'overall_grade':5}
        result = scenario.build_scenario('99', lineup_context(), manual, grades_by_player=grades,
                                         created_at_utc='2026-09-15T08:00:00Z')
        comparison = result['home']['comparison']
        self.assertEqual(comparison['overlap'], 10)
        self.assertEqual(comparison['added'][0]['id'], 'NEW')
        self.assertLess(comparison['xi_quality_delta'], 0)

    def test_save_is_append_only_and_idempotent(self):
        manual = {'home': {'formation':'4-3-3','xi':xi('H')}, 'away': {'formation':'4-2-3-1','xi':xi('A')}}
        result = scenario.build_scenario('99', lineup_context(), manual, source_note='insider',
                                         created_at_utc='2026-09-15T08:00:00Z')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'scenarios.jsonl'
            self.assertTrue(scenario.save_scenario(path, result))
            first = path.read_bytes()
            self.assertFalse(scenario.save_scenario(path, result))
            self.assertEqual(first, path.read_bytes())
            loaded = scenario.load_scenarios(path, '99')
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]['source_note'], 'insider')

    def test_contract_never_mutates_canonical_state(self):
        manual = {'home': {'formation':'4-3-3','xi':xi('H')}, 'away': {'formation':'4-2-3-1','xi':xi('A')}}
        result = scenario.build_scenario('99', lineup_context(), manual, created_at_utc='2026-09-15T08:00:00Z')
        for key in ('creates_signal','probability_mutation','eligibility_mutation','stake_changes',
                    'forward_journal_mutation','settlement_mutation','motivation_mutation','context_mutation'):
            self.assertFalse(result[key])


if __name__ == '__main__':
    unittest.main()
