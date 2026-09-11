#!/usr/bin/env python3
"""Stage 73 — internal PBK HTTP API over the Stage72 SQLite projection.

No external dependencies. The API is read-only and never creates betting
signals, mutates ledgers, or changes strategy eligibility.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DB=Path(os.getenv('PBK_DB_PATH','build/pbk_unified.sqlite'))
OPS=Path(os.getenv('OPS_DIR','ops'))
STRATEGY_FILTER=Path('config/pbk_strategy_filter.json')
META=OPS/'stage73_last_run.json'
API_VERSION='v1'
MAX_LIMIT=500

SELECTION_RU={
    'Home':'П1','home':'П1','1':'П1','Away':'П2','away':'П2','2':'П2','Draw':'Х','draw':'Х','X':'Х','x':'Х',
    'Over 2.5':'ТБ(2.5)','Under 2.5':'ТМ(2.5)','Yes':'ОЗ — Да','No':'ОЗ — Нет',
}

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def connect():
    if not DB.exists():
        raise FileNotFoundError(f'Stage72 DB missing: {DB}')
    c=sqlite3.connect(f'file:{DB}?mode=ro',uri=True)
    c.row_factory=sqlite3.Row
    return c

def columns(conn,table):
    return [r['name'] for r in conn.execute(f'PRAGMA table_info("{table}")')]

def table_exists(conn,table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone() is not None

def qfirst(q,name,default=None):
    vals=q.get(name)
    return vals[0] if vals else default

def as_int(v,default,lo=0,hi=MAX_LIMIT):
    try:return max(lo,min(hi,int(v)))
    except:return default

def enrich(row):
    d=dict(row)
    sel=d.get('selection')
    if sel is not None:d['selection_ru']=SELECTION_RU.get(str(sel),sel)
    return d

def query_table(conn,table,q,filter_map=None,odds_candidates=None,default_order=None):
    if not table_exists(conn,table):return {'items':[],'count':0,'limit':0,'offset':0}
    cols=set(columns(conn,table)); where=[];args=[]
    filter_map=filter_map or {}
    for param,col in filter_map.items():
        val=qfirst(q,param)
        if val not in (None,'') and col in cols:
            where.append(f'LOWER("{col}") = LOWER(?)');args.append(val)
    # Optional user-view odds range. It filters output only and never eligibility.
    odds_col=next((c for c in (odds_candidates or []) if c in cols),None)
    if odds_col:
        mn=qfirst(q,'min_odds');mx=qfirst(q,'max_odds')
        try:
            if mn not in (None,''):where.append(f'CAST("{odds_col}" AS REAL) >= ?');args.append(float(mn))
        except:pass
        try:
            if mx not in (None,''):where.append(f'CAST("{odds_col}" AS REAL) <= ?');args.append(float(mx))
        except:pass
    limit=as_int(qfirst(q,'limit'),100,1,MAX_LIMIT);offset=as_int(qfirst(q,'offset'),0,0,10_000_000)
    w=(' WHERE '+' AND '.join(where)) if where else ''
    count=conn.execute(f'SELECT COUNT(*) AS n FROM "{table}"'+w,args).fetchone()['n']
    order=''
    if default_order:
        valid=[c for c in default_order if c in cols]
        if valid:order=' ORDER BY '+', '.join(f'"{c}" ASC' for c in valid)
    rows=conn.execute(f'SELECT * FROM "{table}"'+w+order+' LIMIT ? OFFSET ?',args+[limit,offset]).fetchall()
    return {'items':[enrich(r) for r in rows],'count':count,'limit':limit,'offset':offset}

def state_doc(conn,name):
    if not table_exists(conn,'state_documents'):return None
    r=conn.execute('SELECT payload_json FROM state_documents WHERE name=?',(name,)).fetchone()
    if not r:return None
    try:return json.loads(r['payload_json'])
    except:return None

def dispatch(path_with_query):
    u=urlparse(path_with_query);path=u.path.rstrip('/') or '/';q=parse_qs(u.query,keep_blank_values=True)
    with connect() as conn:
        if path=='/':
            return 200,{'service':'PBK Internal API','api_version':API_VERSION,'read_only':True,'docs':'/v1/meta'}
        if path=='/health' or path=='/v1/health':
            meta=dict(conn.execute('SELECT key,value FROM pbk_meta').fetchall()) if table_exists(conn,'pbk_meta') else {}
            sys_health=state_doc(conn,'system_health.json') or {}
            return 200,{'status':'OK' if str(sys_health.get('status','HEALTHY')).upper()!='CRITICAL' else 'CRITICAL',
                        'api_version':API_VERSION,'db_schema_version':meta.get('schema_version'),
                        'db_built_at_utc':meta.get('built_at_utc'),'system_health':sys_health.get('status','UNKNOWN'),'read_only':True}
        if path=='/v1/meta':
            meta=dict(conn.execute('SELECT key,value FROM pbk_meta').fetchall()) if table_exists(conn,'pbk_meta') else {}
            return 200,{'api_version':API_VERSION,'db':meta,'global_odds_cap':None,'eligibility_mutation':False}
        if path=='/v1/competitions':
            return 200,query_table(conn,'competitions',q,{'country':'country','league':'league','group':'group'},default_order=['country','league'])
        if path=='/v1/signals/canonical':
            return 200,query_table(conn,'canonical_signals',q,{'strategy':'rule','status':'status','team':'away_team'},
                                   ['paper_user_execution_odds','market_execution_odds','trigger_selected_odds'],['kickoff_utc','forward_id'])
        if path=='/v1/signals/challengers':
            return 200,query_table(conn,'challenger_signals',q,{'strategy':'family','league':'league','status':'status','country':'country'},
                                   ['user_odds','trigger_b365_away'],['kickoff_utc','research_id'])
        if path=='/v1/signals/watch':
            return 200,query_table(conn,'watch_signals',q,{'strategy':'watch_family','league':'league','status':'status'},
                                   ['user_cross_odds','user_odds','paper_user_execution_odds'],['kickoff_utc','watch_id'])
        if path=='/v1/lifecycle':
            return 200,query_table(conn,'lifecycle_events',q,{'signal_id':'signal_id','fixture_id':'api_fixture_id','strategy':'rule'},
                                   [],['event_at_utc','signal_id'])
        if path=='/v1/exposure':
            return 200,query_table(conn,'exposure_positions',q,{'fixture_id':'api_fixture_id','status':'status','strategy':'rules'},
                                   [],['kickoff_utc','api_fixture_id'])
        if path=='/v1/context':
            return 200,query_table(conn,'context_latest',q,{'fixture_id':'api_fixture_id'},[],['kickoff_utc','api_fixture_id'])
        if path=='/v1/odds':
            return 200,query_table(conn,'odds_snapshots',q,{'fixture_id':'api_fixture_id','bookmaker':'bookmaker'},
                                   ['odds'],['captured_at_utc','api_fixture_id'])
        if path=='/v1/attention':
            return 200,(state_doc(conn,'attention_board.json') or {})
        if path=='/v1/governance':
            return 200,{
                'system_health':state_doc(conn,'system_health.json'),
                'exposure':state_doc(conn,'exposure_summary.json'),
                'watch_promotion':state_doc(conn,'watch_promotion_gate.json'),
                'league_challenger':state_doc(conn,'stage71_challenger_board.json'),
                'fonbet_coverage':state_doc(conn,'stage71b_fonbet_coverage.json'),
            }
        if path=='/v1/config/strategy-filter':
            try:return 200,json.loads(STRATEGY_FILTER.read_text(encoding='utf-8'))
            except Exception:return 200,{'global_odds_cap':None,'groups':[],'future_ui_filters':[]}
    return 404,{'error':'NOT_FOUND','path':path,'api_version':API_VERSION}

class Handler(BaseHTTPRequestHandler):
    server_version='PBKInternalAPI/1.0'
    def do_GET(self):
        try:status,payload=dispatch(self.path)
        except FileNotFoundError as e:status,payload=503,{'error':'DATA_LAYER_UNAVAILABLE','detail':str(e)}
        except Exception as e:status,payload=500,{'error':'INTERNAL_ERROR','detail':str(e)}
        raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def log_message(self,fmt,*args):
        if os.getenv('PBK_API_ACCESS_LOG','0')=='1':super().log_message(fmt,*args)

def self_test():
    tests={
        '/v1/health':lambda p:p.get('status') in {'OK','CRITICAL'},
        '/v1/competitions?limit=100':lambda p:p.get('count')==16,
        '/v1/signals/canonical':lambda p:p.get('count') is not None,
        '/v1/signals/challengers':lambda p:p.get('count') is not None,
        '/v1/signals/watch':lambda p:p.get('count') is not None,
        '/v1/lifecycle':lambda p:p.get('count') is not None,
        '/v1/attention':lambda p:isinstance(p,dict),
        '/v1/governance':lambda p:isinstance(p,dict),
        '/v1/config/strategy-filter':lambda p:p.get('global_odds_cap') is None,
    }
    results=[];ok=True
    for path,check in tests.items():
        try:status,payload=dispatch(path);passed=status==200 and bool(check(payload))
        except Exception as e:status=500;payload={'error':str(e)};passed=False
        results.append({'path':path,'http_status':status,'passed':passed,'count':payload.get('count') if isinstance(payload,dict) else None});ok=ok and passed
    payload={'run_at_utc':now_iso(),'status':'OK' if ok else 'FAIL','api_version':API_VERSION,'db_path':str(DB),'tests':results,'passed':sum(1 for r in results if r['passed']),'total':len(results),'api_calls':0}
    OPS.mkdir(parents=True,exist_ok=True);META.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    return 0 if ok else 1

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--self-test',action='store_true');ap.add_argument('--host',default=os.getenv('PBK_API_HOST','127.0.0.1'));ap.add_argument('--port',type=int,default=int(os.getenv('PBK_API_PORT','8787')));args=ap.parse_args()
    if args.self_test:raise SystemExit(self_test())
    server=ThreadingHTTPServer((args.host,args.port),Handler)
    print(f'PBK Internal API {API_VERSION} serving http://{args.host}:{args.port} from {DB}',flush=True)
    server.serve_forever()
if __name__=='__main__':main()
