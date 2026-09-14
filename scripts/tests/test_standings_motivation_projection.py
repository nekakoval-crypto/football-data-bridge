import csv
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage72_build_data_layer as builder
import stage73_internal_api as api


class MotivationProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / 'pbk.sqlite'

    def tearDown(self):
        self.temp.cleanup()

    def standings_row(self, snapshot, observed, team_id, name, rank, points, description=''):
        return dict.fromkeys(builder.STANDINGS_FIELDS, '') | {
            'snapshot_id': snapshot,
            'provider_league_id': '39',
            'league_name': 'Premier League',
            'season': '2026',
            'observed_at_utc': observed,
            'team_id': str(team_id),
            'team_name': name,
            'rank': str(rank),
            'points': str(points),
            'played': '20',
            'group_name': 'Premier League',
            'description': description,
            'source': 'test',
        }

    def write_standings(self, rows):
        path = self.root / 'standings_snapshots.csv'
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=builder.STANDINGS_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def make_db(self, standings=True, status='scheduled'):
        conn = sqlite3.connect(self.db)
        conn.execute('CREATE TABLE pbk_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        conn.executemany('INSERT INTO pbk_meta VALUES (?,?)', [
            ('schema_version', '13'), ('built_at_utc', '2026-09-14T12:30:00Z')])
        conn.execute('CREATE TABLE current_round_leagues ('
                     'provider_league_id TEXT, league_name TEXT, country TEXT, country_flag_url TEXT, '
                     'league_logo_url TEXT, season TEXT, round TEXT, observed_at_utc TEXT, status TEXT, error TEXT)')
        conn.execute('INSERT INTO current_round_leagues VALUES (?,?,?,?,?,?,?,?,?,?)',
                     ('39', 'Premier League', 'England', '', '', '2026', 'Round 5',
                      '2026-09-14T09:00:00Z', 'available', ''))
        conn.execute('CREATE TABLE current_round_matches ('
                     'fixture_id TEXT, provider_league_id TEXT, season TEXT, kickoff_utc TEXT, '
                     'home_team TEXT, away_team TEXT, status TEXT, source_status TEXT, '
                     'score_home TEXT, score_away TEXT, observed_at_utc TEXT)')
        conn.execute('INSERT INTO current_round_matches VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                     ('999', '39', '2026', '2026-09-14T12:00:00Z', 'Alpha', 'Beta',
                      status, 'NS', '', '', '2026-09-14T09:00:00Z'))
        if standings:
            self.write_standings([
                self.standings_row('pre', '2026-09-14T10:00:00Z', 1, 'Alpha', 1, 30, 'Champions League'),
                self.standings_row('pre', '2026-09-14T10:00:00Z', 2, 'Beta', 2, 28, ''),
                self.standings_row('post', '2026-09-14T13:00:00Z', 1, 'Alpha', 2, 30, ''),
                self.standings_row('post', '2026-09-14T13:00:00Z', 2, 'Beta', 1, 31, 'Champions League'),
            ])
        builder.create_standings_table(conn, self.root)
        count, violations = builder.create_fixture_motivation_table(conn)
        self.assertEqual(violations, 0)
        self.assertEqual(count, 1)
        conn.commit()
        conn.close()

    def test_projection_uses_only_pre_match_snapshot(self):
        self.make_db()
        conn = sqlite3.connect(self.db)
        row = conn.execute('SELECT snapshot_id, snapshot_observed_at_utc, no_lookahead, payload_json '
                           'FROM fixture_motivation WHERE fixture_id=?', ('999',)).fetchone()
        conn.close()
        self.assertEqual(row[0], 'pre')
        self.assertEqual(row[1], '2026-09-14T10:00:00Z')
        self.assertEqual(row[2], '1')
        payload = json.loads(row[3])
        self.assertEqual(payload['home']['standings']['rank'], '1')
        self.assertEqual(payload['away']['standings']['rank'], '2')

    def test_live_and_ft_status_do_not_change_snapshot_cutoff(self):
        for status in ('live', 'finished'):
            if self.db.exists():
                self.db.unlink()
            self.make_db(status=status)
            conn = sqlite3.connect(self.db)
            snapshot = conn.execute('SELECT snapshot_id FROM fixture_motivation').fetchone()[0]
            conn.close()
            self.assertEqual(snapshot, 'pre')

    def test_motivation_endpoint_and_current_round_compact_contract(self):
        self.make_db()
        with patch.object(api, 'DB', self.db):
            status, payload = api.dispatch('/v1/motivation?fixture_id=999')
            self.assertEqual(status, 200)
            self.assertTrue(payload['standings_context']['no_lookahead'])
            self.assertTrue(payload['read_only'])
            self.assertFalse(payload['provider_polling'])
            status, rounds = api.dispatch('/v1/rounds/current')
        self.assertEqual(status, 200)
        compact = rounds['leagues'][0]['matches'][0]['motivation']
        self.assertTrue(compact['no_lookahead'])
        self.assertEqual(compact['snapshot_observed_at_utc'], '2026-09-14T10:00:00Z')

    def test_known_fixture_without_snapshot_returns_unavailable(self):
        self.make_db(standings=False)
        with patch.object(api, 'DB', self.db):
            status, payload = api.dispatch('/v1/motivation?fixture_id=999')
        self.assertEqual(status, 200)
        self.assertFalse(payload['coverage']['available'])
        self.assertTrue(payload['standings_context']['no_lookahead'])

    def test_unknown_fixture_and_missing_parameter_are_stable_errors(self):
        self.make_db()
        with patch.object(api, 'DB', self.db):
            status, payload = api.dispatch('/v1/motivation')
            self.assertEqual(status, 400)
            self.assertEqual(payload['error'], 'MISSING_FIXTURE_ID')
            status, payload = api.dispatch('/v1/motivation?fixture_id=does-not-exist')
        self.assertEqual(status, 404)
        self.assertEqual(payload['error'], 'UNKNOWN_FIXTURE')


if __name__ == '__main__':
    unittest.main()
