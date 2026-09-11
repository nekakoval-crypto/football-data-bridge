#!/usr/bin/env python3
"""Stage71G: prospective full-time Draw No Bet / Asian Handicap line 0 capture.

Research data only. Captures real Bet365 and Marathonbet Ф1(0)/Ф2(0) prices.
Creates no betting signals and does not revive the rejected Stage71D hypothesis.
"""
from __future__ import annotations
import csv, json, math, os, re
from datetime import datetime, timezone
from pathlib import Path
import stage53_daily_screener as s53

OPS=Path(os.getenv('OPS_DIR','ops'))
OPENERS=OPS/'stage71g_dnb_openers.csv';SNAPS=OPS/'stage71g_dnb_snapshots.csv';CLOSES=OPS/'stage71g_dnb_closes.csv';META=OPS/'stage71g_last_run.json'
SEASON=int(os.getenv('API_FOOTBALL_SEASON','2026'));USER_BOOK=os.getenv('STAGE71G_USER_BOOKMAKER','Marathonbet').strip();OPEN_H=float(os.getenv('STAGE71G_OPEN_HORIZON_H','336'));TRACK_H=float(os.getenv('STAGE71G_TRACK_HORIZON_H','72'));NEXT_N=int(os.getenv('STAGE71G_NEXT_PER_LEAGUE','10'));BET_ID=int(os.getenv('STAGE71G_AH_BET_ID','4'))
LEAGUES={'Premier League':39,'La Liga':140,'Serie A':135,'Bundesliga':78,'Ligue 1':61,'Austrian Bundesliga':218,'Belgian Pro League':144,'Danish Superliga':119,'A Lyga':362,'Virsliga':365,'Eredivisie':88,'Eliteserien':103,'Ekstraklasa':106,'Primeira Liga':94,'Super Lig':203,'Scottish Premiership':179}
OPEN_FIELDS=['api_fixture_id','league','league_id','captured_at_utc','kickoff_utc','home_team','away_team','bet_id','bet_name','line','open_b365_f1_0','open_b365_f2_0','open_p_f1_0','open_p_f2_0','status','source']
SNAP_FIELDS=['api_fixture_id','league','league_id','captured_at_utc','kickoff_utc','minutes_to_kickoff','home_team','away_team','bet_id','bet_name','line','b365_f1_0','b365_f2_0','p_f1_0','p_f2_0','open_p_f1_0','open_p_f2_0','move_f1_0_pp','move_f2_0_pp','user_bookmaker','user_f1_0','user_f2_0','api_odds_update_utc']
CLOSE_FIELDS=['api_fixture_id','league','league_id','locked_at_utc','kickoff_utc','close_observed_at_utc','close_gap_minutes','home_team','away_team','bet_id','bet_name','line','open_p_f1_0','open_p_f2_0','close_p_f1_0','close_p_f2_0','move_f1_0_pp','move_f2_0_pp','bet365_close_f1_0','bet365_close_f2_0','user_bookmaker','user_close_f1_0','user_close_f2_0','status','note']

def now():return datetime.now(timezone.utc).replace(microsecond=0)
def iso(d):return d.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z') if d else ''
def dt(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None
def num(v):
    try:
        x=float(str(v).strip());return x if math.isfinite(x) else None
    except:return None
def norm(v):return ' '.join(re.sub(r'[^a-z0-9.+-]+',' ',str(v or '').lower()).split())
def read(p):
    if not p.exists():return []
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,fields,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def verify_market():
    rows=(s53.api_get('/odds/bets') or {}).get('response',[])
    hit=next((x for x in rows if int(x.get('id') or 0)==BET_ID),None)
    if not hit or norm(hit.get('name'))!='asian handicap':raise RuntimeError(f'Bet id {BET_ID} is not generic full-time Asian Handicap')
    return str(hit.get('name') or 'Asian Handicap')

def parse_value(v):
    text=norm(v.get('value'));m=re.match(r'^(home|away)\s*([+-]?\d+(?:\.\d+)?)$',text)
    if not m:return None
    line=num(m.group(2))
    if line is None or abs(line)>1e-9:return None
    return ('H' if m.group(1)=='home' else 'A'),num(v.get('odd'))

def prices(resp):
    out={}
    for item in (resp or {}).get('response',[]):
        upd=item.get('update') or ''
        for bm in item.get('bookmakers',[]) or []:
            bname=str(bm.get('name') or '');bk=bname.lower();z=out.setdefault(bk,{'display':bname,'update':'','H':None,'A':None});z['update']=max(z['update'],upd)
            for bet in bm.get('bets',[]) or []:
                if int(bet.get('id') or 0)!=BET_ID:continue
                for v in bet.get('values',[]) or []:
                    p=parse_value(v)
                    if not p:continue
                    side,odd=p
                    if odd is not None and odd>1 and (z[side] is None or odd>z[side]):z[side]=odd
    return out

def pair(bookmap,name):
    z=bookmap.get(str(name).lower())
    if not z or num(z.get('H')) is None or num(z.get('A')) is None:return None
    return z
def probs(z):
    ih,ia=1/z['H'],1/z['A'];s=ih+ia;return {'H':ih/s,'A':ia/s}
def upcoming():
    out=[]
    for lname,lid in LEAGUES.items():
        data=s53.api_get('/fixtures',{'league':lid,'season':SEASON,'next':NEXT_N,'timezone':'UTC'})
        for r in (data or {}).get('response',[]):
            fx=r.get('fixture',{}) or {};teams=r.get('teams',{}) or {};ko=dt(fx.get('date'))
            if ko:out.append({'id':str(fx.get('id') or ''),'league':lname,'league_id':lid,'kickoff':ko,'home':((teams.get('home') or {}).get('name') or ''),'away':((teams.get('away') or {}).get('name') or '')})
    return out

def main():
    t=now();OPS.mkdir(parents=True,exist_ok=True);bname=verify_market();openers,snaps,closes=read(OPENERS),read(SNAPS),read(CLOSES);ob={str(r.get('api_fixture_id')):r for r in openers};cb={str(r.get('api_fixture_id')):r for r in closes};fixtures=upcoming();ao=asn=ac=calls=0;warnings=[]
    for fx in fixtures:
        h=(fx['kickoff']-t).total_seconds()/3600
        if h<=0 or h>OPEN_H:continue
        fid=fx['id'];opened=ob.get(fid)
        if opened and h>TRACK_H:continue
        try:bm=prices(s53.api_get('/odds',{'fixture':fid,'bet':BET_ID}));calls+=1
        except Exception as e:warnings.append(f'odds {fid}: {e}');continue
        b365=pair(bm,'Bet365');user=pair(bm,USER_BOOK) if USER_BOOK else None
        if not b365:continue
        p=probs(b365)
        if opened is None:
            opened={'api_fixture_id':fid,'league':fx['league'],'league_id':fx['league_id'],'captured_at_utc':iso(t),'kickoff_utc':iso(fx['kickoff']),'home_team':fx['home'],'away_team':fx['away'],'bet_id':BET_ID,'bet_name':bname,'line':'0','open_b365_f1_0':b365['H'],'open_b365_f2_0':b365['A'],'open_p_f1_0':f"{p['H']:.8f}",'open_p_f2_0':f"{p['A']:.8f}",'status':'FROZEN','source':'API-Football Bet365 first complete full-time Asian Handicap line 0 pair captured prospectively'};openers.append(opened);ob[fid]=opened;ao+=1
        if h<=TRACK_H:
            oh=num(opened.get('open_p_f1_0'));oa=num(opened.get('open_p_f2_0'))
            snaps.append({'api_fixture_id':fid,'league':fx['league'],'league_id':fx['league_id'],'captured_at_utc':iso(t),'kickoff_utc':iso(fx['kickoff']),'minutes_to_kickoff':f'{h*60:.1f}','home_team':fx['home'],'away_team':fx['away'],'bet_id':BET_ID,'bet_name':bname,'line':'0','b365_f1_0':b365['H'],'b365_f2_0':b365['A'],'p_f1_0':f"{p['H']:.8f}",'p_f2_0':f"{p['A']:.8f}",'open_p_f1_0':opened.get('open_p_f1_0',''),'open_p_f2_0':opened.get('open_p_f2_0',''),'move_f1_0_pp':'' if oh is None else f"{p['H']-oh:.8f}",'move_f2_0_pp':'' if oa is None else f"{p['A']-oa:.8f}",'user_bookmaker':USER_BOOK,'user_f1_0':user['H'] if user else '','user_f2_0':user['A'] if user else '','api_odds_update_utc':max(b365.get('update') or '',user.get('update') or '' if user else '')});asn+=1
    latest={}
    for r in snaps:
        fid=str(r.get('api_fixture_id'));st=dt(r.get('captured_at_utc'));ko=dt(r.get('kickoff_utc'))
        if not fid or not st or not ko or st>ko:continue
        old=latest.get(fid);oldt=dt(old.get('captured_at_utc')) if old else None
        if old is None or oldt is None or st>oldt:latest[fid]=r
    for fid,o in list(ob.items()):
        if fid in cb:continue
        ko=dt(o.get('kickoff_utc'))
        if not ko or t<ko:continue
        s=latest.get(fid)
        if not s:continue
        ct=dt(s.get('captured_at_utc'));row={'api_fixture_id':fid,'league':o.get('league',''),'league_id':o.get('league_id',''),'locked_at_utc':iso(t),'kickoff_utc':o.get('kickoff_utc',''),'close_observed_at_utc':s.get('captured_at_utc',''),'close_gap_minutes':'' if not ct else f'{(ko-ct).total_seconds()/60:.1f}','home_team':o.get('home_team',''),'away_team':o.get('away_team',''),'bet_id':BET_ID,'bet_name':bname,'line':'0','open_p_f1_0':o.get('open_p_f1_0',''),'open_p_f2_0':o.get('open_p_f2_0',''),'close_p_f1_0':s.get('p_f1_0',''),'close_p_f2_0':s.get('p_f2_0',''),'move_f1_0_pp':s.get('move_f1_0_pp',''),'move_f2_0_pp':s.get('move_f2_0_pp',''),'bet365_close_f1_0':s.get('b365_f1_0',''),'bet365_close_f2_0':s.get('b365_f2_0',''),'user_bookmaker':USER_BOOK,'user_close_f1_0':s.get('user_f1_0',''),'user_close_f2_0':s.get('user_f2_0',''),'status':'OBSERVED_CLOSE_FROZEN','note':'Latest stored pre-kickoff exact Asian Handicap line 0 pair'};closes.append(row);cb[fid]=row;ac+=1
    write(OPENERS,OPEN_FIELDS,openers);write(SNAPS,SNAP_FIELDS,snaps);write(CLOSES,CLOSE_FIELDS,closes)
    meta={'run_at_utc':iso(t),'status':'OK','mode':'PROSPECTIVE_CAPTURE_ONLY','leagues':len(LEAGUES),'fixtures_scanned':len(fixtures),'dnb_bet_id':BET_ID,'dnb_bet_name':bname,'dnb_line':'0','odds_calls':calls,'new_openers':ao,'new_snapshots':asn,'new_closes':ac,'total_openers':len(openers),'total_snapshots':len(snaps),'total_closes':len(closes),'signals_created':0,'warnings':warnings[:50]};META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
