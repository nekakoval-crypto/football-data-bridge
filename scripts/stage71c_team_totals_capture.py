#!/usr/bin/env python3
"""Stage71C: prospective individual team-total market capture.

Research data only. No WATCH, no canonical signal, no promotion decision.
Captures all observed full-time team-total GOAL lines for PBK's locked 16 leagues.
"""
from __future__ import annotations
import csv, json, math, os, re
from datetime import datetime, timezone
from pathlib import Path
import stage53_daily_screener as s53

OPS=Path(os.getenv('OPS_DIR','ops'))
OPENERS=OPS/'stage71c_team_total_openers.csv'; SNAPS=OPS/'stage71c_team_total_snapshots.csv'; CLOSES=OPS/'stage71c_team_total_closes.csv'; META=OPS/'stage71c_last_run.json'
SEASON=int(os.getenv('API_FOOTBALL_SEASON','2026')); USER_BOOK=os.getenv('STAGE71C_USER_BOOKMAKER','Marathonbet').strip()
OPEN_H=float(os.getenv('STAGE71C_OPEN_HORIZON_H','336')); TRACK_H=float(os.getenv('STAGE71C_TRACK_HORIZON_H','72')); NEXT_N=int(os.getenv('STAGE71C_NEXT_PER_LEAGUE','10'))
HOME_OVERRIDE=os.getenv('STAGE71C_HOME_TEAM_TOTAL_BET_ID','').strip(); AWAY_OVERRIDE=os.getenv('STAGE71C_AWAY_TEAM_TOTAL_BET_ID','').strip()
LEAGUES={'Premier League':39,'La Liga':140,'Serie A':135,'Bundesliga':78,'Ligue 1':61,'Austrian Bundesliga':218,'Belgian Pro League':144,'Danish Superliga':119,'A Lyga':362,'Virsliga':365,'Eredivisie':88,'Eliteserien':103,'Ekstraklasa':106,'Primeira Liga':94,'Super Lig':203,'Scottish Premiership':179}
OPEN_FIELDS=['market_key','api_fixture_id','league','league_id','captured_at_utc','kickoff_utc','home_team','away_team','team_side','team_name','line','bet_id','bet_name','open_b365_over','open_b365_under','open_p_over','open_p_under','status','source']
SNAP_FIELDS=['market_key','api_fixture_id','league','league_id','captured_at_utc','kickoff_utc','minutes_to_kickoff','home_team','away_team','team_side','team_name','line','bet_id','bet_name','b365_over','b365_under','p_over','p_under','open_p_over','over_move_pp','user_bookmaker','user_over','user_under','api_odds_update_utc']
CLOSE_FIELDS=['market_key','api_fixture_id','league','league_id','locked_at_utc','kickoff_utc','close_observed_at_utc','close_gap_minutes','home_team','away_team','team_side','team_name','line','bet_id','bet_name','open_p_over','close_p_over','movement_pp','bet365_close_over','bet365_close_under','user_bookmaker','user_close_over','user_close_under','status','note']

def now(): return datetime.now(timezone.utc).replace(microsecond=0)
def iso(d): return d.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z') if d else ''
def dt(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None
def num(v):
    try:
        x=float(str(v).strip()); return x if math.isfinite(x) else None
    except:return None
def norm(v): return ' '.join(str(v or '').strip().lower().replace('-',' ').replace('_',' ').split())
def read(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(path,fields,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def novig(o,u):
    o,u=num(o),num(u)
    if o is None or u is None or o<=1 or u<=1:return None
    io,iu=1/o,1/u; return io/(io+iu)

FORBIDDEN_MARKET_WORDS=('shot','corner','card','offside','foul','booking','throw in','goal kick','possession','save','tackle')
def bet_score(name,side):
    low=norm(name)
    if any(x in low for x in FORBIDDEN_MARKET_WORDS): return 0
    if any(x in low for x in ('first half','second half','1st half','2nd half')): return 0
    exact={'H':{'total home','home total','home team total goals','home team goals over under','home goals over under'},'A':{'total away','away total','away team total goals','away team goals over under','away goals over under'}}[side]
    if low in exact:return 1000
    token='home' if side=='H' else 'away'
    if token not in low:return 0
    score=0
    if 'goal' in low:score+=60
    if 'total' in low:score+=50
    if 'over under' in low:score+=50
    if 'team' in low:score+=10
    if 'exact' in low or 'number of' in low:score-=100
    return score if score>=100 else 0

def discover_bets():
    rows=(s53.api_get('/odds/bets') or {}).get('response',[]); out={}; debug=[]
    for side,override in (('H',HOME_OVERRIDE),('A',AWAY_OVERRIDE)):
        if override:
            bid=int(override); match=next((str(r.get('name') or '') for r in rows if int(r.get('id') or 0)==bid),'override')
            out[side]=(bid,match); continue
        c=[]
        for r in rows:
            bid=int(r.get('id') or 0); name=str(r.get('name') or '').strip(); sc=bet_score(name,side)
            if ('home' in norm(name) or 'away' in norm(name) or 'total' in norm(name)) and len(debug)<60: debug.append((bid,name))
            if bid and sc:c.append((sc,-len(name),bid,name))
        if not c: raise RuntimeError(f"No safe {'home' if side=='H' else 'away'} GOAL team-total bet found. Catalog sample={debug}")
        c.sort(reverse=True); _,_,bid,name=c[0]; out[side]=(bid,name)
    for side,(bid,name) in out.items():
        low=norm(name)
        if any(x in low for x in FORBIDDEN_MARKET_WORDS): raise RuntimeError(f'Unsafe Stage71C bet discovery: {bid} {name}')
    if out['H'][0]==out['A'][0]: raise RuntimeError('Home/Away team totals resolved to same bet id')
    return out

def parse_value(v):
    text=f"{v.get('value') or ''} {v.get('handicap') or ''}".lower().replace(',','.')
    side='O' if 'over' in text else ('U' if 'under' in text else '')
    if not side:return None
    xs=re.findall(r'(?<!\d)(\d+(?:\.\d+)?)(?!\d)',text)
    if not xs:return None
    line=num(xs[-1])
    if line is None or not 0<=line<=10:return None
    return side,line

def market_prices(resp,wanted_ids):
    out={}; wanted=set(wanted_ids)
    for item in (resp or {}).get('response',[]):
        upd=item.get('update') or ''
        for bm in item.get('bookmakers',[]) or []:
            bname=bm.get('name') or ''; bk=norm(bname)
            for bet in bm.get('bets',[]) or []:
                bid=int(bet.get('id') or 0)
                if bid not in wanted:continue
                z=out.setdefault((bk,bid),{'update':'','lines':{}}); z['update']=max(z['update'],upd)
                for v in bet.get('values',[]) or []:
                    p=parse_value(v); odd=num(v.get('odd'))
                    if not p or odd is None or odd<=1:continue
                    s,line=p; pair=z['lines'].setdefault(line,{'O':None,'U':None})
                    if pair[s] is None or odd>pair[s]:pair[s]=odd
    return out

def complete(prices,book,bid):
    z=prices.get((norm(book),int(bid)))
    if not z:return {},''
    return {line:p for line,p in z['lines'].items() if num(p.get('O')) is not None and num(p.get('U')) is not None},z.get('update') or ''

def upcoming():
    out=[]
    for lname,lid in LEAGUES.items():
        d=s53.api_get('/fixtures',{'league':lid,'season':SEASON,'next':NEXT_N,'timezone':'UTC'})
        for r in (d or {}).get('response',[]):
            fx=r.get('fixture',{}) or {}; teams=r.get('teams',{}) or {}; ko=dt(fx.get('date'))
            if ko:out.append({'id':str(fx.get('id') or ''),'league':lname,'league_id':lid,'kickoff':ko,'home':((teams.get('home') or {}).get('name') or ''),'away':((teams.get('away') or {}).get('name') or '')})
    return out
def mkey(fid,side,line):return f'TT|{fid}|{side}|{line:g}'

def main():
    t=now(); OPS.mkdir(parents=True,exist_ok=True); bets=discover_bets(); wanted=[bets['H'][0],bets['A'][0]]
    openers, snaps, closes=read(OPENERS),read(SNAPS),read(CLOSES); open_by={r.get('market_key',''):r for r in openers}; close_by={r.get('market_key',''):r for r in closes}
    fixtures=upcoming(); add_o=add_s=add_c=calls=0; warnings=[]
    for fx in fixtures:
        h=(fx['kickoff']-t).total_seconds()/3600
        if h<=0 or h>OPEN_H:continue
        fid=fx['id']; has_open=any(str(r.get('api_fixture_id'))==fid for r in openers)
        if has_open and h>TRACK_H:continue
        try:prices=market_prices(s53.api_get('/odds',{'fixture':fid}),wanted); calls+=1
        except Exception as e:warnings.append(f'odds {fid}: {e}'); continue
        for side in ('H','A'):
            bid,bname=bets[side]; b365,ub365=complete(prices,'Bet365',bid); user,uuser=complete(prices,USER_BOOK,bid) if USER_BOOK else ({},''); team=fx['home'] if side=='H' else fx['away']
            for line,pair in sorted(b365.items()):
                key=mkey(fid,side,line); opened=open_by.get(key); pn=novig(pair['O'],pair['U'])
                if pn is None:continue
                if opened is None:
                    opened={'market_key':key,'api_fixture_id':fid,'league':fx['league'],'league_id':fx['league_id'],'captured_at_utc':iso(t),'kickoff_utc':iso(fx['kickoff']),'home_team':fx['home'],'away_team':fx['away'],'team_side':side,'team_name':team,'line':f'{line:g}','bet_id':bid,'bet_name':bname,'open_b365_over':pair['O'],'open_b365_under':pair['U'],'open_p_over':f'{pn:.8f}','open_p_under':f'{1-pn:.8f}','status':'FROZEN','source':'API-Football Bet365 first complete GOAL team-total pair captured prospectively'}
                    openers.append(opened);open_by[key]=opened;add_o+=1
                if h<=TRACK_H:
                    po=num(opened.get('open_p_over')); move=pn-po if po is not None else None; up=user.get(line,{})
                    snaps.append({'market_key':key,'api_fixture_id':fid,'league':fx['league'],'league_id':fx['league_id'],'captured_at_utc':iso(t),'kickoff_utc':iso(fx['kickoff']),'minutes_to_kickoff':f'{h*60:.1f}','home_team':fx['home'],'away_team':fx['away'],'team_side':side,'team_name':team,'line':f'{line:g}','bet_id':bid,'bet_name':bname,'b365_over':pair['O'],'b365_under':pair['U'],'p_over':f'{pn:.8f}','p_under':f'{1-pn:.8f}','open_p_over':opened.get('open_p_over',''),'over_move_pp':'' if move is None else f'{move:.8f}','user_bookmaker':USER_BOOK,'user_over':up.get('O',''),'user_under':up.get('U',''),'api_odds_update_utc':max(ub365,uuser)});add_s+=1
    latest={}
    for r in snaps:
        key=r.get('market_key',''); st=dt(r.get('captured_at_utc')); ko=dt(r.get('kickoff_utc'))
        if not key or not st or not ko or st>ko:continue
        old=latest.get(key); oldt=dt(old.get('captured_at_utc')) if old else None
        if old is None or oldt is None or st>oldt:latest[key]=r
    for key,o in list(open_by.items()):
        if key in close_by:continue
        ko=dt(o.get('kickoff_utc'))
        if not ko or t<ko:continue
        s=latest.get(key)
        if not s:continue
        ct=dt(s.get('captured_at_utc')); po=num(o.get('open_p_over')); pc=num(s.get('p_over')); mv=pc-po if po is not None and pc is not None else None
        row={'market_key':key,'api_fixture_id':o.get('api_fixture_id',''),'league':o.get('league',''),'league_id':o.get('league_id',''),'locked_at_utc':iso(t),'kickoff_utc':o.get('kickoff_utc',''),'close_observed_at_utc':s.get('captured_at_utc',''),'close_gap_minutes':'' if not ct else f'{(ko-ct).total_seconds()/60:.1f}','home_team':o.get('home_team',''),'away_team':o.get('away_team',''),'team_side':o.get('team_side',''),'team_name':o.get('team_name',''),'line':o.get('line',''),'bet_id':o.get('bet_id',''),'bet_name':o.get('bet_name',''),'open_p_over':o.get('open_p_over',''),'close_p_over':s.get('p_over',''),'movement_pp':'' if mv is None else f'{mv:.8f}','bet365_close_over':s.get('b365_over',''),'bet365_close_under':s.get('b365_under',''),'user_bookmaker':USER_BOOK,'user_close_over':s.get('user_over',''),'user_close_under':s.get('user_under',''),'status':'OBSERVED_CLOSE_FROZEN','note':'Exact same team-side and line; latest stored pre-kickoff price'}
        closes.append(row);close_by[key]=row;add_c+=1
    write(OPENERS,OPEN_FIELDS,openers);write(SNAPS,SNAP_FIELDS,snaps);write(CLOSES,CLOSE_FIELDS,closes)
    meta={'run_at_utc':iso(t),'status':'OK','mode':'PROSPECTIVE_CAPTURE_ONLY','leagues':len(LEAGUES),'fixtures_scanned':len(fixtures),'home_team_total_bet_id':bets['H'][0],'home_team_total_bet_name':bets['H'][1],'away_team_total_bet_id':bets['A'][0],'away_team_total_bet_name':bets['A'][1],'odds_calls':calls,'new_openers':add_o,'new_snapshots':add_s,'new_closes':add_c,'total_openers':len(openers),'total_snapshots':len(snaps),'total_closes':len(closes),'signals_created':0,'warnings':warnings[:50]}
    META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
