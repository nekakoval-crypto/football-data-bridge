#!/usr/bin/env python3
"""Stage71H — PBK core-market data readiness board.

Governance only. Never creates signals or promotes a strategy.
"""
from __future__ import annotations
import csv, json, os
from datetime import datetime, timezone
from pathlib import Path

OPS=Path(os.getenv('OPS_DIR','ops'))
REGISTRY=Path(os.getenv('PBK_CORE_MARKET_REGISTRY','config/pbk_core_market_registry.json'))
OUT_JSON=OPS/'core_market_readiness.json';OUT_MD=OPS/'core_market_readiness.md';META=OPS/'stage71h_last_run.json'
MIN_CLOSE_FIXTURES=120;MIN_USER_COVERAGE=90.0;MIN_SETTLEMENT_COVERAGE=90.0

CAPTURES={
 'TEAM_TOTAL':{'open':'stage71c_team_total_openers.csv','snap':'stage71c_team_total_snapshots.csv','close':'stage71c_team_total_closes.csv','meta':'stage71c_last_run.json','user':['user_close_over','user_close_under']},
 'DOUBLE_CHANCE':{'open':'stage71e_double_chance_openers.csv','snap':'stage71e_double_chance_snapshots.csv','close':'stage71e_double_chance_closes.csv','meta':'stage71e_last_run.json','user':['user_close_1x','user_close_x2','user_close_12']},
 'EUROPEAN_HANDICAP':{'open':'stage71f_eh_openers.csv','snap':'stage71f_eh_snapshots.csv','close':'stage71f_eh_closes.csv','meta':'stage71f_last_run.json','user':['user_close_home','user_close_draw','user_close_away']},
 'DRAW_NO_BET':{'open':'stage71g_dnb_openers.csv','snap':'stage71g_dnb_snapshots.csv','close':'stage71g_dnb_closes.csv','meta':'stage71g_last_run.json','user':['user_close_f1_0','user_close_f2_0']},
}

def now_iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def read_csv(name):
 p=OPS/name
 if not p.exists():return []
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def read_json(path):
 try:return json.loads(Path(path).read_text(encoding='utf-8-sig'))
 except:return {}
def fid(r):return str(r.get('api_fixture_id') or r.get('fixture_id') or '').strip()
def is_price(v):
 try:return float(str(v).strip())>1.0
 except:return False
def uniq(rows):return {fid(r) for r in rows if fid(r)}
def settlement_map():
 rows=read_csv('stage71i_market_settlements.csv');out={}
 for r in rows:
  fam=str(r.get('market_family') or '').strip();f=fid(r);status=str(r.get('settlement_status') or '').upper()
  if fam and f and status in {'SETTLED','FINAL','READY'}:out.setdefault(fam,set()).add(f)
 return out

def capture_row(mid,cfg,settled):
 opens=read_csv(cfg['open']);snaps=read_csv(cfg['snap']);closes=read_csv(cfg['close']);meta=read_json(OPS/cfg['meta'])
 oids,sids,cids=uniq(opens),uniq(snaps),uniq(closes)
 executable=set()
 for r in closes:
  if fid(r) and any(is_price(r.get(k)) for k in cfg['user']):executable.add(fid(r))
 settled_ids=set(settled.get(mid,set())) & cids
 n=len(cids);uc=(100.0*len(executable)/n) if n else None;sc=(100.0*len(settled_ids)/n) if n else None
 blockers=[]
 if int(meta.get('signals_created') or 0)!=0:blockers.append('RAW_CAPTURE_SIGNAL_LEAK')
 if n<MIN_CLOSE_FIXTURES:blockers.append(f'CLOSED_FIXTURES_{n}/{MIN_CLOSE_FIXTURES}')
 if n and (uc is None or uc<MIN_USER_COVERAGE):blockers.append(f'MARATHONBET_CLOSE_COVERAGE_{uc:.1f}%/{MIN_USER_COVERAGE:.0f}%')
 if n and (sc is None or sc<MIN_SETTLEMENT_COVERAGE):blockers.append(f'SETTLEMENT_COVERAGE_{sc:.1f}%/{MIN_SETTLEMENT_COVERAGE:.0f}%')
 if n==0:state='COLLECTING_OPENERS'
 elif n<MIN_CLOSE_FIXTURES:state='COLLECTING_CLOSES'
 elif uc is None or uc<MIN_USER_COVERAGE:state='EXECUTION_COVERAGE_REQUIRED'
 elif sc is None or sc<MIN_SETTLEMENT_COVERAGE:state='OUTCOME_LAYER_REQUIRED'
 elif int(meta.get('signals_created') or 0)!=0:state='BLOCKED_SIGNAL_LEAK'
 else:state='DISCOVERY_POOL_READY'
 return {'market_id':mid,'readiness_state':state,'opener_rows':len(opens),'opener_fixtures':len(oids),'snapshot_rows':len(snaps),'snapshot_fixtures':len(sids),'close_rows':len(closes),'close_fixtures':n,'marathonbet_close_fixture_coverage_pct':None if uc is None else round(uc,2),'settled_fixture_coverage_pct':None if sc is None else round(sc,2),'settled_fixtures':len(settled_ids),'signals_created':int(meta.get('signals_created') or 0),'blocking_reasons':blockers}

def main():
 reg=read_json(REGISTRY);settled=settlement_map();byid={x.get('id'):x for x in reg.get('markets',[])};rows=[]
 for mid in ['MATCH_RESULT_1X2','DOUBLE_CHANCE','DRAW_NO_BET','ASIAN_HANDICAP','EUROPEAN_HANDICAP','MATCH_TOTAL','TEAM_TOTAL','BTTS']:
  r=byid.get(mid,{})
  if mid in CAPTURES:base=capture_row(mid,CAPTURES[mid],settled)
  elif mid=='MATCH_RESULT_1X2':base={'market_id':mid,'readiness_state':'ACTIVE_GOVERNED','blocking_reasons':[]}
  elif mid in {'MATCH_TOTAL','BTTS'}:base={'market_id':mid,'readiness_state':'WATCH_GOVERNED','blocking_reasons':[]}
  else:base={'market_id':mid,'readiness_state':'HISTORICAL_NO_CANDIDATE','blocking_reasons':['NEW_INDEPENDENT_HYPOTHESIS_REQUIRED']}
  base.update({'label_ru':r.get('label_ru',mid),'registry_status':r.get('status'),'registry_next_gate':r.get('next_gate')});rows.append(base)
 counts={}
 for r in rows:counts[r['readiness_state']]=counts.get(r['readiness_state'],0)+1
 payload={'generated_at_utc':now_iso(),'status':'OK','scope':'PBK_CORE_8','policy':{'min_unique_close_fixtures_for_discovery_freeze':MIN_CLOSE_FIXTURES,'min_marathonbet_close_coverage_pct':MIN_USER_COVERAGE,'min_settlement_coverage_pct':MIN_SETTLEMENT_COVERAGE,'promotion_effect':'NONE'},'state_counts':counts,'markets':rows,'api_calls':0}
 OPS.mkdir(parents=True,exist_ok=True);OUT_JSON.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 md=['# PBK Core Market Data Readiness','',f"Обновлено UTC: {payload['generated_at_utc']}",'','> Это data-readiness board. `DISCOVERY_POOL_READY` не означает value, WATCH или ставку.','']
 for r in rows:
  md.append(f"## {r['label_ru']} — {r['readiness_state']}")
  if 'close_fixtures' in r:md.append(f"- Openers: {r['opener_rows']} rows / {r['opener_fixtures']} fixtures; snapshots: {r['snapshot_rows']} rows / {r['snapshot_fixtures']} fixtures; closes: {r['close_rows']} rows / {r['close_fixtures']} fixtures.")
  if r.get('marathonbet_close_fixture_coverage_pct') is not None:md.append(f"- Marathonbet close coverage: {r['marathonbet_close_fixture_coverage_pct']}%; settlement coverage: {r['settled_fixture_coverage_pct']}%.")
  md.append('- Blocking: '+('; '.join(r.get('blocking_reasons') or []) if r.get('blocking_reasons') else 'нет на уровне data-readiness policy.'))
  md.append(f"- Next gate: {r.get('registry_next_gate') or 'N/A'}")
  md.append('')
 OUT_MD.write_text('\n'.join(md),encoding='utf-8')
 meta={'run_at_utc':payload['generated_at_utc'],'status':'OK','markets':len(rows),'state_counts':counts,'discovery_pool_ready':sum(1 for r in rows if r['readiness_state']=='DISCOVERY_POOL_READY'),'api_calls':0};META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
