import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage78_player_grade_research as s78


def player(pid, pos='M'):
    return {'id': str(pid), 'name': f'P{pid}', 'pos': pos}


def grade(pid, kickoff, observed, value=7.0, minutes=90, team='10'):
    return {
        'fixture_id': f'g-{pid}-{kickoff}', 'team_id': team, 'player_id': str(pid),
        'player_name': f'P{pid}', 'kickoff_utc': kickoff, 'observed_at_utc': observed,
        'overall_grade': str(value), 'minutes': str(minutes), 'confidence': 'HIGH',
        'position_group': 'M', 'grade_version': 'PBK_PLAYER_GRADE_V1', 'source': 'TEST',
    }


class Stage78Tests(unittest.TestCase):
    def test_grade_asof_blocks_future_observation_and_low_minutes(self):
        rows = [
            grade('1', '2026-09-01T18:00:00Z', '2026-09-01T20:00:00Z', 6.0, 90),
            grade('1', '2026-09-05T18:00:00Z', '2026-09-05T20:00:00Z', 8.0, 20),
            # Match is historical, but late backfill was not known at capture time.
            grade('1', '2026-09-08T18:00:00Z', '2026-09-12T20:00:00Z', 10.0, 90),
        ]
        value, sample, low, version, source = s78._grade_asof(
            '1', rows, '2026-09-10T18:00:00Z', '2026-09-10T16:00:00Z')
        self.assertEqual(value, 6.0)
        self.assertEqual(sample, 1)
        self.assertEqual(low, 1)
        self.assertEqual(version, 'PBK_PLAYER_GRADE_V1')
        self.assertEqual(source, 'TEST')

    def test_xi_history_uses_current_vs_previous_not_fake_expected_semantics(self):
        grades = []
        for pid in range(1, 13):
            grades.append(grade(pid, '2026-09-01T18:00:00Z', '2026-09-01T20:00:00Z', 6.0 + pid / 10))
        current = [player(i) for i in range(1, 12)]
        previous = [player(i) for i in range(2, 13)]
        rotations = [{
            'api_fixture_id': '999', 'captured_at_utc': '2026-09-10T17:50:00Z',
            'kickoff_utc': '2026-09-10T18:00:00Z', 'home_team': 'Home', 'away_team': 'Away',
            'home_team_id': '10', 'away_team_id': '20',
            'home_current_formation': '4-3-3', 'away_current_formation': '4-4-2',
            'home_current_xi_json': __import__('json').dumps(current),
            'home_prev_xi_json': __import__('json').dumps(previous),
            'away_current_xi_json': '[]', 'away_prev_xi_json': '[]',
            'current_lineups_available': 'YES',
        }]
        rows = s78.build_xi_quality_history(rotations, grades)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['lineup_status'], 'OFFICIAL_OR_PROVIDER_CURRENT')
        self.assertEqual(row['covered_players'], 11)
        self.assertIsNotNone(row['previous_xi_quality'])
        self.assertIsNotNone(row['delta_vs_previous_xi'])
        self.assertEqual(row['no_lookahead'], 'true')
        self.assertNotIn('expected', row['lineup_status'].lower())

    def test_coverage_detects_duplicates_and_low_minutes(self):
        g = grade('1', '2026-09-01T18:00:00Z', '2026-09-01T20:00:00Z', minutes=20)
        report = s78.coverage_report([g, dict(g)], [dict(g)])
        self.assertEqual(report['duplicate_grade_rows'], 1)
        self.assertEqual(report['low_minute_rows_lt30'], 2)
        self.assertEqual(report['status'], 'ATTENTION')

    def test_importance_is_unknown_when_sample_is_insufficient(self):
        rotations = []
        fixtures = []
        for i in range(4):
            fid = str(100 + i)
            starters = [player('X')] + [player(f'a{i}-{n}') for n in range(10)]
            rotations.append({
                'api_fixture_id': fid, 'home_team_id': '10', 'home_team': 'Home',
                'away_team_id': '20', 'away_team': 'Away',
                'home_current_xi_json': __import__('json').dumps(starters),
                'away_current_xi_json': __import__('json').dumps([player(f'b{i}-{n}') for n in range(11)]),
            })
            fixtures.append({
                'fixture_id': fid, 'home_team': 'Home', 'away_team': 'Away',
                'score_home': '1', 'score_away': '0', 'status': 'finished',
            })
        rows = s78.build_player_importance(rotations, fixtures, min_with=5, min_without=5)
        target = next(r for r in rows if r['team_id'] == '10' and r['player_id'] == 'X')
        self.assertEqual(target['status'], 'UNKNOWN')
        self.assertEqual(target['eligible'], 'false')
        self.assertIsNone(target['importance_score'])
        self.assertIn('INSUFFICIENT_SAMPLE', target['sample_reason'])

    def test_importance_eligible_uses_shrinkage_and_never_mutates_strategy(self):
        rotations = []
        fixtures = []
        for i in range(10):
            fid = str(200 + i)
            includes_x = i < 5
            starters = ([player('X')] if includes_x else [player(f'z{i}')]) + [player(f'h{i}-{n}') for n in range(10)]
            rotations.append({
                'api_fixture_id': fid, 'home_team_id': '10', 'home_team': 'Home',
                'away_team_id': '20', 'away_team': 'Away',
                'home_current_xi_json': __import__('json').dumps(starters),
                'away_current_xi_json': __import__('json').dumps([player(f'a{i}-{n}') for n in range(11)]),
            })
            fixtures.append({
                'fixture_id': fid, 'home_team': 'Home', 'away_team': 'Away',
                'score_home': '2' if includes_x else '0', 'score_away': '0' if includes_x else '1',
                'status': 'finished',
            })
        rows = s78.build_player_importance(rotations, fixtures, min_with=5, min_without=5)
        target = next(r for r in rows if r['team_id'] == '10' and r['player_id'] == 'X')
        self.assertEqual(target['status'], 'RESEARCH_ESTIMATE')
        self.assertEqual(target['eligible'], 'true')
        self.assertAlmostEqual(target['shrinkage_weight'], 0.25)
        self.assertIsNotNone(target['importance_score'])
        self.assertEqual(target['creates_signal'], 'false')
        self.assertEqual(target['probability_mutation'], 'false')
        self.assertEqual(target['eligibility_mutation'], 'false')
        self.assertEqual(target['stake_changes'], 'false')


if __name__ == '__main__':
    unittest.main()
