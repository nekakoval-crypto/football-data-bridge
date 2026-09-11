#!/usr/bin/env python3
"""Stage71E: prospective full-time Double Chance market capture.

Research data only. Captures real Bet365 and Marathonbet 1X/X2/12 prices.
Never derives executable Double Chance odds from 1X2 and creates no signals.
"""
from __future__ import annotations
import csv, json, math, os, re
from datetime import datetime, timezone
from pathlib import Path
import stage53_daily_screener as s53

OPS=Path(os.getenv('OPS_DIR','ops'))
OPENERS=OPS/'stage71e_double_chance_openers.csv';SNAPS=OPS/'stage71e_double_chance_snapshots.csv';CLOSES=OPS/'stage71e_double_chance_closes.csv';META=OPS/'stage71e_last_run.json'
SEASON=int(os.getenv('API_FOOTBALL_SEASON','2026'));USER_BOOK=os.getenv('STAGE71E_USER_BOOKMAKER','Marathonbet').strip();OPEN_H=float(os.getenv('STAGE71E_OPEN_HORIZON_H','336'));TRACK_H=float(os.getenv('STAGE71E_TRACK_HORIZON_H','72'));NEXT_N=int(os.getenv('STAGE71E_NEXT_PER_LEAGUE','10'));BET_OVERRIDE=os.getenv('STAGE71E_DOUBLE_CHANCE_BET_ID','').strip()
LEAGUES={'Premier League':39,'La Liga':140,'Serie A':135,'Bundesliga':78,'Ligue 1':61,'Austrian Bundesliga':218,'Belgian Pro League':144,'Danish Superliga':119,'A Lyga':362,'Virsliga':365,'Eredivisie':88,'Eliteserien':103,'Ekstraklasa':106,'Primeira Liga':94,'Super Lig':203,'Scottish Premiership':179}
OPEN_FIELDS=['api_fixture_id','league','league_id','captured_at_utc','kickoff_utc','home_team','away_team','bet_id','bet_name','open_b365_1x','open_b365_x2','open_b365_12','open_p_1x','open_p_x2','open_p_12','status','source']
SNAP_FIELDS=['api_fixture_id','league','league_id','captured_at_utc','kickoff_utc','minutes_to_kickoff','home_team','away_team','bet_id','bet_name','b365_1x','b365_x2','b365_12','p_1x','p_x2','p_12','open_p_1x','open_p_x2','open_p_12','move_1x_pp','move_x2_pp','move_12_pp','user_bookmaker','user_1x','user_x2','user_12','api_odds_update_utc']
CLOSE_FIELDS=['api_fixture_id','league','league_id','locked_at_utc','kickoff_utc','close_observed_at_utc','close_gap_minutes','home_team','away_team','bet_id','bet_name','open_p_1x','open_p_x2','open_p_12','close_p_1x','close_p_x2','close_p_12','move_1x_pp','move_x2_pp','move_12_pp','bet365_close_1x','bet365_close_x2','bet365_close_12','user_bookmaker','user_close_1x','user_close_x2','user_close_12','status','note']

def now():return datetime.now(timezone.utc).replace(microsecond=0)
def iso(d):return d.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z') if d else ''
def dt(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None
def num(v):
    try:
        x=float(str(v).strip());return x if math.isfinite(x) else None
    except:return None
def norm(v):return ' '.join(re.sub(r'[^a-z0-9]+',' ',str(v or '').lower()).split())
def read(p):
    if not p.exists():return []
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,fields,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def discover_bet():
    rows=(s53.api_get('/odds/bets') or {}).get('response',[])
    if BET_OVERRIDE:
        bid=int(BET_OVERRIDE);name=next((str(x.get('name') or '') for x in rows if int(x.get('id') or 0)==bid),'override');return bid,name
    c=[]
    for x in rows:
        bid=int(x.get('id') or 0);name=str(x.get('name') or '').strip();low=norm(name)
        if not bid or any(z in low for z in ('first half','second half','1st half','2nd half')):continue
        score=1000 if low=='double chance' else (800 if 'double chance' in low else 0)
        if score:c.append((score,-len(name),bid,name))
    if not c:raise RuntimeError('Could not discover generic full-time Double Chance bet')
    c.sort(reverse=True);_,_,bid,name=c[0];return bid,name

def sel(v):
    low=norm(v.get('value'))
    has_h=any(x in low.split() for x in ('home','1'))
    has_a=any(x in low.split() for x in ('away','2'))
    has_d=any(x in low.split() for x in ('draw','x'))
    if has_h and has_d and not has_a:return '1X'
    if has_a and has_d and not has_h:return 'X2'
    if has_h and has_a and not has_d:return '12'
    compact=low.replace(' ','')
    if compact in {'1x','x1'}:return '1X'
    if compact in {'x2','2x'}:return 'X2'
    if compact in {'12','21'}:return '12'
    return ''

def prices(resp,bid):
    out={}
    for item in (resp or {}).get('response',[]):
        upd=item.get('update') or ''
        for bm in item.get('bookmakers',[]) or []:
            bname=bm.get('name') or '';bk=norm(bname);z=out.setdefault(bk,{'display':bname,'update':'','1X':None,'X2':None,'12':None});z['update']=max(z['update'],upd)
            for bet in bm.get('bets',[]) or []:
                if int(bet.get('id') or 0)!=int(bid):continue
                for v in bet.get('values',[]) or []:
                    s=sel(v);o=num(v.get('odd'))
                    if s and o is not None and o>1 and (z[s] is None or o>z[s]):z[s]=o
    return out

def triplet(bookmap,book):
    z=bookmap.get(norm(book))
    if not z or any(num(z.get(k)) is None for k in ('1X','X2','12')):return None
    return z

def probs(z):
    inv=[1/z[k] for k in ('1X','X2','12')];s=sum(inv);return {'1X':inv[0]/s,'X2':inv[1]/s,'12':inv[2]/s}
def upcoming():
    out=[]
    for lname,lid in LEAGUES.items():
        data=s53.api_get('/fixtures',{'league':lid,'season':SEASON,'next':NEXT_N,'timezone':'UTC'})
        for r in (data or {}).get('response',[]):
            fx=r.get('fixture',{}) or {};teams=r.get('teams',{}) or {};ko=dt(fx.get('date'))
            if ko:out.append({'id':str(fx.get('id') or ''),'league':lname,'league_id':lid,'kickoff':ko,'home':((teams.get('home') or {}).get('name') or ''),'away':((teams.get('away') or {}).get('name') or '')})
    return out

def main():
    t=now();OPS.mkdir(parents=True,exist_ok=True);bid,bname=discover_bet();openers, snaps, closes=read(OPENERS),read(SNAPS),read(CLOSES);ob={str(r.get('api_fixture_id')):r for r in openers};cb={str(r.get('api_fixture_id')):r for r in closes};fixtures=upcoming();ao=asn=ac=calls=0;warnings=[]
    for fx in fixtures:
        h=(fx['kickoff']-t).total_seconds()/3600
        if h<=0 or h>OPEN_H:continue
        fid=fx['id'];opened=ob.get(fid)
        if opened and h>TRACK_H:continue
        try:bm=prices(s53.api_get('/odds',{'fixture':fid,'bet':bid}),bid);calls+=1
        except Exception as e:warnings.append(f'odds {fid}: {e}');continue
        b365=triplet(bm,'Bet365');user=triplet(bm,USER_BOOK) if USER_BOOK else None
        if not b365:continue
        p=probs(b365)
        if opened is None:
            opened={'api_fixture_id':fid,'league':fx['league'],'league_id':fx['league_id'],'captured_at_utc':iso(t),'kickoff_utc':iso(fx['kickoff']),'home_team':fx['home'],'away_team':fx['away'],'bet_id':bid,'bet_name':bname,'open_b365_1x':b365['1X'],'open_b365_x2':b365['X2'],'open_b365_12':b365['12'],'open_p_1x':f"{p['1X']:.8f}",'open_p_x2':f"{p['X2']:.8f}",'open_p_12':f"{p['12']:.8f}",'status':'FROZEN','source':'API-Football Bet365 first complete Double Chance triplet captured prospectively'};openers.append(opened);ob[fid]=opened;ao+=1
        if h<=TRACK_H:
            moves={k:p[k]-num(opened.get('open_p_'+k.lower())) for k in ('1X','X2','12')}
            snaps.append({'api_fixture_id':fid,'league':fx['league'],'league_id':fx['league_id'],'captured_at_utc':iso(t),'kickoff_utc':iso(fx['kickoff']),'minutes_to_kickoff':f'{h*60:.1f}','home_team':fx['home'],'away_team':fx['away'],'bet_id':bid,'bet_name':bname,'b365_1x':b365['1X'],'b365_x2':b365['X2'],'b365_12':b365['12'],'p_1x':f"{p['1X']:.8f}",'p_x2':f"{p['X2']:.8f}",'p_12':f"{p['12']:.8f}",'open_p_1x':opened.get('open_p_1x',''),'open_p_x2':opened.get('open_p_x2',''),'open_p_12':opened.get('open_p_12',''),'move_1x_pp':f"{moves['1X']:.8f}",'move_x2_pp':f"{moves['X2']:.8f}",'move_12_pp':f"{moves['12']:.8f}",'user_bookmaker':USER_BOOK,'user_1x':user['1X'] if user else '','user_x2':user['X2'] if user else '','user_12':user['12'] if user else '','api_odds_update_utc':max(b365.get('update') or '',user.get('update') or '' if user else '')});asn+=1
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
        ct=dt(s.get('captured_at_utc'));row={'api_fixture_id':fid,'league':o.get('league',''),'league_id':o.get('league_id',''),'locked_at_utc':iso(t),'kickoff_utc':o.get('kickoff_utc',''),'close_observed_at_utc':s.get('captured_at_utc',''),'close_gap_minutes':'' if not ct else f'{(ko-ct).total_seconds()/60:.1f}','home_team':o.get('home_team',''),'away_team':o.get('away_team',''),'bet_id':bid,'bet_name':bname,'open_p_1x':o.get('open_p_1x',''),'open_p_x2':o.get('open_p_x2',''),'open_p_12':o.get('open_p_12',''),'close_p_1x':s.get('p_1x',''),'close_p_x2':s.get('p_x2',''),'close_p_12':s.get('p_12',''),'move_1x_pp':s.get('move_1x_pp',''),'move_x2_pp':s.get('move_x2_pp',''),'move_12_pp':s.get('move_12_pp',''),'bet365_close_1x':s.get('b365_1x',''),'bet365_close_x2':s.get('b365_x2',''),'bet365_close_12':s.get('b365_12',''),'user_bookmaker':USER_BOOK,'user_close_1x':s.get('user_1x',''),'user_close_x2':s.get('user_x2',''),'user_close_12':s.get('user_12',''),'status':'OBSERVED_CLOSE_FROZEN','note':'Latest stored pre-kickoff exact Double Chance triplet'};closes.append(row);cb[fid]=row;ac+=1
    write(OPENERS,OPEN_FIELDS,openers);write(SNAPS,SNAP_FIELDS,snaps);write(CLOSES,CLOSE_FIELDS,closes)
    meta={'run_at_utc':iso(t),'status':'OK','mode':'PROSPECTIVE_CAPTURE_ONLY','leagues':len(LEAGUES),'fixtures_scanned':len(fixtures),'double_chance_bet_id':bid,'double_chance_bet_name':bname,'odds_calls':calls,'new_openers':ao,'new_snapshots':asn,'new_closes':ac,'total_openers':len(openers),'total_snapshots':len(snaps),'total_closes':len(closes),'signals_created':0,'warnings':warnings[:50]};META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
