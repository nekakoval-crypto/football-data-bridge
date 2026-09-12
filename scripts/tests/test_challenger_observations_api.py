"""Read-only observation contract, isolated from live files and providers."""
import json
from contextlib import closing
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage73_internal_api as api


class ObservationContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'fixture.sqlite'
        self.override = patch.object(api, 'DB', self.db)
        self.override.start()
        with closing(sqlite3.connect(self.db)) as c, c:
            c.execute('CREATE TABLE state_documents(name TEXT, payload_json TEXT)')
            board = {'rows': [{'family': f, 'league': l, 'status': s} for f, l, s in
                             [('R1', 'League & One', 'MONITORING'), ('R2', 'League & One', 'MONITORING'), ('R1', 'Serie A', 'ACTIVE')]]}
            c.execute('INSERT INTO state_documents VALUES (?, ?)', ('stage71_challenger_board.json', json.dumps(board)))
            fields = 'research_id family league kickoff_utc home_team away_team selection trigger_b365_home trigger_b365_draw trigger_b365_away user_bookmaker user_odds status result final_home_goals final_away_goals user_profit_u'.split()
            c.execute('CREATE TABLE challenger_signals (' + ','.join(f'{k} TEXT' for k in fields) + ')')
            for i in range(8):
                values = [str(i), 'R1' if i < 7 else 'R2', 'League & One', f'2026-09-{i+10:02}T12:00:00Z', 'Home', 'Away', 'П2', '3.1', '3.2', '1.48', 'Marathonbet', '1.50', 'SETTLED', 'PUSH', '0', '0', '0.000']
                c.execute('INSERT INTO challenger_signals VALUES (' + ','.join('?' for _ in fields) + ')', values)
            c.execute('CREATE TABLE canonical_signals (forward_id TEXT, rule TEXT, kickoff_utc TEXT, selection TEXT, trigger_selected_odds TEXT, paper_user_execution_bookmaker TEXT, paper_user_execution_odds TEXT, status TEXT)')
            c.execute("INSERT INTO canonical_signals VALUES ('canonical-1','R1','2026-09-12T12:00:00Z','Away','1.7','Marathonbet','1.8','PAPER')")
        self.before = self.db.read_bytes()

    def tearDown(self):
        self.assertEqual(self.before, self.db.read_bytes(), 'read endpoint must not mutate DB')
        self.override.stop()
        self.tmp.cleanup()

    def get(self, params='family=R1&league=League+%26+One'):
        return api.dispatch('/v1/challengers/observations?' + params)

    def test_default_latest_five_and_exact_family_league(self):
        code, p = self.get()
        self.assertEqual(code, 200)
        self.assertEqual(p['count'], 7)
        self.assertEqual([r['id'] for r in p['items']], ['6','5','4','3','2'])
        self.assertEqual(p['source'], 'research-only')
        self.assertTrue(p['read_only'])
        row = p['items'][0]
        self.assertEqual((row['bet365_price'], row['marathonbet_price']), ('1.48','1.50'))
        self.assertEqual((row['final_home_goals'], row['result'], row['user_profit_u']), ('0','PUSH','0.000'))

    def test_pagination_and_bounds(self):
        _, p = self.get('family=R1&league=League+%26+One&offset=5&limit=5000')
        self.assertEqual(p['limit'], 500)
        self.assertEqual([r['id'] for r in p['items']], ['1','0'])
        _, p = self.get('family=R1&league=League+%26+One&offset=99')
        self.assertEqual(p['items'], [])
        self.assertEqual(p['count'], 7)

    def test_canonical_uses_same_fallback_as_board_and_preserves_scope(self):
        _, p = self.get('family=R1&league=Serie+A')
        self.assertEqual((p['source'], p['count']), ('canonical', 1))
        row = p['items'][0]
        self.assertEqual((row['selection'], row['status']), ('П2', 'PENDING'))
        self.assertEqual(row['bet365_price'], '1.7')
        self.assertIsNone(row['user_profit_u'])
        self.assertIsNone(row['final_home_goals'])

    def test_unknown_card_and_injection(self):
        for params in ('', 'family=R3&league=Serie+A', 'family=R1&league=%27+OR+1=1--'):
            self.assertEqual(self.get(params)[0], 404)

    def test_missing_table_is_unavailable_not_empty_observations(self):
        with closing(sqlite3.connect(self.db)) as c, c:
            c.execute('DROP TABLE challenger_signals')
        self.before = self.db.read_bytes()
        self.assertFalse(self.get()[1]['available'])

    def test_pending_hides_settlement_and_other_bookmaker_price(self):
        with closing(sqlite3.connect(self.db)) as c, c:
            c.execute("UPDATE challenger_signals SET status='PENDING', user_bookmaker='Other', selection='П1' WHERE research_id='6'")
        self.before = self.db.read_bytes()
        row = self.get()[1]['items'][0]
        self.assertEqual(row['bet365_price'], '3.1')
        for key in ('marathonbet_price', 'result', 'user_profit_u', 'final_home_goals', 'final_away_goals'):
            self.assertIsNone(row[key])


if __name__ == '__main__':
    unittest.main()
