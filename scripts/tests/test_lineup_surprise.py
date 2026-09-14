import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lineup_surprise as surprise


def expected(prefix, sample=5):
    return {
        'xi': [
            {'id': f'{prefix}{i}', 'name': f'{prefix}{i}', 'historical_starts': sample if i <= 8 else sample - 2, 'history_sample': sample}
            for i in range(1, 12)
        ],
        'basis_fixtures': sample,
        'confidence': 'HIGH' if sample >= 5 else 'LOW',
    }


def official(ids):
    return {'xi': [{'id': pid, 'name': pid} for pid in ids]}


def lineup_payload(home_official=None, away_official=None, home_expected=None, away_expected=None):
    return {
        'fixture_id':'999','no_lookahead':True,
        'home':{'official':home_official,'expected':home_expected},
        'away':{'official':away_official,'expected':away_expected},
    }


class LineupSurpriseTests(unittest.TestCase):
    def test_exact_expected_xi_has_full_overlap(self):
        exp = expected('A')
        payload = lineup_payload(official([f'A{i}' for i in range(1,12)]), None, exp, None)
        result = surprise.build_surprise_context(payload)
        self.assertEqual(result['home']['overlap_starters'], 11)
        self.assertEqual(result['home']['unexpected_starters_count'], 0)
        self.assertEqual(result['home']['missing_expected_count'], 0)
        self.assertEqual(result['status'], 'PARTIAL')

    def test_two_unexpected_starters_are_reported_factually(self):
        exp = expected('A')
        ids = [f'A{i}' for i in range(1,10)] + ['NEW1','NEW2']
        team = surprise.analyze_team({'official':official(ids),'expected':exp})
        self.assertTrue(team['available'])
        self.assertEqual(team['overlap_starters'], 9)
        self.assertEqual(team['unexpected_starters_count'], 2)
        self.assertEqual({p['id'] for p in team['unexpected_starters']}, {'NEW1','NEW2'})
        self.assertEqual({p['id'] for p in team['missing_expected']}, {'A10','A11'})

    def test_concentration_is_history_frequency_not_betting_score(self):
        exp = expected('A', 5)
        team = surprise.analyze_team({'official':official([f'A{i}' for i in range(1,12)]),'expected':exp})
        concentration = team['concentration']
        self.assertTrue(concentration['available'])
        self.assertEqual(concentration['history_sample'], 5)
        self.assertEqual(concentration['stable_core_players'], 11)
        self.assertAlmostEqual(concentration['average_start_share_pct'], 89.1, places=1)

    def test_missing_official_or_expected_stays_unavailable(self):
        team = surprise.analyze_team({'official':None,'expected':expected('A')})
        self.assertFalse(team['available'])
        self.assertIn('OFFICIAL_XI_UNAVAILABLE', team['limitations'])
        team = surprise.analyze_team({'official':official([f'A{i}' for i in range(1,12)]),'expected':None})
        self.assertFalse(team['available'])
        self.assertIn('EXPECTED_XI_UNAVAILABLE', team['limitations'])

    def test_contract_never_claims_model_or_signal_mutation(self):
        exp_h, exp_a = expected('A'), expected('B')
        payload = lineup_payload(
            official([f'A{i}' for i in range(1,12)]),
            official([f'B{i}' for i in range(1,12)]), exp_h, exp_a,
        )
        result = surprise.build_surprise_context(payload)
        self.assertEqual(result['status'], 'AVAILABLE')
        self.assertTrue(result['context_only'])
        self.assertTrue(result['read_only'])
        self.assertFalse(result['provider_polling'])
        self.assertFalse(result['creates_signal'])
        self.assertFalse(result['probability_mutation'])
        self.assertFalse(result['eligibility_mutation'])
        self.assertFalse(result['stake_changes'])
        self.assertIn('no betting-impact score', result['notes'])


if __name__ == '__main__':
    unittest.main()
