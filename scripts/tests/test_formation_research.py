import json
import csv
import contextlib
import io
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import formation_research as audit
import test_lineup_context as fixtures
from test_lineup_context import xi, KICKOFF


class FormationResearchTests(unittest.TestCase):
    setUp = fixtures.LineupContextTests.setUp
    tearDown = fixtures.LineupContextTests.tearDown
    add_rotation = fixtures.LineupContextTests.add_rotation

    def test_stage72_rebuild_and_readonly_api_preserve_evidence(self):
        import stage72_build_data_layer as stage72
        import stage73_internal_api as api
        self.add_rotation('999', '2026-09-20T15:00:00Z', KICKOFF, 10, 20, xi('H'), xi('A'))
        with tempfile.TemporaryDirectory() as tmp:
            ops=Path(tmp)/'ops';ops.mkdir();db=Path(tmp)/'test.sqlite'
            for table, filename in [('current_round_matches','current_round_fixtures.csv'),('context_latest','context_latest.csv'),('raw_rotation_snapshots','rotation_snapshots.csv')]:
                cursor=self.conn.execute(f'SELECT * FROM {table}')
                with (ops/filename).open('w',newline='',encoding='utf-8') as stream:
                    writer=csv.writer(stream);writer.writerow([c[0] for c in cursor.description]);writer.writerows(cursor.fetchall())
            with patch.object(stage72,'OPS',ops), patch.object(stage72,'OUT',db), patch.object(stage72,'META',ops/'meta.json'), patch.object(stage72,'SCHEMA',ops/'schema.json'), contextlib.redirect_stdout(io.StringIO()):
                stage72.main()
                before=(ops/'formation_research.jsonl').read_bytes()
                stage72.main()
            self.assertEqual((ops/'formation_research.jsonl').read_bytes(),before)
            db_before=db.read_bytes()
            with patch.object(api,'DB',db):
                status,payload=api.dispatch('/v1/research/formations?team_id=10&fixture_id=999')
                self.assertEqual(status,200)
                self.assertEqual(payload['matrix'][0]['matches'],1)
                self.assertEqual(payload['history'][0]['teams']['home']['status'],'OFFICIAL')
            self.assertEqual(db.read_bytes(),db_before)

    def test_stale_result_cannot_replace_newer_result(self):
        identity={'fixture_id':'999','kind':'result'}
        events=[{**identity,'source_observed_at_utc':'2026-09-20T18:00:00Z','result':{'status':'FT','score':[2,1],'outcome':'HOME'}},
                {**identity,'source_observed_at_utc':'2026-09-20T17:00:00Z','result':{'status':'UNKNOWN'}},
                {'fixture_id':'999','kind':'lineup','teams':{'home':{'status':'OFFICIAL','formation':'4-3-3'}}}]
        self.assertEqual(audit.summarize(events)['history'][0]['result']['status'],'FT')

    def test_append_idempotence_projection_and_result_linkage(self):
        self.add_rotation('999', '2026-09-20T15:00:00Z', KICKOFF, 10, 20, xi('H'), xi('A'))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'audit.jsonl'
            events = audit.capture(self.conn, path, '2026-09-20T15:05:00Z')
            before = path.read_bytes()
            self.assertEqual(len(events), 2)
            audit.capture(self.conn, path, '2026-09-20T15:10:00Z')
            self.assertEqual(path.read_bytes(), before)
            for col in ('source_status', 'score_home', 'score_away'):
                self.conn.execute(f'ALTER TABLE current_round_matches ADD COLUMN {col} TEXT')
            self.conn.execute("UPDATE current_round_matches SET source_status='FT',score_home='2',score_away='1'")
            events = audit.capture(self.conn, path, '2026-09-20T18:00:00Z')
            self.assertTrue(path.read_bytes().startswith(before))
            audit.project(self.conn, events)
            payload = audit.read_audit(self.conn, team_id='10')
            self.assertEqual(len(payload['history']), 1)
            self.assertEqual(payload['matrix'][0]['matches'], 1)
            self.assertEqual(payload['matrix'][0]['home_wins'], 1)
            self.assertTrue(payload['matrix'][0]['small_sample'])
            self.assertEqual(payload['history'][0]['teams']['home']['coach'], 'Coach A')
            self.assertFalse(audit.read_audit(self.conn, team_id='unrelated')['available'])
            self.assertFalse(payload['stake_changes'])
            # Rolling current-round removal must not erase the research history.
            self.conn.execute('DELETE FROM current_round_matches')
            self.assertEqual(audit.capture(self.conn, path, '2026-09-21T00:00:00Z'), events)

    def test_expected_official_retained_and_official_wins_summary(self):
        for fid, day in [('901', '01'), ('902', '10')]:
            self.add_rotation(fid, f'2026-09-{day}T14:00:00Z', f'2026-09-{day}T15:00:00Z', 10, 20, xi('H'), xi('A'))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'audit.jsonl'
            audit.capture(self.conn, path, '2026-09-20T12:00:00Z')
            self.add_rotation('999', '2026-09-20T15:00:00Z', KICKOFF, 10, 20, xi('H'), xi('A'), home_formation='3-5-2')
            events = audit.capture(self.conn, path, '2026-09-20T15:10:00Z')
            kinds = {e['teams']['home']['status'] for e in events if e['kind']=='lineup'}
            self.assertEqual(kinds, {'EXPECTED', 'OFFICIAL'})
            # Even later expected observations must not downgrade official evidence.
            expected = next(e for e in events if e['kind']=='lineup' and e['teams']['home']['status']=='EXPECTED')
            payload = audit.summarize(events + [expected])
            self.assertEqual(payload['matrix'][0]['home_formation'], '3-5-2')
            self.assertEqual(payload['matrix'][0]['matches'], 1)
            self.assertEqual(payload['matrix'][0]['settled'], 0)
            self.assertIsNone(payload['matrix'][0]['home_win_rate'])

    def test_invalid_results_unknown(self):
        for status, home, away in [('PST','0','0'),('CANC','1','0'),('LIVE','1','0'),('FT','-1','0'),('FT',None,'1'),('FT','1.5','0'),('FT','²','0'),('AET','2','1')]:
            self.assertEqual(audit.result_for({'source_status':status,'score_home':home,'score_away':away})['status'], 'UNKNOWN')

    def test_missing_newer_snapshot_does_not_erase_official_or_team_identity(self):
        self.conn.execute('DELETE FROM context_latest')
        self.add_rotation('999','2026-09-20T15:00:00Z',KICKOFF,10,20,xi('H'),xi('A'))
        self.add_rotation('999','2026-09-20T15:30:00Z',KICKOFF,10,20,[],[],available='NO')
        _,lineup=fixtures.lineup.build_lineup_context(self.conn,'999')
        self.assertEqual(lineup['home']['status'],'CONFIRMED')
        self.assertEqual(lineup['home']['team_id'],'10')
        self.assertEqual(lineup['home']['updated_at_utc'],'2026-09-20T15:00:00Z')

    def test_corruption_fails_without_changing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'audit.jsonl';path.write_text('broken\n')
            with self.assertRaises(json.JSONDecodeError):
                audit.capture(self.conn,path,'2026-09-20T12:00:00Z')
            self.assertEqual(path.read_text(),'broken\n')

    def test_empty_database_is_honest(self):
        conn=sqlite3.connect(':memory:')
        self.assertFalse(audit.read_audit(conn)['available'])
        conn.close()


if __name__ == '__main__':
    unittest.main()
