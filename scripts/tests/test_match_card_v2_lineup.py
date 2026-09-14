import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import match_card_v2 as card


class MatchCardLineupCompositionTests(unittest.TestCase):
    def base_payload(self):
        return {
            'fixture_id': '999',
            'fixture': {'fixture_id': '999'},
            'coverage': {'status': 'AVAILABLE', 'sections': {}, 'limitations': []},
            'read_only': True,
            'provider_polling': False,
            'eligibility_mutation': False,
            'model_mutation': False,
        }

    def test_lineup_and_surprise_are_added_without_mutating_model_contract(self):
        lineup = {
            'fixture_id': '999', 'available': True, 'no_lookahead': True,
            'home': {'status': 'CONFIRMED'}, 'away': {'status': 'EXPECTED'},
        }
        surprise = {
            'fixture_id': '999', 'available': True, 'status': 'AVAILABLE',
            'context_only': True, 'probability_mutation': False,
            'eligibility_mutation': False, 'stake_changes': False,
        }
        with patch.object(card._core, 'build_match_card', return_value=(200, self.base_payload())), \
             patch.object(card, 'build_lineup_context', return_value=(200, lineup)), \
             patch.object(card, 'build_surprise_context', return_value=surprise):
            status, payload = card.build_match_card(object(), '999')
        self.assertEqual(status, 200)
        self.assertIs(payload['lineup_context'], lineup)
        self.assertIs(payload['lineup_surprise'], surprise)
        self.assertTrue(payload['coverage']['optional_sections']['lineup_context'])
        self.assertTrue(payload['coverage']['optional_sections']['lineup_surprise'])
        self.assertEqual(payload['coverage']['status'], 'AVAILABLE')
        self.assertEqual(payload['coverage']['limitations'], [])
        self.assertEqual(payload['coverage']['extension_limitations'], [])
        self.assertFalse(payload['feature_contract']['provider_polling'])
        self.assertFalse(payload['feature_contract']['probability_mutation'])
        self.assertFalse(payload['feature_contract']['eligibility_mutation'])
        self.assertFalse(payload['feature_contract']['stake_changes'])

    def test_lineup_unavailable_is_honest_but_does_not_degrade_core_coverage(self):
        with patch.object(card._core, 'build_match_card', return_value=(200, self.base_payload())), \
             patch.object(card, 'build_lineup_context', return_value=(404, {'error': 'UNKNOWN_FIXTURE'})):
            status, payload = card.build_match_card(object(), '999')
        self.assertEqual(status, 200)
        self.assertFalse(payload['lineup_context']['available'])
        self.assertFalse(payload['lineup_surprise']['available'])
        self.assertEqual(payload['coverage']['status'], 'AVAILABLE')
        self.assertEqual(payload['coverage']['limitations'], [])
        self.assertFalse(payload['coverage']['optional_sections']['lineup_context'])
        self.assertFalse(payload['coverage']['optional_sections']['lineup_surprise'])
        self.assertIn('LINEUP_CONTEXT_UNAVAILABLE', payload['coverage']['extension_limitations'])
        self.assertIn('LINEUP_SURPRISE_PENDING_OR_UNAVAILABLE', payload['coverage']['extension_limitations'])

    def test_base_error_contract_is_preserved(self):
        with patch.object(card._core, 'build_match_card', return_value=(404, {'error': 'UNKNOWN_FIXTURE'})):
            status, payload = card.build_match_card(object(), 'missing')
        self.assertEqual(status, 404)
        self.assertEqual(payload['error'], 'UNKNOWN_FIXTURE')


if __name__ == '__main__':
    unittest.main()
