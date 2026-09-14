import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage71_live_snapshot as live
import stage71_observation_audit as audit
import stage72_build_data_layer as builder


class LiveSnapshotTests(unittest.TestCase):
    now = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)

    def base(self, fid, kickoff, status='scheduled'):
        return {'fixture_id': str(fid), 'kickoff_utc': kickoff, 'status': status,
                'observed_at_utc': '2026-09-13T14:00:00Z', 'score_home': '',
                'score_away': ''}

    def provider(self, fid, status, home, away, elapsed):
        return {'fixture': {'id': fid, 'status': {'short': status, 'elapsed': elapsed}},
                'teams': {'home': {'id': 10}, 'away': {'id': 20}},
                'goals': {'home': home, 'away': away}, 'events': []}

    def test_candidate_window_and_one_ids_batch(self):
        calls = []
        base = [self.base(1, '2026-09-13T15:10:00Z'),
                self.base(2, '2026-09-13T14:00:00Z', 'live'),
                self.base(3, '2026-09-20T15:00:00Z')]

        def get(path, params, **kwargs):
            calls.append((path, params))
            return {'response': [self.provider(1, '1H', 0, 0, 1),
                                 self.provider(2, 'HT', 0, 1, 45),
                                 self.provider(99, 'FT', 9, 9, None)]}

        rows, meta = live.refresh(base, [], get, self.now)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], '/fixtures')
        self.assertEqual(calls[0][1]['ids'], '2-1')
        self.assertEqual(meta['candidate_fixtures'], 2)
        by_id = {row['fixture_id']: row for row in rows}
        self.assertEqual(by_id['2']['status'], 'live')
        self.assertEqual(by_id['2']['elapsed'], 45)
        self.assertNotIn('3', by_id)

    def test_live_score_and_terminal_transitions(self):
        base = [self.base(1, '2026-09-13T14:00:00Z', 'live')]
        responses = [
            {'response': [self.provider(1, '1H', 0, 3, 30)]},
            {'response': [self.provider(1, 'HT', 0, 3, 45)]},
            {'response': [self.provider(1, '2H', 0, 3, 60)]},
            {'response': [self.provider(1, 'FT', 2, 4, None)]},
        ]
        rows, _ = live.refresh(base, [], lambda *a, **k: responses.pop(0), self.now)
        self.assertEqual(rows[0]['source_status'], '1H')
        rows, _ = live.refresh(base, rows, lambda *a, **k: responses.pop(0), self.now)
        self.assertEqual(rows[0]['source_status'], 'HT')
        rows, _ = live.refresh(base, rows, lambda *a, **k: responses.pop(0), self.now)
        self.assertEqual(rows[0]['source_status'], '2H')
        rows, _ = live.refresh(base, rows, lambda *a, **k: responses.pop(0), self.now)
        self.assertEqual(rows[0]['status'], 'finished')
        self.assertEqual(rows[0]['score_home'], 2)
        self.assertEqual(rows[0]['score_away'], 4)

    def test_no_candidates_makes_no_request(self):
        rows, meta = live.refresh([self.base(1, '2026-09-20T15:00:00Z')], [],
                                  lambda *a, **k: self.fail('provider called'), self.now)
        self.assertEqual(rows, [])
        self.assertEqual(meta['provider_calls'], 0)
        self.assertTrue(meta['skipped_no_candidates'])

    def test_failure_preserves_values_and_marks_stale(self):
        previous = [{'fixture_id': '1', 'status': 'live', 'score_home': '0',
                     'score_away': '3', 'observed_at_utc': '2026-09-13T14:40:00Z'}]
        rows, meta = live.refresh([self.base(1, '2026-09-13T14:00:00Z', 'live')],
                                  previous,
                                  lambda *a, **k: (_ for _ in ()).throw(RuntimeError('budget exhausted')),
                                  self.now)
        self.assertTrue(meta['budget_exhausted'])
        self.assertEqual(rows[0]['score_away'], '3')
        self.assertEqual(rows[0]['live_freshness_status'], 'stale')

    def test_shared_budget_exhaustion_preserves_values(self):
        previous = [{'fixture_id': '1', 'status': 'live', 'score_home': '0',
                     'score_away': '3', 'observed_at_utc': '2026-09-13T14:40:00Z'}]
        state = {'api_day': self.now.date().isoformat(), 'api_day_calls': 180}
        budget = audit.Budget(lambda *a, **k: self.fail('provider called'),
                              state, self.now, daily_limit=180)
        rows, meta = live.refresh([self.base(1, '2026-09-13T14:00:00Z', 'live')],
                                  previous, budget, self.now)
        self.assertTrue(meta['budget_exhausted'])
        self.assertEqual(rows[0]['score_away'], '3')
        self.assertEqual(rows[0]['live_freshness_status'], 'stale')

    def test_newer_wins_and_older_live_cannot_regress_ft(self):
        base = self.base(1, '2026-09-13T14:00:00Z', 'finished')
        base.update(status='finished', source_status='FT', score_home='2',
                    score_away='4', observed_at_utc='2026-09-13T15:00:00Z',
                    home_team='Stable')
        older = {'fixture_id': '1', 'status': 'live', 'source_status': '1H',
                 'score_home': '0', 'score_away': '3',
                 'observed_at_utc': '2026-09-13T14:30:00Z'}
        merged = builder.merge_live_overlay([base], [older])[0]
        self.assertEqual(merged['status'], 'finished')
        self.assertEqual(merged['score_home'], '2')
        self.assertEqual(merged['home_team'], 'Stable')

    def test_newer_live_cannot_regress_terminal_snapshot(self):
        for terminal_status in ('FT', 'AET', 'PEN'):
            with self.subTest(terminal_status=terminal_status):
                base = self.base(1, '2026-09-13T14:00:00Z', 'finished')
                base.update(status='finished', source_status=terminal_status, score_home='2',
                            score_away='4', observed_at_utc='2026-09-13T15:00:00Z')
                newer_live = {'fixture_id': '1', 'status': 'live', 'source_status': '1H',
                              'score_home': '0', 'score_away': '3',
                              'observed_at_utc': '2026-09-13T15:30:00Z'}
                merged = builder.merge_live_overlay([base], [newer_live])[0]
                self.assertEqual(merged['status'], 'finished')
                self.assertEqual(merged['score_home'], '2')
                self.assertEqual(merged['score_away'], '4')

    def test_terminal_snapshot_preserves_final_red_cards(self):
        base = self.base(1, '2026-09-13T14:00:00Z', 'finished')
        base.update(status='finished', source_status='FT', score_home='2',
                    score_away='4', red_cards_home=1, red_cards_away=0,
                    observed_at_utc='2026-09-13T15:00:00Z')
        older_live = {'fixture_id': '1', 'status': 'live', 'source_status': '1H',
                      'score_home': '0', 'score_away': '3', 'red_cards_home': 0,
                      'red_cards_away': 0, 'observed_at_utc': '2026-09-13T14:30:00Z'}
        merged = builder.merge_live_overlay([base], [older_live])[0]
        self.assertEqual((merged['status'], merged['red_cards_home'],
                          merged['red_cards_away']), ('finished', 1, 0))

    def test_zero_and_missing_scores_are_distinct(self):
        base = self.base(1, '2026-09-13T14:00:00Z', 'live')
        zero = live.provider_row(self.provider(1, '1H', 0, 0, 1), '2026-09-13T15:00:00Z')
        missing = live.provider_row(self.provider(1, '1H', None, None, 2), '2026-09-13T15:01:00Z')
        self.assertEqual((zero['score_home'], zero['score_away']), (0, 0))
        self.assertIsNone(missing['score_home'])
        self.assertIsNone(missing['score_away'])

    def test_events_and_card_semantics(self):
        item = self.provider(1, '1H', 0, 0, 20)
        item['events'] = [
            {'type': 'Card', 'detail': 'Red Card', 'team': {'id': 10},
             'player': {'id': 1}, 'time': {'elapsed': 20, 'extra': None}},
            {'type': 'Card', 'detail': 'Yellow-Red Card', 'team': {'id': 20},
             'player': {'id': 2}, 'time': {'elapsed': 30, 'extra': None}},
            {'type': 'Card', 'detail': 'Yellow Card', 'team': {'id': 10},
             'player': {'id': 3}, 'time': {'elapsed': 10, 'extra': None}},
            {'type': 'Card', 'detail': 'Red Card', 'team': {'id': 10},
             'player': {'id': 1}, 'time': {'elapsed': 20, 'extra': None}},
        ]
        row = live.provider_row(item, '2026-09-13T15:00:00Z')
        self.assertEqual((row['red_cards_home'], row['red_cards_away']), (1, 1))
        self.assertEqual(live.provider_row({**item, 'events': None}, 'x')['red_cards_home'], None)
        self.assertEqual(live.provider_row({**item, 'events': {}}, 'x')['red_cards_away'], None)

    def test_repeated_snapshots_do_not_accumulate_and_missing_fixture_isolated(self):
        item = self.provider(1, '1H', 0, 0, 20)
        item['events'] = [{'type': 'Card', 'detail': 'Red Card', 'team': {'id': 10},
                           'player': {'id': 1}, 'time': {'elapsed': 20, 'extra': None}}]
        get = lambda *args, **kwargs: {'response': [item, self.provider(99, 'FT', 9, 9, None)]}
        rows, _ = live.refresh([self.base(1, '2026-09-13T14:00:00Z', 'live')], [], get, self.now)
        rows, _ = live.refresh([self.base(1, '2026-09-13T14:00:00Z', 'live')], rows, get, self.now)
        self.assertEqual(rows[0]['red_cards_home'], 1)
        self.assertEqual(len(rows), 1)

    def test_two_batches_and_active_priority(self):
        base = [self.base(i, '2026-09-13T14:00:00Z', 'live' if i == 21 else 'scheduled')
                for i in range(1, 22)]
        calls = []
        def get(path, params, **kwargs):
            calls.append(params['ids'])
            return {'response': [self.provider(int(fid), '1H', 0, 0, 1)
                                 for fid in params['ids'].split('-')]}
        rows, meta = live.refresh(base, [], get, self.now)
        self.assertEqual(len(calls), 2)
        self.assertEqual(meta['skipped_fixtures'], 0)
        self.assertIn('21', calls[0])

    def test_budget_skips_lower_priority_and_marks_previous_stale(self):
        base = [self.base(i, '2026-09-13T14:00:00Z',
                          'live' if i == 1 else 'scheduled') for i in range(1, 22)]
        previous = [{**base[0], 'score_home': '0', 'score_away': '1',
                     'live_freshness_status': 'fresh'}]
        state = {'api_day': self.now.date().isoformat(), 'api_day_calls': 179}
        budget = audit.Budget(lambda *a, **k: {'response': []}, state, self.now, daily_limit=180)
        rows, meta = live.refresh(base, previous, budget, self.now)
        self.assertEqual(meta['skipped_fixtures'], 1)
        self.assertEqual(rows[0]['live_freshness_status'], 'stale')


if __name__ == '__main__':
    unittest.main()
