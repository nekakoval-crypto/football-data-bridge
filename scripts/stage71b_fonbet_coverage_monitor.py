#!/usr/bin/env python3
"""Stage 71B — Fonbet API-Football coverage monitor.

Diagnostic only. Fonbet must not become executable merely because it exists in
API-Football's bookmaker catalogue. This monitor measures real Match Winner
coverage across the locked 16-league PBK scope.
"""
from __future__ import annotations
import csv, json, os, math
from datetime import datetime, timezone
from pathlib import Path

import stage53_daily_screener as s53

OPS=Path(os.getenv('OPS_DIR','ops'))
CATALOG=OPS/'stage71_league_catalog.csv'
LEDGER=OPS/'stage71b_fonbet_probe_ledger.csv'
SUMMARY=OPS/'stage71b_fonbet_coverage.json'
META=OPS/'stage71b_fonbet_last_run.json'
SEASON=int(os.getenv('API_FOOTBALL_SEASON','2026'))
NEXT_PER_LEAGUE=int(os.getenv('STAGE71B_FONBET_NEXT_PER_LEAGUE','3'))
FONBET_ID=int(os.getenv('STAGE71B_FONBET_BOOKMAKER_ID','33'))
MATCH_WINNER_ID=int(os.getenv('STAGE71B_MATCH_WINNER_BET_ID','1'))
FIELDS=['run_at_utc','country','league','api_league_id','fixture_id','kickoff_utc','home_team','away_team','has_1x2','home_odds','draw_odds','away_odds','api_errors']

def now_iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def read_csv(p):
    if not p.exists():return []
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write_csv(p, rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore');w.writeheader();w.writerows(rows)
def fnum(v):
    try:
        x=float(str(v));return x if math.isfinite(x) else None
    except:return None

def extract_1x2(payload):
    home=draw=away=None
    for event in (payload or {}).get('response',[]) or []:
        for bm in event.get('bookmakers',[]) or []:
            if int(bm.get('id') or -1)!=FONBET_ID and str(bm.get('name') or '').strip().lower()!='fonbet':continue
            for bet in bm.get('bets',[]) or []:
                if int(bet.get('id') or -1)!=MATCH_WINNER_ID and str(bet.get('name') or '').strip().lower()!='match winner':continue
                for val in bet.get('values',[]) or []:
                    name=str(val.get('value') or '').strip().lower();odd=fnum(val.get('odd'))
                    if name in {'home','1'}:home=odd
                    elif name in {'draw','x'}:draw=odd
                    elif name in {'away','2'}:away=odd
    return home,draw,away

def main():
    run_at=now_iso(); warnings=[]; api_calls=0
    catalog=[r for r in read_csv(CATALOG) if r.get('api_league_id')]
    if not catalog:
        META.write_text(json.dumps({'run_at_utc':run_at,'status':'WAITING_FOR_STAGE71_CATALOG'},indent=2),encoding='utf-8');return
    ledger=read_csv(LEDGER); new=[]
    for lg in catalog:
        lid=str(lg['api_league_id'])
        try:
            fixtures=s53.api_get('/fixtures',{'league':lid,'season':SEASON,'next':NEXT_PER_LEAGUE,'timezone':'UTC'});api_calls+=1
            upcoming=(fixtures or {}).get('response',[]) or []
        except Exception as e:
            warnings.append(f"{lg.get('league')}: next fixtures error {e}");continue
        for x in upcoming:
            fx=x.get('fixture',{}) or {};teams=x.get('teams',{}) or {};home=(teams.get('home') or {});away=(teams.get('away') or {})
            fid=str(fx.get('id') or '')
            if not fid:continue
            try:
                odds=s53.api_get('/odds',{'fixture':fid,'bookmaker':FONBET_ID,'bet':MATCH_WINNER_ID});api_calls+=1
                h,d,a=extract_1x2(odds)
                errs=(odds or {}).get('errors') or []
            except Exception as e:
                h=d=a=None;errs=[str(e)]
            new.append({'run_at_utc':run_at,'country':lg.get('country') or '','league':lg.get('league') or '','api_league_id':lid,
                        'fixture_id':fid,'kickoff_utc':fx.get('date') or '','home_team':home.get('name') or '','away_team':away.get('name') or '',
                        'has_1x2':'YES' if all(v is not None for v in (h,d,a)) else 'NO','home_odds':'' if h is None else h,
                        'draw_odds':'' if d is None else d,'away_odds':'' if a is None else a,'api_errors':json.dumps(errs,ensure_ascii=False) if errs else ''})
    ledger.extend(new);write_csv(LEDGER,ledger)
    checked=len(new);covered=sum(1 for r in new if r.get('has_1x2')=='YES');pct=100.0*covered/checked if checked else None
    # Distinct-fixture historical coverage prevents repeated runs on the same fixture from inflating the sample.
    by_fixture={}
    for r in ledger:
        fid=r.get('fixture_id') or ''
        if fid:by_fixture[fid]=r
    distinct=list(by_fixture.values());d_cov=sum(1 for r in distinct if r.get('has_1x2')=='YES');d_pct=100.0*d_cov/len(distinct) if distinct else None
    status='AUTO_REVIEW_ELIGIBLE' if len(distinct)>=30 and (d_pct or 0)>=90 else 'AUTO_CANDIDATE_MONITORING'
    payload={'run_at_utc':run_at,'status':'OK','bookmaker':'Fonbet','bookmaker_id':FONBET_ID,'current_checked':checked,'current_covered':covered,
             'current_coverage_pct':None if pct is None else round(pct,2),'distinct_fixtures_checked':len(distinct),'distinct_fixtures_covered':d_cov,
             'distinct_coverage_pct':None if d_pct is None else round(d_pct,2),'governance_status':status,
             'auto_review_gate':{'min_distinct_fixtures':30,'min_coverage_pct':90,'meaning':'review only; never automatic executable promotion'},
             'api_calls':api_calls,'warnings':warnings}
    SUMMARY.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    META.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(payload,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
