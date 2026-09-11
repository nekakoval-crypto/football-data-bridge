#!/usr/bin/env python3
"""Stage71F probe: discover and inspect a safe pre-match European Handicap market."""
from __future__ import annotations
import json, os, re
from datetime import datetime, timezone
from pathlib import Path
import stage53_daily_screener as s53

OPS=Path(os.getenv('OPS_DIR','ops'));OUT=OPS/'stage71f_european_handicap_probe.json';SEASON=int(os.getenv('API_FOOTBALL_SEASON','2026'))

def norm(v):return ' '.join(re.sub(r'[^a-z0-9]+',' ',str(v or '').lower()).split())
def iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def score(name):
    low=norm(name)
    forbidden=('asian','first half','second half','1st half','2nd half','corner','card','shot','offside','booking')
    if 'handicap' not in low or any(x in low for x in forbidden):return 0
    if low in {'european handicap','handicap result','3 way handicap','three way handicap'}:return 1000
    if 'european' in low:return 900
    if 'result' in low:return 800
    if '3 way' in low or 'three way' in low:return 800
    return 0

def main():
    OPS.mkdir(parents=True,exist_ok=True);bets=(s53.api_get('/odds/bets') or {}).get('response',[]);candidates=[];all_handicap=[]
    for x in bets:
        bid=int(x.get('id') or 0);name=str(x.get('name') or '').strip();low=norm(name)
        if 'handicap' in low:all_handicap.append({'id':bid,'name':name})
        sc=score(name)
        if bid and sc:candidates.append((sc,-len(name),bid,name))
    if not candidates:
        payload={'run_at_utc':iso(),'status':'NO_SAFE_CANDIDATE','all_handicap_bets':all_handicap,'api_calls':1};OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(payload,ensure_ascii=False,indent=2));raise SystemExit(2)
    candidates.sort(reverse=True);_,_,bid,bname=candidates[0]
    fixtures=(s53.api_get('/fixtures',{'league':39,'season':SEASON,'next':10,'timezone':'UTC'}) or {}).get('response',[]);calls=2;sample=None
    for f in fixtures:
        fid=int((f.get('fixture') or {}).get('id') or 0)
        if not fid:continue
        data=s53.api_get('/odds',{'fixture':fid,'bet':bid});calls+=1
        response=(data or {}).get('response',[])
        if not response:continue
        books=[]
        for item in response:
            for bm in item.get('bookmakers',[]) or []:
                if bm.get('name') not in {'Bet365','Marathonbet'}:continue
                for bet in bm.get('bets',[]) or []:
                    if int(bet.get('id') or 0)!=bid:continue
                    books.append({'bookmaker':bm.get('name'),'bet_id':bid,'bet_name':bet.get('name'),'values':[{'value':v.get('value'),'odd':v.get('odd'),'handicap':v.get('handicap'),'main':v.get('main'),'suspended':v.get('suspended')} for v in (bet.get('values',[]) or [])]})
        if books:
            teams=f.get('teams',{}) or {};sample={'api_fixture_id':fid,'home_team':((teams.get('home') or {}).get('name')),'away_team':((teams.get('away') or {}).get('name')),'books':books};break
    payload={'run_at_utc':iso(),'status':'OK' if sample else 'NO_ODDS_SAMPLE','selected_bet_id':bid,'selected_bet_name':bname,'candidate_bets':[{'score':x[0],'id':x[2],'name':x[3]} for x in candidates],'all_handicap_bets':all_handicap,'sample':sample,'api_calls':calls};OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(payload,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
