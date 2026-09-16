#!/usr/bin/env python3
"""Stage71J — shared cached capture for prospective core markets.

Runs Stage71C/E/F/G in one Python process and memoizes API-Football GETs.
Before child parsers run, Stage71J prefetches the common 16-league fixture set
and one unfiltered /odds payload per fixture. Filtered child requests such as
/odds?fixture=...&bet=12 are intentionally served from that same fixture cache,
because each child parser performs its own market-id filtering locally.

The same already-fetched fixture and /odds payloads also feed Generic 1X2 v1
prospective Bet365 Match Winner capture with zero additional provider calls.

The already-needed /odds/bets catalog and observed market-presence counts are
persisted for offline deferred-market audits, adding zero API calls.

Research data only. Creates no betting signal or WATCH.
"""
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path

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
import market_research_inventory
import generic_1x2_probability_v1_stage71j_capture as generic_1x2
from api_football_broker import get_broker

OPS=Path(os.getenv('OPS_DIR','ops'))
META=OPS/'stage71j_last_run.json'
BET_CATALOG=OPS/'api_football_odds_bet_catalog.json'
MARKET_PRESENCE=OPS/'api_football_market_presence.json'
MAX_REAL_CALLS=int(os.getenv('STAGE71J_MAX_REAL_API_CALLS','190'))
_real=s53.api_get
_cache={}
_fixture_odds_cache={}
real_calls=0
cache_hits=0
by_path={}

def now_iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def _key(path,params):
    return path, tuple(sorted((str(k),str(v)) for k,v in (params or {}).items()))

def cached_api_get(path,params=None):
    global real_calls, cache_hits
    k=_key(path,params)
    if k in _cache:
        cache_hits+=1
        return _cache[k]
    if path=='/odds' and (params or {}).get('fixture') not in (None,''):
        fixture_key=str((params or {}).get('fixture'))
        if fixture_key in _fixture_odds_cache:
            cache_hits+=1
            return _fixture_odds_cache[fixture_key]
    broker = get_broker() if _real is s53._stage53_api_get else None
    before = broker.stats() if broker else None
    if (before and before['real_api_calls'] >= MAX_REAL_CALLS) or (not before and real_calls>=MAX_REAL_CALLS):
        raise RuntimeError(f'Stage71J API hard cap reached: {real_calls}/{MAX_REAL_CALLS}')
    fresh = path == '/fixtures' or path == '/odds'
    if broker:
        broker.max_real_calls = MAX_REAL_CALLS
    try:
        if _real is s53._stage53_api_get:
            val=_real(path,params,**({'force_refresh':True} if fresh else {}))
        else:
            val=_real(path,params)
    finally:
        after = broker.stats() if broker else None
        if before is not None:
            provider_calls = after['real_api_calls'] - before['real_api_calls']
            broker_hits = (
                after['memory_cache_hits'] + after['disk_cache_hits']
                - before['memory_cache_hits'] - before['disk_cache_hits']
            )
        else:
            provider_calls, broker_hits = 1, 0
        real_calls += provider_calls
        cache_hits += broker_hits
        if provider_calls:
            by_path[path]=by_path.get(path,0)+provider_calls
    _cache[k]=val
    if path=='/odds' and set((params or {}).keys())=={'fixture'}:
        _fixture_odds_cache[str((params or {}).get('fixture'))]=val
    return val

s53.api_get=cached_api_get

def read_meta(path):
    try:return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception:return {}

def prefetch_common_universe():
    fixture_ids=[]
    season=c.SEASON
    next_n=max(c.NEXT_N,e.NEXT_N,f.NEXT_N,g.NEXT_N)
    catalog=cached_api_get('/odds/bets') or {}
    BET_CATALOG.write_text(json.dumps({'captured_at_utc':now_iso(),'source':'API-Football /odds/bets via Stage71J shared call','api_calls_added_for_catalog':0,'response':catalog.get('response',[])},ensure_ascii=False,indent=2),encoding='utf-8')
    for _lname,lid in c.LEAGUES.items():
        data=cached_api_get('/fixtures',{'league':lid,'season':season,'next':next_n,'timezone':'UTC'})
        for r in (data or {}).get('response',[]):
            fid=str(((r.get('fixture') or {}).get('id')) or '')
            if fid and fid not in fixture_ids:fixture_ids.append(fid)
    for fid in fixture_ids:cached_api_get('/odds',{'fixture':fid})
    return fixture_ids

def persist_market_presence(fixture_ids):
    presence={}
    for k,payload in _cache.items():
        if not k or k[0]!='/odds':continue
        fid=''
        for a,b in (k[1] if len(k)>1 else ()): 
            if a=='fixture':fid=str(b)
        if not fid:continue
        for item in (payload or {}).get('response',[]) or []:
            for bm in item.get('bookmakers',[]) or []:
                bname=str(bm.get('name') or '').strip();bnorm=bname.lower()
                for bet in bm.get('bets',[]) or []:
                    try:bid=int(bet.get('id'))
                    except Exception:continue
                    row=presence.setdefault(bid,{'bet_id':bid,'bet_name':str(bet.get('name') or '').strip(),'fixtures_any':set(),'fixtures_bet365':set(),'fixtures_marathonbet':set()})
                    if not row['bet_name']:row['bet_name']=str(bet.get('name') or '').strip()
                    row['fixtures_any'].add(fid)
                    if bnorm=='bet365':row['fixtures_bet365'].add(fid)
                    if bnorm=='marathonbet':row['fixtures_marathonbet'].add(fid)
    out=[];den=max(1,len(fixture_ids))
    for bid in sorted(presence):
        r=presence[bid];out.append({'bet_id':bid,'bet_name':r['bet_name'],'fixture_sample':len(fixture_ids),'fixtures_any':len(r['fixtures_any']),'fixtures_bet365':len(r['fixtures_bet365']),'fixtures_marathonbet':len(r['fixtures_marathonbet']),'bet365_coverage_pct':round(100*len(r['fixtures_bet365'])/den,2),'marathonbet_coverage_pct':round(100*len(r['fixtures_marathonbet'])/den,2)})
    MARKET_PRESENCE.write_text(json.dumps({'generated_at_utc':now_iso(),'fixture_sample':len(fixture_ids),'api_calls_added':0,'markets':out},ensure_ascii=False,indent=2),encoding='utf-8')
    return len(out)

def main():
    started=now_iso();OPS.mkdir(parents=True,exist_ok=True)
    fixture_ids=prefetch_common_universe();presence_markets=persist_market_presence(fixture_ids)
    market_research_inventory.persist(OPS, _cache, now_iso())
    generic_capture=generic_1x2.capture_from_stage71j_cache(
        _cache, c.LEAGUES, OPS, process_time=now_iso())
    children=[]
    for label,mod,meta in [('TEAM_TOTAL',c,c.META),('DOUBLE_CHANCE',e,e.META),('EUROPEAN_HANDICAP',f,f.META),('DRAW_NO_BET',g,g.META)]:
        mod.main();m=read_meta(meta)
        children.append({'market_family':label,'status':m.get('status'),'fixtures_scanned':m.get('fixtures_scanned'),'logical_odds_calls':m.get('odds_calls'),'new_openers':m.get('new_openers'),'new_snapshots':m.get('new_snapshots'),'new_closes':m.get('new_closes'),'warnings':len(m.get('warnings') or [])})
    payload={'run_at_utc':started,'status':'OK','mode':'SHARED_PREFETCHED_PROSPECTIVE_CAPTURE','prefetched_fixture_ids':len(fixture_ids),'real_api_calls':real_calls,'api_hard_cap':MAX_REAL_CALLS,'cache_hits':cache_hits,'unique_cached_requests':len(_cache),'real_calls_by_path':by_path,'bet_catalog_saved':BET_CATALOG.exists(),'bet_catalog_api_calls_added':0,'market_presence_saved':MARKET_PRESENCE.exists(),'market_presence_count':presence_markets,'market_presence_api_calls_added':0,'generic_1x2_forward_capture':generic_capture,'children':children,'signals_created':0,'policy':'One fixture odds response feeds multiple market parsers plus Generic 1X2 forward capture; market ledgers remain separate and auditable. Generic 1X2 adds zero provider calls. Catalog and observed market presence reuse already-required calls.'}
    META.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(payload,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
