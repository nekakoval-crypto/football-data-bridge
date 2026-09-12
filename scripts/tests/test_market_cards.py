"""Offline projection, cache persistence, and SQLite/API round-trip regressions."""
import csv
import gc
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage66_append_market_cards as cards
import market_research_inventory as inventory
import stage72_build_data_layer as builder
import stage73_internal_api as api
import stage74_app_api as app

class MarketCards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ops = Path(self.tmp.name)
        self.catalog = cards.read_csv(Path(__file__).resolve().parents[2]/'ops/stage71_league_catalog.csv')
        self.write('stage71_league_catalog.csv', self.catalog)
        self.now = datetime(2026,9,12,12,tzinfo=timezone.utc)
        self.fixtures = [dict(api_fixture_id=str(i), api_league_id=r['api_league_id'],
                              kickoff_utc='2026-09-13T14:00:00Z', fixture_status='NS',
                              home_team='Home', away_team='Away', captured_at_utc='2026-09-12T11:00:00Z') for i,r in enumerate(self.catalog,1)]
        self.save_inventory()

    def tearDown(self):
        gc.collect()
        self.tmp.cleanup()
    def write(self,name,rows):
        with (self.ops/name).open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
            w.writeheader();w.writerows(rows)
    def save_inventory(self):
        (self.ops/'market_research_fixtures.json').write_text(json.dumps({'fixtures':self.fixtures}),encoding='utf-8')
    def build(self): return cards.build_cards(self.ops,self.now)
    def row(self,**kwargs): return {**self.fixtures[0], 'captured_at_utc':'2026-09-12T10:00:00Z', **kwargs}

    def test_all_16_without_odds_no_top8_or_signal_dependency(self):
        out=self.build()
        self.assertEqual(len(out),16)
        self.assertEqual({c['league'] for c in out},{r['league'] for r in self.catalog})
        for c in out:
            self.assertFalse(c['creates_signal'])
            self.assertEqual(c['status'],'MARKET_VIEW_ONLY')
            self.assertEqual({m['market'] for m in c['markets']},set(cards.LABELS))
            self.assertTrue(all(m['status']=='NO_DATA' for m in c['markets']))

    def test_latest_snapshot_partial_invalid_and_bookmaker_provenance(self):
        self.write('stage71e_double_chance_snapshots.csv',[
            self.row(b365_1x='1.4', user_1x='1.5'),
            self.row(captured_at_utc='2026-09-12T10:30:00Z', b365_1x='1.6', user_1x='', b365_x2='NaN', b365_12='0'),
            self.row(captured_at_utc='2026-09-14T10:00:00Z', b365_1x='9')])
        rows=[m for c in self.build() if c['fixture_id']=='1' for m in c['markets'] if m['market']=='DOUBLE_CHANCE']
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['bookmaker'],'Bet365')
        self.assertIn('1.6',rows[0]['text'])
        self.assertIn('нет данных',rows[0]['text'])
        self.assertNotIn('NaN',rows[0]['text'])

    def test_all_lines_retained_and_snapshot_fallback(self):
        (self.ops/'market_research_fixtures.json').unlink()
        self.write('stage71c_team_total_snapshots.csv',[self.row(team_side=side,line=line,b365_over='1.9') for side in ('H','A') for line in ('0.5','1.5','2.5')])
        out=self.build()
        self.assertEqual(len(out),1)
        self.assertEqual(len([m for m in out[0]['markets'] if m['market']=='TEAM_TOTAL']),6)

    def test_status_horizon_scope_and_reschedule_price_guard(self):
        self.write('stage71e_double_chance_snapshots.csv',[self.row(b365_1x='1.4')])
        self.fixtures[0]['kickoff_utc']='2026-09-14T14:00:00Z'
        for i,st in enumerate(('FT','PST','CANC','1H'),1): self.fixtures[i]['fixture_status']=st
        self.fixtures[5]['kickoff_utc']='2026-09-12T12:00:00Z'
        self.fixtures[6]['kickoff_utc']='2026-10-20T12:00:00Z'
        self.fixtures[7]['api_league_id']='999999'
        self.save_inventory()
        out=self.build()
        self.assertEqual(len(out),11)
        first=next(c for c in out if c['fixture_id']=='1')
        self.assertTrue(all(m['status']=='NO_DATA' for m in first['markets']))

    def test_disrupted_fixtures_visible_with_status_and_no_prices(self):
        for status in ('PST','CANC','SUSP','INT','TBD'):
            with self.subTest(status=status):
                self.fixtures[0]['fixture_status']=status
                self.write('stage71e_double_chance_snapshots.csv',[self.row(b365_1x='1.4',fixture_status='NS')])
                self.save_inventory()
                card=next(c for c in self.build() if c['fixture_id']=='1')
                self.assertEqual(card['fixture_status'],status)
                self.assertFalse(card['creates_signal'])
                self.assertTrue(all(m['status']=='NO_DATA' for m in card['markets']))

    def test_cached_inventory_keeps_fixture_without_any_odds(self):
        cache={('/fixtures',(('league','39'),)):{'response':[{'fixture':{'id':99,'date':'2026-09-13T14:00:00Z','status':{'short':'NS'}},'league':{'id':39},'teams':{'home':{'name':'H'},'away':{'name':'A'}}}]},('/odds',()):{'response':[]}}
        inventory.persist(self.ops,cache,'2026-09-12T11:00:00Z')
        self.assertEqual([c['fixture_id'] for c in self.build()],['99'])

    def test_stage72_73_74_roundtrip_and_read_only(self):
        board={'market_cards':self.build(),'canonical':[], 'watch':[], 'summary':{'market_cards':16}}
        (self.ops/'attention_board.json').write_text(json.dumps(board),encoding='utf-8')
        db=self.ops/'test.sqlite'
        with patch.multiple(builder,OPS=self.ops,OUT=db,META=self.ops/'meta.json',SCHEMA=self.ops/'schema.json'):
            builder.main()
        before=db.read_bytes()
        with patch.object(api,'DB',db):
            code,payload=api.dispatch('/v1/attention')
            self.assertEqual(code,200)
            self.assertEqual(payload,board)
            code,detail=app.aggregate_match('16')
            self.assertEqual(code,200)
            self.assertEqual(detail['identity']['league'],self.catalog[15]['league'])
            self.assertEqual(detail['attention_card']['markets'],board['market_cards'][next(i for i,c in enumerate(board['market_cards']) if c['fixture_id']=='16')]['markets'])
            self.assertEqual(detail['canonical'],[])
            self.assertEqual(detail['watch'],[])
            self.assertFalse(detail['creates_signal'])
        self.assertEqual(before,db.read_bytes())

if __name__=='__main__':unittest.main()
