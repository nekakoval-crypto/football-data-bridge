"""Locked Radar boundaries, prospective provenance and read-only API contracts."""
import contextlib
import copy
import gc
import io
import json
import socket
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage75_value_radar as radar
import stage75_probability_value as probability
import stage72_build_data_layer as builder
import stage73_internal_api as base
import stage74_app_api as api

NOW = '2026-09-12T12:00:00Z'
KICK = '2026-09-13T12:00:00Z'


class RadarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(gc.collect)
        self.ops = Path(self.tmp.name)
        self.cfg = {'version':'v1','models':{r:{'gate':'PASS'} for r in ('R1','R2','R3')}}
        self.row = dict(rule='R1',api_fixture_id='123',selection='Away',kickoff_utc=KICK,
                        home_team='Home',away_team='Away',status='PAPER',result='',
                        paper_user_execution_odds='2',paper_user_execution_bookmaker='Marathonbet',
                        user_execution_status='FROZEN',paper_user_execution_at_utc=NOW)
        self.pred = dict(rule='R1',api_fixture_id='123',selection='Away',kickoff_utc=KICK,
                         prediction_id='v1|R1|123|Away',model_version='v1',p_pbk='.525',
                         p_market_no_vig='.495',created_at_utc=NOW,trigger_captured_at_utc=NOW,
                         status='FROZEN_PREMATCH')

    def run_radar(self, rows=None, preds=None, now=NOW):
        with patch.object(socket, 'socket', side_effect=AssertionError('Network forbidden')):
            return radar.materialize(self.ops,rows or [self.row],preds or [self.pred],self.cfg,now)

    def current(self):
        return json.loads((self.ops/'value_radar_current.json').read_text(encoding='utf-8'))

    def kinds(self, pp, pm, odds='2', book='Marathonbet'):
        result=radar.classify(pp,pm,odds,book)
        return result['kinds'] if result else []

    def test_exact_boundaries_and_near_misses(self):
        self.assertEqual(self.kinds('.525','.495'),['STRONG_VALUE','LONGSHOT_STRONG'])
        self.assertEqual(self.kinds('.51','.49'),['WATCH_VALUE'])
        self.assertNotIn('STRONG_VALUE',self.kinds('.524995','.494995'))
        self.assertNotIn('STRONG_VALUE',self.kinds('.525','.49501'))
        self.assertEqual(self.kinds('.509995','.489995'),[])
        self.assertEqual(self.kinds('.51','.49001'),[])
        self.assertEqual(self.kinds('.55','.50',None),['MARKET_DISAGREEMENT'])
        self.assertEqual(self.kinds('.549999','.50',None),[])
        self.assertEqual(self.kinds('.65','.64','1.5'),['HIGH_PROB_LOW_VALUE'])
        self.assertEqual(self.kinds('.649999','.64','1.5'),[])
        self.assertEqual(self.kinds('.68','.67','1.5'),[])
        self.assertNotIn('LONGSHOT_STRONG',self.kinds('.6','.5','1.9999'))
        self.assertNotIn('LONGSHOT_STRONG',self.kinds('.51','.49','2'))

    def test_invalid_and_reference_only(self):
        for value in (None,'NaN','Infinity','-1','0','1','1.1'):
            self.assertIsNone(radar.classify(value,'.5','2','Marathonbet'))
            self.assertIsNone(radar.classify('.6',value,'2','Marathonbet'))
        for book in ('1xBet','Pinnacle','Fonbet',None):
            result=radar.classify('.6','.5','3',book)
            self.assertEqual(result['kinds'],['MARKET_DISAGREEMENT'])
            self.assertIsNone(result['ev'])
            self.assertIsNone(result['executable_odds'])
        for odds in (None,'NaN','Infinity','1','0'):
            self.assertEqual(self.kinds('.6','.5',odds),['MARKET_DISAGREEMENT'])
        self.assertEqual(self.kinds('.6','.5','1.5'),[])
        self.assertEqual(self.kinds('.65','.64',None),[])

    def test_first_crossing_bytes_rerun_and_transition(self):
        self.pred.update(p_pbk='.51',p_market_no_vig='.48')
        self.assertEqual(self.run_radar()['radar_events_created'],1)
        first=(self.ops/'stage75_value_radar.jsonl').read_bytes()
        self.assertEqual(self.run_radar()['radar_events_created'],0)
        self.assertEqual((self.ops/'stage75_value_radar.jsonl').read_bytes(),first)
        # Synthetic later input exercises the transition without rewriting the event.
        self.row['paper_user_execution_odds']='2.1'
        self.assertEqual(self.run_radar()['radar_events_created'],2)
        self.assertTrue((self.ops/'stage75_value_radar.jsonl').read_bytes().startswith(first))
        frozen=(self.ops/'stage75_value_radar.jsonl').read_bytes()
        self.row['paper_user_execution_odds']='1.5'
        self.run_radar()
        self.assertEqual((self.ops/'stage75_value_radar.jsonl').read_bytes(),frozen)
        self.assertEqual(self.current()['items'],[])

    def test_model_version_and_nested_dedupe(self):
        row2=dict(self.row,rule='R2')
        pred2=dict(self.pred,rule='R2',prediction_id='v1|R2|123|Away')
        self.run_radar([self.row,row2],[self.pred,pred2])
        item=self.current()['items'][0]
        self.assertEqual(item['source_rules'],['R1','R2'])
        self.assertEqual(item['primary_rule'],'R2')
        self.assertEqual(len(self.current()['items']),1)
        first=(self.ops/'stage75_value_radar.jsonl').read_bytes()
        self.cfg['version']='v2';self.pred['model_version']='v2'
        self.assertEqual(self.run_radar()['radar_events_created'],2)
        self.assertTrue((self.ops/'stage75_value_radar.jsonl').read_bytes().startswith(first))

    def test_watch_invalid_model_and_result_exclusion(self):
        for rule in ('Stage61','Stage62','Stage63','WATCH','R4'):
            row=dict(self.row,rule=rule);pred=dict(self.pred,rule=rule)
            self.cfg['models'][rule]={'gate':'PASS'}
            self.assertEqual(self.run_radar([row],[pred])['radar_events_created'],0)
        for change in ({'status':'SETTLED'},{'result':'W'},{'user_profit_u':'1'}, {'status':'CANC'}):
            self.assertEqual(self.run_radar([dict(self.row,**change)])['radar_events_created'],0)
        self.cfg['models']['R1']['gate']='FAIL'
        self.assertEqual(self.run_radar()['radar_events_created'],0)

    def test_no_postkickoff_future_or_historical_backfill(self):
        self.assertEqual(self.run_radar(now=KICK)['radar_events_created'],0)
        for field in ('created_at_utc','trigger_captured_at_utc'):
            for value in ('',KICK,'2026-09-12T13:00:00Z'):
                self.assertEqual(self.run_radar(preds=[dict(self.pred,**{field:value})])['radar_events_created'],0)
        self.row['paper_user_execution_at_utc']=KICK
        self.assertEqual(self.run_radar()['radar_events_created'],0)

    def test_duplicate_ledger_and_concurrent_writer_fail_closed(self):
        self.run_radar()
        ledger=self.ops/'stage75_value_radar.jsonl';raw=ledger.read_bytes()
        ledger.write_bytes(raw+raw)
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            self.run_radar()
        self.assertEqual(ledger.read_bytes(),raw+raw)
        (self.ops/'.stage75_value_radar.lock').touch()
        with self.assertRaises(FileExistsError):self.run_radar()

    def build(self):
        with patch.multiple(builder,OPS=self.ops,OUT=self.ops/'db.sqlite',META=self.ops/'meta.json',SCHEMA=self.ops/'schema.json'), patch.object(builder,'now_iso',return_value=NOW),contextlib.redirect_stdout(io.StringIO()):
            builder.main()
        return (self.ops/'db.sqlite').read_bytes()

    def test_sqlite_missing_empty_populated_determinism_and_api(self):
        self.build()
        with patch.object(base,'DB',self.ops/'db.sqlite'):
            self.assertEqual(api.value_radar_payload()[1]['status'],'NO_DATA')
        self.run_radar()
        before=self.build()
        self.assertEqual(self.build(),before)
        with contextlib.closing(sqlite3.connect(self.ops/'db.sqlite')) as conn:
            self.assertEqual(conn.execute('pragma integrity_check').fetchone()[0],'ok')
            self.assertEqual(conn.execute('select count(*) from value_radar_events').fetchone()[0],2)
            self.assertEqual(conn.execute("select value from pbk_meta where key='schema_version'").fetchone()[0],'8')
            conn.execute('drop table canonical_signals')
            conn.execute('create table canonical_signals (api_fixture_id TEXT)')
            conn.execute("insert into canonical_signals values ('123')")
            conn.commit()
        with patch.object(base,'DB',self.ops/'db.sqlite'):
            for supplied,expected in [('0',1),('-9',1),('999',100),('bad',50),('2',2)]:
                status,payload=api.dispatch('/v1/value-radar?limit='+supplied)
                self.assertEqual(status,200);self.assertEqual(payload['limit'],expected)
                self.assertFalse(payload['creates_signal'])
            status,match=api.aggregate_match('123')
            self.assertEqual(status,200)
            self.assertTrue({'canonical','watch','markets','probability','lifecycle','odds','value_radar'} <= set(match))
            self.assertEqual(len(match['value_radar']['items']),1)
            self.assertFalse(match['value_radar']['creates_signal'])
        gc.collect()

    def test_stage75_integration_zero_network_immutable_inputs(self):
        repo=Path(__file__).resolve().parents[2]
        for name in ('user_forward_view.csv','trigger_ledger.csv','stage75_probability_predictions.csv','stage75_probability_settlements.csv'):
            (self.ops/name).write_bytes((repo/'ops'/name).read_bytes())
        paths=dict(OPS=self.ops,CFG=repo/'config/pbk_probability_models.json',
                   FORWARD=self.ops/'user_forward_view.csv',TRIGGERS=self.ops/'trigger_ledger.csv',
                   LEDGER=self.ops/'stage75_probability_predictions.csv',SETTLE=self.ops/'stage75_probability_settlements.csv',
                   RANK=self.ops/'probability_rankings.json',PERF=self.ops/'probability_performance.json',META=self.ops/'stage75_last_run.json')
        source={key:path.read_bytes() for key,path in paths.items() if key in {'FORWARD','TRIGGERS','LEDGER','SETTLE'}}
        with patch.multiple(probability,**paths),patch.object(probability,'now_iso',return_value=NOW),patch.object(socket,'socket',side_effect=AssertionError('Network forbidden')),contextlib.redirect_stdout(io.StringIO()):
            probability.main()
            first=(self.ops/'stage75_value_radar.jsonl').read_bytes()
            probability.main()
        self.assertEqual((self.ops/'stage75_value_radar.jsonl').read_bytes(),first)
        for key,raw in source.items():self.assertEqual(paths[key].read_bytes(),raw,key)
        meta=json.loads(paths['META'].read_text())
        self.assertEqual(meta['api_calls'],0)
        self.assertEqual(meta['radar_events_created'],0)


if __name__ == '__main__':unittest.main()
