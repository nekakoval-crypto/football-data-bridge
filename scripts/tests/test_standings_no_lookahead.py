import csv
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage72_build_data_layer as builder
import stage73_internal_api as api


FIELDS = builder.STANDINGS_FIELDS


def row(snapshot, observed, team='1', league='39', season='2026', rank='1'):
    return dict.fromkeys(FIELDS, '') | {
        'snapshot_id': snapshot, 'provider_league_id': league, 'league_name': 'Premier League',
        'season': season, 'observed_at_utc': observed, 'team_id': team,
        'team_name': f'Team {team}', 'rank': rank, 'points': '10', 'source': 'test',
    }


class StandingsNoLookaheadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ops = Path(self.temp.name)
        self.db = self.ops / 'db.sqlite'

    def tearDown(self):
        self.temp.cleanup()

    def create_db(self, rows):
        conn = sqlite3.connect(self.db)
        conn.execute('CREATE TABLE pbk_meta (key TEXT, value TEXT)')
        conn.executemany('INSERT INTO pbk_meta VALUES (?,?)', [
            ('built_at_utc', '2026-09-14T12:00:00Z'), ('schema_version', '12')])
        builder.create_standings_table(conn, self.ops)
        conn.commit()
        return conn

    def write_rows(self, rows):
        with (self.ops / 'standings_snapshots.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def test_as_of_uses_latest_snapshot_before_cutoff(self):
        self.write_rows([row('a', '2026-09-14T10:00:00Z'),
                         row('b', '2026-09-14T20:00:00Z')])
        conn = self.create_db([])
        selected = builder.select_standings_as_of(conn, '39', '2026', '2026-09-14T18:00:00Z')
        self.assertEqual(selected[0]['snapshot_id'], 'a')
        self.assertIsNone(builder.select_standings_as_of(
            conn, '39', '2025', '2026-09-14T18:00:00Z'))
        conn.close()

    def test_exact_cutoff_and_no_lookahead(self):
        self.write_rows([row('a', '2026-09-14T10:00:00Z')])
        conn = self.create_db([])
        self.assertIsNotNone(builder.select_standings_as_of(
            conn, '39', '2026', '2026-09-14T10:00:00Z'))
        self.assertIsNone(builder.select_standings_as_of(
            conn, '39', '2026', '2026-09-14T09:59:59Z'))
        conn.close()

    def test_rows_from_snapshots_are_never_mixed_and_ambiguity_is_unavailable(self):
        self.write_rows([row('a', '2026-09-14T10:00:00Z', '1'),
                         row('a', '2026-09-14T10:00:00Z', '2'),
                         row('b', '2026-09-14T10:00:00Z', '1')])
        conn = self.create_db([])
        self.assertIsNone(builder.select_standings_as_of(
            conn, '39', '2026', '2026-09-14T11:00:00Z'))
        conn.close()

    def test_corrupt_snapshot_is_rejected(self):
        self.write_rows([row('a', '2026-09-14T10:00:00Z', '1'),
                         row('a', 'bad', '2')])
        conn = self.create_db([])
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM standings_snapshots').fetchone()[0], 0)
        conn.close()

    def test_historical_age_uses_requested_cutoff(self):
        self.write_rows([row('a', '2026-09-14T16:00:00Z')])
        conn = self.create_db([])
        with patch.object(api, 'DB', self.db):
            status, payload = api.dispatch(
                '/v1/standings?provider_league_id=39&season=2026&as_of_utc=2026-09-14T18:00:00Z')
        self.assertEqual(status, 200)
        self.assertEqual(payload['age_seconds_at_cutoff'], 7200)
        self.assertTrue(payload['no_lookahead'])
        conn.close()

    def test_api_defaults_to_build_cutoff_and_rejects_invalid_cutoff(self):
        self.write_rows([row('a', '2026-09-14T10:00:00Z')])
        conn = self.create_db([])
        conn.close()
        with patch.object(api, 'DB', self.db):
            status, payload = api.dispatch('/v1/standings?provider_league_id=39&season=2026')
            self.assertEqual(status, 200)
            self.assertEqual(payload['requested_as_of_utc'], '2026-09-14T12:00:00Z')
            status, payload = api.dispatch(
                '/v1/standings?provider_league_id=39&season=2026&as_of_utc=not-a-time')
        self.assertEqual(status, 400)
        self.assertEqual(payload['error'], 'INVALID_AS_OF_UTC')

    def test_missing_csv_creates_empty_stable_table(self):
        conn = sqlite3.connect(self.db)
        count = builder.create_standings_table(conn, self.ops)
        self.assertEqual(count, 0)
        self.assertEqual(conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='standings_snapshots'"
        ).fetchone()[0], 'standings_snapshots')
        conn.close()


if __name__ == '__main__':
    unittest.main()
