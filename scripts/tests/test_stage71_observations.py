import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage71_challenger_capture as c
import stage71_observation_audit as a

NOW = datetime(2026, 9, 12, 10, tzinfo=timezone.utc)


def fixture(fid=1, lid=218, hours=2, status='NS', goals=None):
    return {'fixture': {'id': fid, 'date': a.stamp(NOW+timedelta(hours=hours)), 'status': {'short': status}},
            'league': {'id': lid}, 'teams': {'home': {'id': 10, 'name': 'Home'}, 'away': {'id': 20, 'name': 'Away'}},
            'goals': goals or {'home': None, 'away': None}}


def trigger(fid='1'):
    return dict(api_fixture_id=fid, api_league_id='218', captured_at_utc=a.stamp(NOW),
                kickoff_utc=a.stamp(NOW+timedelta(hours=2)), b365_home='4', b365_draw='3.5', b365_away='1.7')


def forward():
    return dict(research_id='R1|218|1', family='R1', api_fixture_id='1', api_league_id='218',
                status='PENDING', kickoff_utc=a.stamp(NOW-timedelta(hours=5)),
                trigger_captured_at_utc=a.stamp(NOW-timedelta(hours=10)),
                eligibility_frozen_at_utc=a.stamp(NOW-timedelta(hours=10)),
                user_price_captured_at_utc=a.stamp(NOW-timedelta(hours=10)), user_odds='1.7')


class Guards(unittest.TestCase):
    def test_trigger_provenance(self):
        t = trigger()
        self.assertTrue(a.clean_trigger(t))
        for key, value in [('captured_at_utc', t['kickoff_utc']), ('fixture_status_at_capture', 'FT'),
                           ('api_update_utc', a.stamp(NOW+timedelta(seconds=1))), ('captured_at_utc', 'bad')]:
            self.assertFalse(a.clean_trigger(dict(t, **{key: value})))

    def test_live_or_result_known_never_pregame(self):
        self.assertTrue(a.pregame(fixture(), NOW))
        for st in ['FT', '1H', 'PST', 'CANC', 'TBD', 'SUSP', 'AET', 'PEN']:
            self.assertFalse(a.pregame(fixture(status=st), NOW))
        self.assertFalse(a.pregame(fixture(hours=0), NOW))
        self.assertFalse(a.pregame(fixture(goals={'home': 0, 'away': 0}), NOW))

    def test_settlement_once_official_ft_only(self):
        r = forward()
        for st in ['PST', 'CANC', 'SUSP', 'ABD', 'AWD', 'AET', 'PEN', 'NS']:
            self.assertEqual(c.settle_rows([r], {'218': [fixture(hours=-5, status=st, goals={'home': 0, 'away': 0})]}, NOW), 0)
        result = {'218': [fixture(hours=-5, status='FT', goals={'home': 1, 'away': 2})]}
        self.assertEqual(c.settle_rows([r], result, NOW), 1)
        self.assertEqual(r['result'], 'W')
        self.assertEqual(r['user_profit_u'], '0.700')
        before = copy.deepcopy(r)
        self.assertEqual(c.settle_rows([r], result, NOW+timedelta(days=1)), 0)
        self.assertEqual(r, before)

    def test_invalid_scores_and_late_entry_do_not_settle(self):
        for goals in [{'home': None, 'away': 2}, {'home': -1, 'away': 2}]:
            self.assertEqual(c.settle_rows([forward()], {'218': [fixture(hours=-5, status='FT', goals=goals)]}, NOW), 0)
        row = forward(); row['eligibility_frozen_at_utc'] = a.stamp(NOW)
        self.assertEqual(c.settle_rows([row], {'218': [fixture(hours=-5, status='FT', goals={'home': 1, 'away': 1})]}, NOW), 0)

    def test_postponement_reschedule_then_ft(self):
        row = forward(); frozen = row['kickoff_utc']
        state = {}
        a.remember(state, [fixture(hours=-5, status='PST')], NOW)
        a.remember(state, [fixture(hours=48)], NOW)
        self.assertTrue(state['fixtures']['1']['rescheduled'])
        self.assertEqual(c.settle_rows([row], {'218': [fixture(hours=48)]}, NOW), 0)
        self.assertEqual(c.settle_rows([row], {'218': [fixture(hours=48, status='FT', goals={'home': 0, 'away': 1})]}, NOW+timedelta(hours=51)), 1)
        self.assertEqual(row['kickoff_utc'], frozen)

    def test_budget_counts_failures_and_daily_cap(self):
        state = {}
        def fail(*args): raise RuntimeError('timeout')
        budget = a.Budget(fail, state, NOW, limit=2)
        for _ in range(3):
            with self.assertRaises(RuntimeError): budget('/fixtures')
        self.assertEqual(budget.calls, 2)
        budget = a.Budget(fail, state, NOW, daily_limit=2)
        with self.assertRaises(RuntimeError): budget('/fixtures')
        self.assertEqual(budget.calls, 0)

    def test_missing_key_and_partial_pagination_not_empty_success(self):
        for response in [None, {'errors': ['quota'], 'response': []}, {'response': [], 'paging': {'total': 2}}]:
            budget = a.Budget(lambda *args: response, {}, NOW)
            with self.assertRaises(RuntimeError): budget('/fixtures')

    def test_duplicates_by_semantic_key(self):
        row = forward()
        self.assertEqual(a.duplicates([], [row, dict(row, research_id='different')]), 1)

    def test_missed_window_not_historical_backfill(self):
        state = {}; a.remember(state, [fixture()], NOW)
        state['fixtures']['1']['r1_qualifies'] = True
        health = a.report([trigger()], [], state, NOW+timedelta(hours=3))
        self.assertTrue(any('R2_window_missed' in x['reason'] for x in health['risks']))
        self.assertEqual(health['counts']['captured'], 0)

    def test_history_only_ft_before_evaluation(self):
        rows = [fixture(hours=-5, status='FT', goals={'home': 1, 'away': 0}),
                fixture(hours=-1, status='NS', goals={'home': 0, 'away': 1}),
                fixture(hours=1, status='FT', goals={'home': 0, 'away': 1})]
        self.assertEqual(c.team_state_before(rows, NOW, 10, 20), ((1, 3), (1, 0)))


class CaptureIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Path(self.temp.name)
        source = Path(__file__).resolve().parents[2] / 'ops/stage71_league_catalog.csv'
        (self.ops/'stage71_league_catalog.csv').write_bytes(source.read_bytes())
        self.patches = [patch.object(c, k, self.ops/v) for k, v in
                        [('OPS', ''), ('CATALOG', 'stage71_league_catalog.csv'),
                         ('TRIGGERS', 'stage71_research_trigger_ledger.csv'), ('FORWARD', 'stage71_challenger_forward.csv'),
                         ('META', 'stage71_capture_last_run.json')]]
        for p in self.patches: p.start()
        self.patches.append(patch.object(c, 'now_dt', return_value=NOW)); self.patches[-1].start()
        self.calls = []
        self.fixtures = [fixture(fid=i) for i in range(1, 9)]
        self.fail_odds = False

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.temp.cleanup()

    def api(self, path, params):
        self.calls.append((path, params))
        if path == '/fixtures':
            lid = int(params.get('league', 218))
            return {'response': self.fixtures if lid == 218 else [fixture(fid=lid*100, lid=lid, hours=-72, status='FT', goals={'home': 0, 'away': 0})]}
        if self.fail_odds: raise RuntimeError('temporary odds failure')
        name = 'Bet365' if 'bookmaker' in params else 'Marathonbet'
        return {'response': [{'update': a.stamp(NOW-timedelta(minutes=5)), 'bookmakers': [{'name': name,
                'bets': [{'name': 'Match Winner', 'values': [{'value': 'Home', 'odd': '4'},
                         {'value': 'Draw', 'odd': '3.5'}, {'value': 'Away', 'odd': '1.7'}]}]}]}]}

    def run_capture(self):
        with patch.object(c.s53, 'api_get', side_effect=self.api): c.main()
        return c.read_csv(c.FORWARD)

    def test_full_round_more_than_next5_idempotent(self):
        rows = self.run_capture()
        self.assertEqual(len(rows), 8)
        before = c.FORWARD.read_bytes()
        self.run_capture()
        self.assertEqual(c.FORWARD.read_bytes(), before)
        health = a.read(self.ops/'stage71_observation_health.json')
        self.assertEqual(health['counts']['duplicates'], 0)
        self.assertEqual(sum(s.get('legacy_next5_omitted', 0) for s in health['scan']), 3)
        self.assertTrue(all('next' not in p and 'status' not in p for path, p in self.calls if path == '/fixtures'))

    def test_failed_odds_retries_and_records_no_phantom_rows(self):
        self.fail_odds = True
        self.assertEqual(self.run_capture(), [])
        self.fail_odds = False
        self.assertEqual(len(self.run_capture()), 8)

    def test_result_known_inventory_cannot_capture(self):
        self.fixtures = [fixture(status='FT', goals={'home': 0, 'away': 1})]
        self.assertEqual(self.run_capture(), [])
        self.assertFalse(any(path == '/odds' for path, _ in self.calls))

    def test_crossing_kickoff_during_odds_request(self):
        def api(path, params):
            result = self.api(path, params)
            if path == '/odds': c.now_dt.return_value = NOW+timedelta(hours=3)
            return result
        with patch.object(c.s53, 'api_get', side_effect=api): c.main()
        self.assertEqual(c.read_csv(c.TRIGGERS), [])

    def test_r2_capture_settlement_and_repeat(self):
        self.fixtures = [fixture()]
        for i in range(5):
            self.fixtures.append(fixture(fid=100+i, hours=-24*(i+1), status='FT', goals={'home': 0, 'away': 1}))
        rows = self.run_capture()
        self.assertEqual({r['family'] for r in rows}, {'R1', 'R2'})
        self.assertEqual(len(self.run_capture()), 2)
        self.fixtures[0] = fixture(status='FT', goals={'home': 0, 'away': 1})
        c.now_dt.return_value = NOW+timedelta(hours=5)
        rows = self.run_capture()
        self.assertTrue(all(r['status'] == 'SETTLED' for r in rows))
        before = c.FORWARD.read_bytes()
        self.run_capture()
        self.assertEqual(before, c.FORWARD.read_bytes())

    def test_r2_not_frozen_before_window(self):
        self.fixtures = [fixture(hours=13)] + [fixture(fid=100+i, hours=-24*(i+1), status='FT', goals={'home': 0, 'away': 1}) for i in range(5)]
        self.assertEqual([r['family'] for r in self.run_capture()], ['R1'])
        c.now_dt.return_value = NOW+timedelta(hours=1)
        self.assertEqual({r['family'] for r in self.run_capture()}, {'R1', 'R2'})

    def test_duplicate_ledger_fails_before_network(self):
        row = forward()
        c.write_csv(c.FORWARD, c.FORWARD_FIELDS, [row, row])
        with self.assertRaisesRegex(RuntimeError, 'Duplicate'):
            self.run_capture()
        self.assertEqual(self.calls, [])

    def test_season_rollover_pending_retry(self):
        row = forward(); row['api_fixture_id'] = '999'; row['research_id'] = 'R1|218|999'
        c.write_csv(c.FORWARD, c.FORWARD_FIELDS, [row])
        original = self.api
        def api(path, params):
            if 'ids' in params:
                self.calls.append((path, params))
                return {'response': [fixture(fid=999, hours=-5, status='FT', goals={'home': 1, 'away': 1})]}
            return original(path, params)
        with patch.object(c.s53, 'api_get', side_effect=api): c.main()
        row = next(r for r in c.read_csv(c.FORWARD) if r['api_fixture_id'] == '999')
        self.assertEqual((row['status'], row['result']), ('SETTLED', 'L'))
        self.assertEqual(sum('ids' in p for _, p in self.calls), 1)


if __name__ == '__main__': unittest.main()
