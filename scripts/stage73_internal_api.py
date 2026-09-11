#!/usr/bin/env python3
"""Stage 73 — read-only PBK HTTP API over the Stage72 SQLite projection."""
from __future__ import annotations
import argparse, json, os, sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DB=Path(os.getenv('PBK_DB_PATH','build/pbk_unified.sqlite'));OPS=Path(os.getenv('OPS_DIR','ops'))
STRATEGY_FILTER=Path('config/pbk_strategy_filter.json');MARKET_SCOPE=Path('config/pbk_market_scope.json');CORE_MARKETS=Path('config/pbk_core_market_registry.json');META=OPS/'stage73_last_run.json'
API_VERSION='v1';MAX_LIMIT=500
SELECTION_RU={'Home':'П1','home':'П1','1':'П1','Away':'П2','away':'П2','2':'П2','Draw':'Х','draw':'Х','X':'Х','x':'Х','Over 2.5':'ТБ(2.5)','Under 2.5':'ТМ(2.5)','Yes':'ОЗ — Да','No':'ОЗ — Нет'}

def now_iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def connect():
    if not DB.exists():raise FileNotFoundError(f'Stage72 DB missing: {DB}')
    c=sqlite3.connect(f'file:{DB}?mode=ro',uri=True);c.row_factory=sqlite3.Row;return c
def columns(conn,table):return [r['name'] for r in conn.execute(f'PRAGMA table_info("{table}")')]
def table_exists(conn,table):return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone() is not None
def qfirst(q,name,default=None):
    vals=q.get(name);return vals[0] if vals else default
def as_int(v,default,lo=0,hi=MAX_LIMIT):
    try:return max(lo,min(hi,int(v)))
    except:return default

def enrich(row):
    d=dict(row);sel=d.get('selection')
    if sel is not None:d['selection_ru']=SELECTION_RU.get(str(sel),sel)
    side=d.get('team_side');line=d.get('line')
    if side in {'H','A'} and line not in (None,'') and ('team_name' in d or 'b365_over' in d or 'open_b365_over' in d):
        n='1' if side=='H' else '2';d['over_selection_ru']=f'ИТБ{n}({line})';d['under_selection_ru']=f'ИТМ{n}({line})'
    eh=d.get('home_handicap_line')
    if eh not in (None,''):
        d['home_selection_ru']=f'Ф1({eh})';d['draw_selection_ru']=f'Х с форой хозяев {eh}'
        try:d['away_selection_ru']=f'Ф2({-float(eh):+g})'
        except:d['away_selection_ru']='Ф2 (противоположная европейская фора)'
    if any(k in d for k in ('b365_f1_0','open_b365_f1_0','bet365_close_f1_0')):
        d['f1_selection_ru']='Ф1(0)';d['f2_selection_ru']='Ф2(0)'
    return d

def query_table(conn,table,q,filter_map=None,odds_candidates=None,default_order=None):
    if not table_exists(conn,table):return {'items':[],'count':0,'limit':0,'offset':0}
    cols=set(columns(conn,table));where=[];args=[]
    for param,col in (filter_map or {}).items():
        val=qfirst(q,param)
        if val not in (None,'') and col in cols:where.append(f'LOWER("{col}") = LOWER(?)');args.append(val)
    odds_col=next((c for c in (odds_candidates or []) if c in cols),None)
    if odds_col:
        mn=qfirst(q,'min_odds');mx=qfirst(q,'max_odds')
        try:
            if mn not in (None,''):where.append(f'CAST("{odds_col}" AS REAL) >= ?');args.append(float(mn))
        except:pass
        try:
            if mx not in (None,''):where.append(f'CAST("{odds_col}" AS REAL) <= ?');args.append(float(mx))
        except:pass
    limit=as_int(qfirst(q,'limit'),100,1,MAX_LIMIT);offset=as_int(qfirst(q,'offset'),0,0,10_000_000);w=(' WHERE '+' AND '.join(where)) if where else ''
    count=conn.execute(f'SELECT COUNT(*) AS n FROM "{table}"'+w,args).fetchone()['n'];order=''
    if default_order:
        valid=[c for c in default_order if c in cols]
        if valid:order=' ORDER BY '+', '.join(f'"{c}" ASC' for c in valid)
    rows=conn.execute(f'SELECT * FROM "{table}"'+w+order+' LIMIT ? OFFSET ?',args+[limit,offset]).fetchall();return {'items':[enrich(r) for r in rows],'count':count,'limit':limit,'offset':offset}

def state_doc(conn,name):
    if not table_exists(conn,'state_documents'):return None
    r=conn.execute('SELECT payload_json FROM state_documents WHERE name=?',(name,)).fetchone()
    if not r:return None
    try:return json.loads(r['payload_json'])
    except:return None
def config_doc(path,fallback):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return fallback

def dispatch(path_with_query):
    u=urlparse(path_with_query);path=u.path.rstrip('/') or '/';q=parse_qs(u.query,keep_blank_values=True)
    with connect() as conn:
        if path=='/':return 200,{'service':'PBK Internal API','api_version':API_VERSION,'read_only':True,'docs':'/v1/meta'}
        if path in {'/health','/v1/health'}:
            meta=dict(conn.execute('SELECT key,value FROM pbk_meta').fetchall()) if table_exists(conn,'pbk_meta') else {};sh=state_doc(conn,'system_health.json') or {};return 200,{'status':'OK' if str(sh.get('status','HEALTHY')).upper()!='CRITICAL' else 'CRITICAL','api_version':API_VERSION,'db_schema_version':meta.get('schema_version'),'db_built_at_utc':meta.get('built_at_utc'),'system_health':sh.get('status','UNKNOWN'),'read_only':True}
        if path=='/v1/meta':
            meta=dict(conn.execute('SELECT key,value FROM pbk_meta').fetchall()) if table_exists(conn,'pbk_meta') else {};return 200,{'api_version':API_VERSION,'db':meta,'global_odds_cap':None,'eligibility_mutation':False}
        if path=='/v1/competitions':return 200,query_table(conn,'competitions',q,{'country':'country','league':'league','group':'group'},default_order=['country','league'])
        if path=='/v1/signals/canonical':return 200,query_table(conn,'canonical_signals',q,{'strategy':'rule','status':'status','team':'away_team'},['paper_user_execution_odds','market_execution_odds','trigger_selected_odds'],['kickoff_utc','forward_id'])
        if path=='/v1/signals/challengers':return 200,query_table(conn,'challenger_signals',q,{'strategy':'family','league':'league','status':'status','country':'country'},['user_odds','trigger_b365_away'],['kickoff_utc','research_id'])
        if path=='/v1/signals/watch':return 200,query_table(conn,'watch_signals',q,{'strategy':'watch_family','league':'league','status':'status'},['user_cross_odds','user_odds','paper_user_execution_odds'],['kickoff_utc','watch_id'])
        if path=='/v1/markets/team-totals/openers':return 200,query_table(conn,'team_total_openers',q,{'fixture_id':'api_fixture_id','league':'league','team_side':'team_side','team':'team_name','line':'line'},['open_b365_over','open_b365_under'],['kickoff_utc','api_fixture_id','team_side','line'])
        if path=='/v1/markets/team-totals/snapshots':return 200,query_table(conn,'team_total_snapshots',q,{'fixture_id':'api_fixture_id','league':'league','team_side':'team_side','team':'team_name','line':'line'},['user_over','b365_over'],['kickoff_utc','api_fixture_id','team_side','line','captured_at_utc'])
        if path=='/v1/markets/team-totals/closes':return 200,query_table(conn,'team_total_closes',q,{'fixture_id':'api_fixture_id','league':'league','team_side':'team_side','team':'team_name','line':'line'},['user_close_over','bet365_close_over'],['kickoff_utc','api_fixture_id','team_side','line'])
        if path=='/v1/markets/double-chance/openers':return 200,query_table(conn,'double_chance_openers',q,{'fixture_id':'api_fixture_id','league':'league'},['open_b365_1x','open_b365_x2','open_b365_12'],['kickoff_utc','api_fixture_id'])
        if path=='/v1/markets/double-chance/snapshots':return 200,query_table(conn,'double_chance_snapshots',q,{'fixture_id':'api_fixture_id','league':'league'},['user_1x','user_x2','user_12','b365_1x'],['kickoff_utc','api_fixture_id','captured_at_utc'])
        if path=='/v1/markets/double-chance/closes':return 200,query_table(conn,'double_chance_closes',q,{'fixture_id':'api_fixture_id','league':'league'},['user_close_1x','user_close_x2','user_close_12','bet365_close_1x'],['kickoff_utc','api_fixture_id'])
        if path=='/v1/markets/european-handicap/openers':return 200,query_table(conn,'european_handicap_openers',q,{'fixture_id':'api_fixture_id','league':'league','line':'home_handicap_line'},['open_b365_home','open_b365_draw','open_b365_away'],['kickoff_utc','api_fixture_id','home_handicap_line'])
        if path=='/v1/markets/european-handicap/snapshots':return 200,query_table(conn,'european_handicap_snapshots',q,{'fixture_id':'api_fixture_id','league':'league','line':'home_handicap_line'},['user_home','user_draw','user_away','b365_home'],['kickoff_utc','api_fixture_id','home_handicap_line','captured_at_utc'])
        if path=='/v1/markets/european-handicap/closes':return 200,query_table(conn,'european_handicap_closes',q,{'fixture_id':'api_fixture_id','league':'league','line':'home_handicap_line'},['user_close_home','user_close_draw','user_close_away','bet365_close_home'],['kickoff_utc','api_fixture_id','home_handicap_line'])
        if path=='/v1/markets/dnb/openers':return 200,query_table(conn,'dnb_openers',q,{'fixture_id':'api_fixture_id','league':'league'},['open_b365_f1_0','open_b365_f2_0'],['kickoff_utc','api_fixture_id'])
        if path=='/v1/markets/dnb/snapshots':return 200,query_table(conn,'dnb_snapshots',q,{'fixture_id':'api_fixture_id','league':'league'},['user_f1_0','user_f2_0','b365_f1_0'],['kickoff_utc','api_fixture_id','captured_at_utc'])
        if path=='/v1/markets/dnb/closes':return 200,query_table(conn,'dnb_closes',q,{'fixture_id':'api_fixture_id','league':'league'},['user_close_f1_0','user_close_f2_0','bet365_close_f1_0'],['kickoff_utc','api_fixture_id'])
        if path=='/v1/lifecycle':return 200,query_table(conn,'lifecycle_events',q,{'signal_id':'signal_id','fixture_id':'api_fixture_id','strategy':'rule'},[],['event_at_utc','signal_id'])
        if path=='/v1/exposure':return 200,query_table(conn,'exposure_positions',q,{'fixture_id':'api_fixture_id','status':'status','strategy':'rules'},[],['kickoff_utc','api_fixture_id'])
        if path=='/v1/context':return 200,query_table(conn,'context_latest',q,{'fixture_id':'api_fixture_id'},[],['kickoff_utc','api_fixture_id'])
        if path=='/v1/odds':return 200,query_table(conn,'odds_snapshots',q,{'fixture_id':'api_fixture_id','bookmaker':'bookmaker'},['odds'],['captured_at_utc','api_fixture_id'])
        if path=='/v1/attention':return 200,(state_doc(conn,'attention_board.json') or {})
        if path=='/v1/governance':return 200,{'system_health':state_doc(conn,'system_health.json'),'exposure':state_doc(conn,'exposure_summary.json'),'watch_promotion':state_doc(conn,'watch_promotion_gate.json'),'league_challenger':state_doc(conn,'stage71_challenger_board.json'),'fonbet_coverage':state_doc(conn,'stage71b_fonbet_coverage.json'),'team_total_capture':state_doc(conn,'stage71c_last_run.json'),'double_chance_capture':state_doc(conn,'stage71e_last_run.json'),'european_handicap_capture':state_doc(conn,'stage71f_last_run.json'),'dnb_capture':state_doc(conn,'stage71g_last_run.json')}
        if path=='/v1/config/strategy-filter':return 200,config_doc(STRATEGY_FILTER,{'global_odds_cap':None,'groups':[],'future_ui_filters':[]})
        if path=='/v1/config/market-scope':return 200,config_doc(MARKET_SCOPE,{'status':'UNAVAILABLE','allowed_market_families':[],'deferred_market_universe':[]})
        if path=='/v1/config/core-market-registry':return 200,config_doc(CORE_MARKETS,{'scope':'UNAVAILABLE','markets':[]})
    return 404,{'error':'NOT_FOUND','path':path,'api_version':API_VERSION}

class Handler(BaseHTTPRequestHandler):
    server_version='PBKInternalAPI/1.4'
    def do_GET(self):
        try:status,payload=dispatch(self.path)
        except FileNotFoundError as e:status,payload=503,{'error':'DATA_LAYER_UNAVAILABLE','detail':str(e)}
        except Exception as e:status,payload=500,{'error':'INTERNAL_ERROR','detail':str(e)}
        raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8');self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def log_message(self,fmt,*args):
        if os.getenv('PBK_API_ACCESS_LOG','0')=='1':super().log_message(fmt,*args)

def self_test():
    tests={
        '/v1/health':lambda p:p.get('status') in {'OK','CRITICAL'},
        '/v1/competitions?limit=100':lambda p:p.get('count')==16,
        '/v1/signals/canonical':lambda p:p.get('count') is not None,
        '/v1/signals/challengers':lambda p:p.get('count') is not None,
        '/v1/signals/watch':lambda p:p.get('count') is not None,
        '/v1/markets/team-totals/openers?limit=1':lambda p:(p.get('count') or 0)>0,
        '/v1/markets/double-chance/openers?limit=1':lambda p:(p.get('count') or 0)>0,
        '/v1/markets/european-handicap/openers?limit=1':lambda p:(p.get('count') or 0)>0,
        '/v1/markets/dnb/openers?limit=1':lambda p:(p.get('count') or 0)>0,
        '/v1/lifecycle':lambda p:p.get('count') is not None,
        '/v1/attention':lambda p:isinstance(p,dict),
        '/v1/governance':lambda p:isinstance(p,dict),
        '/v1/config/strategy-filter':lambda p:p.get('global_odds_cap') is None,
        '/v1/config/market-scope':lambda p:len(p.get('allowed_market_families') or [])==8 and len(p.get('deferred_market_universe') or [])>=1 and str(p.get('status','')).startswith('LOCKED_CORE'),
        '/v1/config/core-market-registry':lambda p:p.get('scope')=='PBK_CORE_8' and len(p.get('markets') or [])==8,
    }
    results=[];ok=True
    for path,check in tests.items():
        try:status,payload=dispatch(path);passed=status==200 and bool(check(payload))
        except Exception as e:status=500;payload={'error':str(e)};passed=False
        results.append({'path':path,'http_status':status,'passed':passed,'count':payload.get('count') if isinstance(payload,dict) else None});ok=ok and passed
    payload={'run_at_utc':now_iso(),'status':'OK' if ok else 'FAIL','api_version':API_VERSION,'db_path':str(DB),'tests':results,'passed':sum(1 for r in results if r['passed']),'total':len(results),'api_calls':0};OPS.mkdir(parents=True,exist_ok=True);META.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(payload,ensure_ascii=False,indent=2));return 0 if ok else 1

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--self-test',action='store_true');ap.add_argument('--host',default=os.getenv('PBK_API_HOST','127.0.0.1'));ap.add_argument('--port',type=int,default=int(os.getenv('PBK_API_PORT','8787')));a=ap.parse_args()
    if a.self_test:raise SystemExit(self_test())
    server=ThreadingHTTPServer((a.host,a.port),Handler);print(f'PBK Internal API {API_VERSION} serving http://{a.host}:{a.port} from {DB}',flush=True);server.serve_forever()
if __name__=='__main__':main()
