#!/usr/bin/env python3
"""Stage71K — offline source audit for PBK deferred market universe.

Consumes the API-Football bet catalog and per-bet fixture presence persisted by
Stage71J. Makes zero API calls. It does not create betting signals, candidates
or promotion decisions; it only maps source availability/coverage.
"""
from __future__ import annotations
import json, os, re
from datetime import datetime, timezone
from pathlib import Path

OPS=Path(os.getenv('OPS_DIR','ops'))
CAT=OPS/'api_football_odds_bet_catalog.json'
PRES=OPS/'api_football_market_presence.json'
OUT=OPS/'stage71k_deferred_market_source_audit.json'
OUT_MD=OPS/'stage71k_deferred_market_source_audit.md'
META=OPS/'stage71k_last_run.json'

GROUPS=[
 ('EXACT_SCORE','Точный счёт',[r'correct score',r'exact score',r'score exact']),
 ('BTTS_TOTAL_COMBOS','Комбо ОЗ + ТБ/ТМ / исход + тотал',[r'both teams.*(over|under|total)',r'(over|under|total).*both teams',r'result.*(over|under|total)',r'(over|under|total).*result',r'double chance.*(over|under|total)']),
 ('PLAYER_PROPS','Игроки / бомбардиры',[r'player',r'scorer',r'to score',r'anytime goal',r'first goalscorer',r'last goalscorer']),
 ('CORNERS','Угловые',[r'corner']),
 ('CARDS_BOOKINGS','Карточки / предупреждения',[r'card',r'booking']),
 ('SHOTS','Удары / удары в створ',[r'shot']),
 ('OFFSIDES','Офсайды',[r'offside']),
 ('HALVES_PERIODS','Таймы / периодные рынки',[r'first half',r'second half',r'1st half',r'2nd half',r'half time',r'halftime']),
 ('GOAL_TIMING_INTERVALS','Время гола / интервалы',[r'time of.*goal',r'goal.*minute',r'goal interval',r'first goal time',r'last goal time']),
]

def now_iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def read(p):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except Exception:return None
def norm(s):return ' '.join(str(s or '').lower().replace('-',' ').replace('_',' ').split())
def tags(name):
 low=norm(name);out=[]
 for gid,label,pats in GROUPS:
  if any(re.search(p,low,re.I) for p in pats):out.append(gid)
 return out

def source_status(rows):
 if not rows:return 'SEPARATE_SOURCE_REQUIRED_OR_NOT_IN_CATALOG'
 observed=[r for r in rows if int(r.get('fixtures_any') or 0)>0]
 if not observed:return 'CATALOG_ONLY_NO_OBSERVED_COVERAGE_YET'
 max_m=max(float(r.get('marathonbet_coverage_pct') or 0) for r in observed)
 max_b=max(float(r.get('bet365_coverage_pct') or 0) for r in observed)
 if max_m>=20:return 'API_FOOTBALL_PROSPECTIVE_SOURCE_POSSIBLE'
 if max_b>=20:return 'BET365_REFERENCE_PRESENT_USER_BOOK_SOURCE_WEAK'
 return 'LOW_OBSERVED_COVERAGE_REVIEW'

def main():
 cat=read(CAT);pres=read(PRES)
 if not cat or not pres:
  payload={'run_at_utc':now_iso(),'status':'WAITING_STAGE71J_CATALOG','api_calls':0,'signals_created':0,'missing':[str(p.name) for p,x in ((CAT,cat),(PRES,pres)) if not x]}
  META.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');OUT_MD.write_text('# Stage71K Deferred Market Source Audit\n\nОжидается следующий Stage71J shared capture. API calls: 0.\n',encoding='utf-8');print(json.dumps(payload,ensure_ascii=False));return
 catalog=cat.get('response') or [];presence={int(r.get('bet_id')):r for r in (pres.get('markets') or []) if str(r.get('bet_id') or '').isdigit()}
 details=[]
 for b in catalog:
  try:bid=int(b.get('id'))
  except Exception:continue
  name=str(b.get('name') or '').strip();btags=tags(name)
  if not btags:continue
  pr=presence.get(bid,{})
  details.append({'bet_id':bid,'bet_name':name,'deferred_groups':btags,'fixtures_any':int(pr.get('fixtures_any') or 0),'fixtures_bet365':int(pr.get('fixtures_bet365') or 0),'fixtures_marathonbet':int(pr.get('fixtures_marathonbet') or 0),'bet365_coverage_pct':float(pr.get('bet365_coverage_pct') or 0),'marathonbet_coverage_pct':float(pr.get('marathonbet_coverage_pct') or 0)})
 groups=[]
 for gid,label,_ in GROUPS:
  rows=[r for r in details if gid in r['deferred_groups']]
  observed=[r for r in rows if r['fixtures_any']>0]
  groups.append({'group_id':gid,'label_ru':label,'catalog_market_count':len(rows),'observed_market_count':len(observed),'source_status':source_status(rows),'max_bet365_coverage_pct':max([r['bet365_coverage_pct'] for r in rows] or [0]),'max_marathonbet_coverage_pct':max([r['marathonbet_coverage_pct'] for r in rows] or [0]),'top_observed_markets':sorted(observed,key=lambda x:(x['marathonbet_coverage_pct'],x['bet365_coverage_pct'],x['fixtures_any']),reverse=True)[:10]})
 payload={'generated_at_utc':now_iso(),'status':'OK','mode':'OFFLINE_SOURCE_AUDIT_ONLY','fixture_sample':int(pres.get('fixture_sample') or 0),'catalog_market_count':len(catalog),'deferred_tagged_market_count':len(details),'groups':groups,'details':details,'api_calls':0,'signals_created':0,'policy':'Source availability only. No strategy hypothesis, no WATCH, no promotion. Coverage in one current fixture sample is descriptive, not evidence of edge.'}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 lines=['# Stage71K — Deferred Market Source Audit','',f"Fixture sample: **{payload['fixture_sample']}** | API calls: **0**",'', '> Это аудит источников, не поиск стратегии и не рекомендация.','']
 for g in groups:
  lines += [f"## {g['label_ru']}",f"- Catalog markets: {g['catalog_market_count']} | observed: {g['observed_market_count']}",f"- Source status: **{g['source_status']}**",f"- Max coverage: Bet365 {g['max_bet365_coverage_pct']:.1f}% | Marathonbet {g['max_marathonbet_coverage_pct']:.1f}%"]
  for r in g['top_observed_markets'][:5]:lines.append(f"  - bet {r['bet_id']} `{r['bet_name']}` — Bet365 {r['bet365_coverage_pct']:.1f}% | Marathonbet {r['marathonbet_coverage_pct']:.1f}%")
  lines.append('')
 OUT_MD.write_text('\n'.join(lines),encoding='utf-8')
 meta={'run_at_utc':payload['generated_at_utc'],'status':'OK','fixture_sample':payload['fixture_sample'],'catalog_market_count':len(catalog),'deferred_tagged_market_count':len(details),'groups':len(groups),'groups_with_observed_coverage':sum(1 for g in groups if g['observed_market_count']>0),'api_calls':0,'signals_created':0};META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(meta,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
