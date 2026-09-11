#!/usr/bin/env python3
"""Append compact per-fixture market cards to Stage66.

Presentation only. Reads prospective market snapshots already collected by PBK.
No API calls, no signal creation and no eligibility changes.
"""
from __future__ import annotations
import csv, json, math, os
from datetime import datetime, timezone
from pathlib import Path

OPS=Path(os.getenv('OPS_DIR','ops'))
BOARD_JSON=OPS/'attention_board.json';BOARD_MD=OPS/'attention_board.md'
TT=OPS/'stage71c_team_total_snapshots.csv';DC=OPS/'stage71e_double_chance_snapshots.csv';EH=OPS/'stage71f_eh_snapshots.csv';DNB=OPS/'stage71g_dnb_snapshots.csv'

def read_csv(p):
    if not p.exists():return []
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dt(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None
def num(v):
    try:
        x=float(str(v).strip());return x if math.isfinite(x) else None
    except:return None
def odd(v):
    x=num(v);return '' if x is None else f'{x:g}'
def newest(rows,key='captured_at_utc'):
    return max(rows,key=lambda r:(r.get(key) or '')) if rows else None

def fixture_universe(board):
    out={}
    for section in ('red','orange','canonical','watch','nearest_monitored'):
        for r in board.get(section,[]) or []:
            fid=str(r.get('fixture_id') or '')
            if not fid:continue
            cur=out.get(fid,{})
            cur.update({k:r.get(k) or cur.get(k) for k in ('fixture_id','home_team','away_team','kickoff_utc','kickoff_local','league')})
            out[fid]=cur
    vals=list(out.values())
    vals.sort(key=lambda x:x.get('kickoff_utc') or '')
    return vals[:8]

def main():
    if not BOARD_JSON.exists():return
    board=json.loads(BOARD_JSON.read_text(encoding='utf-8-sig'))
    tt,dc,eh,dnb=read_csv(TT),read_csv(DC),read_csv(EH),read_csv(DNB)
    cards=[]
    for fx in fixture_universe(board):
        fid=str(fx.get('fixture_id') or '')
        markets=[]
        # Individual totals: show the familiar 1.5 line for each team when available.
        for side,label in (('H','ИТБ1/ИТМ1'),('A','ИТБ2/ИТМ2')):
            rows=[r for r in tt if str(r.get('api_fixture_id'))==fid and str(r.get('team_side'))==side and str(r.get('line')) in {'1.5','1.50'}]
            r=newest(rows)
            if r:
                ov=odd(r.get('user_over'));un=odd(r.get('user_under'))
                if ov or un:markets.append({'market':'TEAM_TOTAL_1_5','side':side,'text':f"{label}(1.5): {'ИТБ '+ov if ov else 'ИТБ —'} / {'ИТМ '+un if un else 'ИТМ —'} @ Marathonbet"})
        r=newest([x for x in dc if str(x.get('api_fixture_id'))==fid])
        if r:
            vals=(odd(r.get('user_1x')),odd(r.get('user_x2')),odd(r.get('user_12')))
            if any(vals):markets.append({'market':'DOUBLE_CHANCE','text':f'1Х {vals[0] or "—"} | Х2 {vals[1] or "—"} | 12 {vals[2] or "—"} @ Marathonbet'})
        r=newest([x for x in dnb if str(x.get('api_fixture_id'))==fid])
        if r:
            a,b=odd(r.get('user_f1_0')),odd(r.get('user_f2_0'))
            if a or b:markets.append({'market':'DNB','text':f'Ф1(0) {a or "—"} | Ф2(0) {b or "—"} @ Marathonbet'})
        # European 3-way handicap: one compact +1-to-home reference line.
        rows=[x for x in eh if str(x.get('api_fixture_id'))==fid and str(x.get('home_handicap_line')) in {'+1','1','+1.0','1.0'}]
        r=newest(rows)
        if r:
            a,b,c=odd(r.get('user_home')),odd(r.get('user_draw')),odd(r.get('user_away'))
            if a or b or c:markets.append({'market':'EUROPEAN_HANDICAP_HOME_PLUS_1','text':f'Европ. фора: хозяева +1 → 1:{a or "—"} / Х:{b or "—"} / 2:{c or "—"} @ Marathonbet'})
        if markets:
            cards.append({**fx,'markets':markets,'status':'MARKET_VIEW_ONLY','creates_signal':False})
    board['market_cards']=cards
    board.setdefault('summary',{})['market_cards']=len(cards)
    BOARD_JSON.write_text(json.dumps(board,ensure_ascii=False,indent=2),encoding='utf-8')
    md=BOARD_MD.read_text(encoding='utf-8-sig') if BOARD_MD.exists() else ''
    md += '\n## 🧩 Рыночные карточки ближайших матчей\n'
    md += '> Только обзор доступных рынков. Эти строки **не являются сигналами или рекомендациями**.\n'
    if not cards:md+='- Пока нет доступных рыночных карточек.\n'
    for c in cards:
        md+=f"\n- **{c.get('home_team','')} — {c.get('away_team','')}** | {c.get('kickoff_local') or c.get('kickoff_utc','')}\n"
        for m in c['markets']:md+=f"  - {m['text']}\n"
    BOARD_MD.write_text(md,encoding='utf-8')
    print(json.dumps({'market_cards':len(cards),'api_calls':0,'creates_signals':False},ensure_ascii=False))
if __name__=='__main__':main()
