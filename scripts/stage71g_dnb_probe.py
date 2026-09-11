#!/usr/bin/env python3
"""Stage71G safe probe for full-time DNB / Asian Handicap line 0."""
from __future__ import annotations
import json, os, re
from datetime import datetime, timezone
from pathlib import Path
import stage53_daily_screener as s53
OPS=Path(os.getenv('OPS_DIR','ops'));OUT=OPS/'stage71g_dnb_probe.json';SEASON=int(os.getenv('API_FOOTBALL_SEASON','2026'))
def norm(v):return ' '.join(re.sub(r'[^a-z0-9]+',' ',str(v or '').lower()).split())
def main():
    bets=(s53.api_get('/odds/bets') or {}).get('response',[])
    candidates=[]
    for x in bets:
        bid=int(x.get('id') or 0);name=str(x.get('name') or '').strip();low=norm(name)
        if low=='asian handicap':candidates.append({'id':bid,'name':name,'score':1000})
    if not candidates:raise RuntimeError('Generic full-time Asian Handicap not found')
    candidates.sort(key=lambda x:x['score'],reverse=True);bet=candidates[0]
    fxdata=s53.api_get('/fixtures',{'league':39,'season':SEASON,'next':10,'timezone':'UTC'})
    fixtures=(fxdata or {}).get('response',[])
    if not fixtures:raise RuntimeError('No EPL fixture available for DNB probe')
    sample=None
    for fr in fixtures:
        fx=fr.get('fixture',{}) or {};fid=int(fx.get('id') or 0)
        raw=s53.api_get('/odds',{'fixture':fid,'bet':bet['id']})
        books=[]
        for item in (raw or {}).get('response',[]):
            for bm in item.get('bookmakers',[]) or []:
                if str(bm.get('name') or '') not in {'Bet365','Marathonbet'}:continue
                for b in bm.get('bets',[]) or []:
                    if int(b.get('id') or 0)!=bet['id']:continue
                    vals=[{'value':v.get('value'),'odd':v.get('odd'),'handicap':v.get('handicap'),'main':v.get('main'),'suspended':v.get('suspended')} for v in (b.get('values',[]) or [])]
                    books.append({'bookmaker':bm.get('name'),'bet_id':b.get('id'),'bet_name':b.get('name'),'values':vals})
        if books:
            teams=fr.get('teams',{}) or {};sample={'api_fixture_id':fid,'home_team':((teams.get('home') or {}).get('name') or ''),'away_team':((teams.get('away') or {}).get('name') or ''),'books':books};break
    payload={'run_at_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),'status':'OK','selected_bet_id':bet['id'],'selected_bet_name':bet['name'],'candidate_bets':candidates,'sample':sample,'api_calls_note':'catalog + fixtures + odds until first covered fixture'}
    OPS.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(payload,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
