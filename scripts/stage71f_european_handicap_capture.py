#!/usr/bin/env python3
"""Stage71F: prospective full-time European Handicap (3-way) capture.

Uses API-Football pre-match bet 9 `Handicap Result`, verified by a dedicated
probe. Research data only: all complete integer lines are captured; no signals.
"""
from __future__ import annotations
import csv,json,math,os,re
from datetime import datetime,timezone
from pathlib import Path
import stage53_daily_screener as s53
OPS=Path(os.getenv('OPS_DIR','ops'));OPENERS=OPS/'stage71f_eh_openers.csv';SNAPS=OPS/'stage71f_eh_snapshots.csv';CLOSES=OPS/'stage71f_eh_closes.csv';META=OPS/'stage71f_last_run.json'
SEASON=int(os.getenv('API_FOOTBALL_SEASON','2026'));USER_BOOK=os.getenv('STAGE71F_USER_BOOKMAKER','Marathonbet').strip();OPEN_H=float(os.getenv('STAGE71F_OPEN_HORIZON_H','336'));TRACK_H=float(os.getenv('STAGE71F_TRACK_HORIZON_H','72'));NEXT_N=int(os.getenv('STAGE71F_NEXT_PER_LEAGUE','10'));BET_ID=int(os.getenv('STAGE71F_EH_BET_ID','9'))
LEAGUES={'Premier League':39,'La Liga':140,'Serie A':135,'Bundesliga':78,'Ligue 1':61,'Austrian Bundesliga':218,'Belgian Pro League':144,'Danish Superliga':119,'A Lyga':362,'Virsliga':365,'Eredivisie':88,'Eliteserien':103,'Ekstraklasa':106,'Primeira Liga':94,'Super Lig':203,'Scottish Premiership':179}
OF=['market_key','api_fixture_id','league','league_id','captured_at_utc','kickoff_utc','home_team','away_team','home_handicap_line','bet_id','bet_name','open_b365_home','open_b365_draw','open_b365_away','open_p_home','open_p_draw','open_p_away','status','source']
SF=['market_key','api_fixture_id','league','league_id','captured_at_utc','kickoff_utc','minutes_to_kickoff','home_team','away_team','home_handicap_line','bet_id','bet_name','b365_home','b365_draw','b365_away','p_home','p_draw','p_away','open_p_home','open_p_draw','open_p_away','move_home_pp','move_draw_pp','move_away_pp','user_bookmaker','user_home','user_draw','user_away','api_odds_update_utc']
CF=['market_key','api_fixture_id','league','league_id','locked_at_utc','kickoff_utc','close_observed_at_utc','close_gap_minutes','home_team','away_team','home_handicap_line','bet_id','bet_name','open_p_home','open_p_draw','open_p_away','close_p_home','close_p_draw','close_p_away','move_home_pp','move_draw_pp','move_away_pp','bet365_close_home','bet365_close_draw','bet365_close_away','user_bookmaker','user_close_home','user_close_draw','user_close_away','status','note']
def now():return datetime.now(timezone.utc).replace(microsecond=0)
def iso(d):return d.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z') if d else ''
def dt(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None
def num(v):
    try:
        x=float(str(v).strip());return x if math.isfinite(x) else None
    except:return None
def norm(v):return ' '.join(re.sub(r'[^a-z0-9+.-]+',' ',str(v or '').lower()).split())
def read(p):
    if not p.exists():return []
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,fields,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def parse_value(v):
    text=norm(v.get('value'));m=re.match(r'^(home|draw|away)\s+([+-]?\d+(?:\.0+)?)$',text)
    if not m:return None
    side={'home':'H','draw':'D','away':'A'}[m.group(1)];line=num(m.group(2))
    if line is None or abs(line-round(line))>1e-9 or line==0 or abs(line)>10:return None
    return side,int(round(line))
def prices(resp):
    out={}
    for item in (resp or {}).get('response',[]):
        upd=item.get('update') or ''
        for bm in item.get('bookmakers',[]) or []:
            bname=bm.get('name') or '';z=out.setdefault(bname,{'update':'','lines':{}});z['update']=max(z['update'],upd)
            for bet in bm.get('bets',[]) or []:
                if int(bet.get('id') or 0)!=BET_ID or str(bet.get('name') or '').strip()!='Handicap Result':continue
                for v in bet.get('values',[]) or []:
                    p=parse_value(v);odd=num(v.get('odd'))
                    if not p or odd is None or odd<=1:continue
                    side,line=p;pair=z['lines'].setdefault(line,{'H':None,'D':None,'A':None})
                    if pair[side] is None or odd>pair[side]:pair[side]=odd
    return out
def complete(bookmap,book):
    z=bookmap.get(book)
    if not z:return {},''
    return {line:p for line,p in z['lines'].items() if all(num(p.get(k)) is not None for k in ('H','D','A'))},z.get('update') or ''
def probs(p):
    inv={k:1/p[k] for k in ('H','D','A')};s=sum(inv.values());return {k:inv[k]/s for k in inv}
def upcoming():
    out=[]
    for lname,lid in LEAGUES.items():
        data=s53.api_get('/fixtures',{'league':lid,'season':SEASON,'next':NEXT_N,'timezone':'UTC'})
        for r in (data or {}).get('response',[]):
            fx=r.get('fixture',{}) or {};teams=r.get('teams',{}) or {};ko=dt(fx.get('date'))
            if ko:out.append({'id':str(fx.get('id') or ''),'league':lname,'league_id':lid,'kickoff':ko,'home':((teams.get('home') or {}).get('name') or ''),'away':((teams.get('away') or {}).get('name') or '')})
    return out
def key(fid,line):return f'EH|{fid}|{line:+d}'
def main():
    t=now();OPS.mkdir(parents=True,exist_ok=True);openers,snaps,closes=read(OPENERS),read(SNAPS),read(CLOSES);ob={r.get('market_key',''):r for r in openers};cb={r.get('market_key',''):r for r in closes};fixtures=upcoming();ao=asn=ac=calls=0;warnings=[]
    for fx in fixtures:
        h=(fx['kickoff']-t).total_seconds()/3600
        if h<=0 or h>OPEN_H:continue
        fid=fx['id'];has_open=any(str(r.get('api_fixture_id'))==fid for r in openers)
        if has_open and h>TRACK_H:continue
        try:bm=prices(s53.api_get('/odds',{'fixture':fid,'bet':BET_ID}));calls+=1
        except Exception as e:warnings.append(f'odds {fid}: {e}');continue
        b365,u365=complete(bm,'Bet365');user,uuser=complete(bm,USER_BOOK) if USER_BOOK else ({},'')
        for line,pair in sorted(b365.items()):
            mk=key(fid,line);opened=ob.get(mk);p=probs(pair)
            if opened is None:
                opened={'market_key':mk,'api_fixture_id':fid,'league':fx['league'],'league_id':fx['league_id'],'captured_at_utc':iso(t),'kickoff_utc':iso(fx['kickoff']),'home_team':fx['home'],'away_team':fx['away'],'home_handicap_line':f'{line:+d}','bet_id':BET_ID,'bet_name':'Handicap Result','open_b365_home':pair['H'],'open_b365_draw':pair['D'],'open_b365_away':pair['A'],'open_p_home':f"{p['H']:.8f}",'open_p_draw':f"{p['D']:.8f}",'open_p_away':f"{p['A']:.8f}",'status':'FROZEN','source':'API-Football Bet365 first complete European Handicap 3-way triplet'};openers.append(opened);ob[mk]=opened;ao+=1
            if h<=TRACK_H:
                up=user.get(line,{})
                op={s:num(opened.get('open_p_'+{'H':'home','D':'draw','A':'away'}[s])) for s in ('H','D','A')}
                mv={s:p[s]-op[s] if op[s] is not None else None for s in ('H','D','A')}
                snaps.append({'market_key':mk,'api_fixture_id':fid,'league':fx['league'],'league_id':fx['league_id'],'captured_at_utc':iso(t),'kickoff_utc':iso(fx['kickoff']),'minutes_to_kickoff':f'{h*60:.1f}','home_team':fx['home'],'away_team':fx['away'],'home_handicap_line':f'{line:+d}','bet_id':BET_ID,'bet_name':'Handicap Result','b365_home':pair['H'],'b365_draw':pair['D'],'b365_away':pair['A'],'p_home':f"{p['H']:.8f}",'p_draw':f"{p['D']:.8f}",'p_away':f"{p['A']:.8f}",'open_p_home':opened.get('open_p_home',''),'open_p_draw':opened.get('open_p_draw',''),'open_p_away':opened.get('open_p_away',''),'move_home_pp':'' if mv['H'] is None else f"{mv['H']:.8f}",'move_draw_pp':'' if mv['D'] is None else f"{mv['D']:.8f}",'move_away_pp':'' if mv['A'] is None else f"{mv['A']:.8f}",'user_bookmaker':USER_BOOK,'user_home':up.get('H',''),'user_draw':up.get('D',''),'user_away':up.get('A',''),'api_odds_update_utc':max(u365,uuser)});asn+=1
    latest={}
    for r in snaps:
        mk=r.get('market_key','');st=dt(r.get('captured_at_utc'));ko=dt(r.get('kickoff_utc'))
        if not mk or not st or not ko or st>ko:continue
        old=latest.get(mk);oldt=dt(old.get('captured_at_utc')) if old else None
        if old is None or oldt is None or st>oldt:latest[mk]=r
    for mk,o in list(ob.items()):
        if mk in cb:continue
        ko=dt(o.get('kickoff_utc'))
        if not ko or t<ko:continue
        s=latest.get(mk)
        if not s:continue
        ct=dt(s.get('captured_at_utc'));row={'market_key':mk,'api_fixture_id':o.get('api_fixture_id',''),'league':o.get('league',''),'league_id':o.get('league_id',''),'locked_at_utc':iso(t),'kickoff_utc':o.get('kickoff_utc',''),'close_observed_at_utc':s.get('captured_at_utc',''),'close_gap_minutes':'' if not ct else f'{(ko-ct).total_seconds()/60:.1f}','home_team':o.get('home_team',''),'away_team':o.get('away_team',''),'home_handicap_line':o.get('home_handicap_line',''),'bet_id':BET_ID,'bet_name':'Handicap Result','open_p_home':o.get('open_p_home',''),'open_p_draw':o.get('open_p_draw',''),'open_p_away':o.get('open_p_away',''),'close_p_home':s.get('p_home',''),'close_p_draw':s.get('p_draw',''),'close_p_away':s.get('p_away',''),'move_home_pp':s.get('move_home_pp',''),'move_draw_pp':s.get('move_draw_pp',''),'move_away_pp':s.get('move_away_pp',''),'bet365_close_home':s.get('b365_home',''),'bet365_close_draw':s.get('b365_draw',''),'bet365_close_away':s.get('b365_away',''),'user_bookmaker':USER_BOOK,'user_close_home':s.get('user_home',''),'user_close_draw':s.get('user_draw',''),'user_close_away':s.get('user_away',''),'status':'OBSERVED_CLOSE_FROZEN','note':'Exact same European Handicap home-line; latest stored pre-kickoff triplet'};closes.append(row);cb[mk]=row;ac+=1
    write(OPENERS,OF,openers);write(SNAPS,SF,snaps);write(CLOSES,CF,closes);meta={'run_at_utc':iso(t),'status':'OK','mode':'PROSPECTIVE_CAPTURE_ONLY','leagues':len(LEAGUES),'fixtures_scanned':len(fixtures),'european_handicap_bet_id':BET_ID,'european_handicap_bet_name':'Handicap Result','odds_calls':calls,'new_openers':ao,'new_snapshots':asn,'new_closes':ac,'total_openers':len(openers),'total_snapshots':len(snaps),'total_closes':len(closes),'signals_created':0,'warnings':warnings[:50]};META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
