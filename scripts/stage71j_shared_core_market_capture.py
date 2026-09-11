#!/usr/bin/env python3
"""Stage71J — shared cached capture for prospective core markets.

Runs Stage71C/E/F/G in one Python process and memoizes API-Football GETs.
Before child parsers run, Stage71J prefetches the common 16-league fixture set
and one /odds payload per fixture. The same payload then feeds team totals,
double chance, European handicap and DNB parsers.

Research data only. Creates no betting signal or WATCH.
"""
from __future__ import annotations
import json, os
from pathlib import Path

# Pin already verified API-Football market ids before importing child modules.
os.environ.setdefault('STAGE71C_HOME_TEAM_TOTAL_BET_ID','16')
os.environ.setdefault('STAGE71C_AWAY_TEAM_TOTAL_BET_ID','17')
os.environ.setdefault('STAGE71E_DOUBLE_CHANCE_BET_ID','12')
os.environ.setdefault('STAGE71F_EH_BET_ID','9')
os.environ.setdefault('STAGE71G_AH_BET_ID','4')

import stage53_daily_screener as s53
import stage71c_team_totals_capture as c
import stage71e_double_chance_capture as e
import stage71f_european_handicap_capture as f
import stage71g_dnb_capture as g

OPS=Path(os.getenv('OPS_DIR','ops'))
META=OPS/'stage71j_last_run.json'
MAX_REAL_CALLS=int(os.getenv('STAGE71J_MAX_REAL_API_CALLS','190'))
_real=s53.api_get
_cache={}
real_calls=0
cache_hits=0
by_path={}

def _key(path,params):
    return path, tuple(sorted((str(k),str(v)) for k,v in (params or {}).items()))

def cached_api_get(path,params=None):
    global real_calls, cache_hits
    k=_key(path,params)
    if k in _cache:
        cache_hits+=1
        return _cache[k]
    if real_calls>=MAX_REAL_CALLS:
        raise RuntimeError(f'Stage71J API hard cap reached: {real_calls}/{MAX_REAL_CALLS}')
    val=_real(path,params)
    _cache[k]=val
    real_calls+=1
    by_path[path]=by_path.get(path,0)+1
    return val

# All child modules imported the same stage53 module object.
s53.api_get=cached_api_get

def read_meta(path):
    try:return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception:return {}

def prefetch_common_universe():
    """Fetch the shared 16-league fixture universe and one odds payload per fixture."""
    fixture_ids=[]
    season=c.SEASON
    next_n=max(c.NEXT_N,e.NEXT_N,f.NEXT_N,g.NEXT_N)
    # One catalog response is shared across children that still inspect /odds/bets.
    cached_api_get('/odds/bets')
    for _lname,lid in c.LEAGUES.items():
        data=cached_api_get('/fixtures',{'league':lid,'season':season,'next':next_n,'timezone':'UTC'})
        for r in (data or {}).get('response',[]):
            fid=str(((r.get('fixture') or {}).get('id')) or '')
            if fid and fid not in fixture_ids:fixture_ids.append(fid)
    for fid in fixture_ids:
        cached_api_get('/odds',{'fixture':fid})
    return fixture_ids

def main():
    OPS.mkdir(parents=True,exist_ok=True)
    fixture_ids=prefetch_common_universe()
    children=[]
    for label,mod,meta in [
        ('TEAM_TOTAL',c,c.META),
        ('DOUBLE_CHANCE',e,e.META),
        ('EUROPEAN_HANDICAP',f,f.META),
        ('DRAW_NO_BET',g,g.META),
    ]:
        mod.main()
        m=read_meta(meta)
        children.append({
            'market_family':label,
            'status':m.get('status'),
            'fixtures_scanned':m.get('fixtures_scanned'),
            'logical_odds_calls':m.get('odds_calls'),
            'new_openers':m.get('new_openers'),
            'new_snapshots':m.get('new_snapshots'),
            'new_closes':m.get('new_closes'),
            'warnings':len(m.get('warnings') or []),
        })
    payload={
        'status':'OK',
        'mode':'SHARED_PREFETCHED_PROSPECTIVE_CAPTURE',
        'prefetched_fixture_ids':len(fixture_ids),
        'real_api_calls':real_calls,
        'api_hard_cap':MAX_REAL_CALLS,
        'cache_hits':cache_hits,
        'unique_cached_requests':len(_cache),
        'real_calls_by_path':by_path,
        'children':children,
        'signals_created':0,
        'policy':'One fixture odds response feeds multiple market parsers; market ledgers remain separate and auditable.'
    }
    META.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(payload,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
