#!/usr/bin/env python3
"""Stage74 app API: Stage73-compatible API plus app aggregations and delivery settings."""
from __future__ import annotations
import argparse, json, os, shutil, tempfile, time
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import stage73_internal_api as base

STARTED_AT=time.time()
PUSH_DIR=os.getenv('PBK_PUSH_DATA_DIR','/opt/pbk/data')
PUSH_SUBS=os.path.join(PUSH_DIR,'push_subscriptions.json')
VAPID_PUBLIC=os.path.join(PUSH_DIR,'vapid_public.txt')

TABLES={
    'canonical':'canonical_signals',
    'watch':'watch_signals',
    'challengers':'challenger_signals',
    'context':'context_latest',
    'lifecycle':'lifecycle_events',
    'exposure':'exposure_positions',
    'odds':'odds_snapshots',
    'probability_predictions':'probability_predictions',
    'team_total_openers':'team_total_openers',
    'team_total_snapshots':'team_total_snapshots',
    'team_total_closes':'team_total_closes',
    'double_chance_openers':'double_chance_openers',
    'double_chance_snapshots':'double_chance_snapshots',
    'double_chance_closes':'double_chance_closes',
    'european_handicap_openers':'european_handicap_openers',
    'european_handicap_snapshots':'european_handicap_snapshots',
    'european_handicap_closes':'european_handicap_closes',
    'dnb_openers':'dnb_openers',
    'dnb_snapshots':'dnb_snapshots',
    'dnb_closes':'dnb_closes',
    'settlements':'core_market_settlements',
}

NOTIFICATION_EVENTS={
    'SIGNAL_CREATED':('SIGNAL','high'),
    'WATCH_CROSSING':('WATCH','medium'),
    'XI_ROTATION':('LINEUP','high'),
    'SETTLEMENT':('SETTLEMENT','medium'),
    'WATCH_SETTLEMENT':('SETTLEMENT','low'),
    'FIXTURE_EVENT':('FIXTURE','high'),
}

def fixture_rows(conn,table,fixture_id,limit=500):
    if not base.table_exists(conn,table): return []
    cols=set(base.columns(conn,table))
    if 'api_fixture_id' not in cols: return []
    order=''
    for candidate in ('captured_at_utc','created_at_utc','event_at_utc','event_time_utc','kickoff_utc','line','home_handicap_line'):
        if candidate in cols:
            order=f' ORDER BY "{candidate}" ASC';break
    rows=conn.execute(f'SELECT * FROM "{table}" WHERE CAST("api_fixture_id" AS TEXT)=?{order} LIMIT ?', (str(fixture_id),limit)).fetchall()
    return [base.enrich(r) for r in rows]

def match_card_from_attention(conn,fixture_id):
    att=base.state_doc(conn,'attention_board.json') or {}
    for x in att.get('market_cards') or []:
        if str(x.get('fixture_id'))==str(fixture_id): return x
    for group in ('canonical','watch','nearest_monitored','red','orange'):
        for x in att.get(group) or []:
            if str(x.get('fixture_id'))==str(fixture_id): return x
    return None

def aggregate_match(fixture_id):
    if not fixture_id: return 400,{'error':'FIXTURE_ID_REQUIRED'}
    with base.connect() as conn:
        payload={k:fixture_rows(conn,t,fixture_id) for k,t in TABLES.items()}
        card=match_card_from_attention(conn,fixture_id)
        identity={}
        if card:
            identity={k:card.get(k) for k in ('fixture_id','league','home_team','away_team','kickoff_utc','kickoff_local') if card.get(k) is not None}
        if not identity:
            for key in ('canonical','watch','challengers','context','team_total_openers','double_chance_openers','dnb_openers'):
                if payload.get(key):
                    r=payload[key][0]
                    identity={k:r.get(k) for k in ('api_fixture_id','league','home_team','away_team','kickoff_utc') if r.get(k) is not None}
                    identity['fixture_id']=identity.pop('api_fixture_id',str(fixture_id));break
        found=bool(card or any(payload.values()))
        if not found:return 404,{'error':'MATCH_NOT_FOUND','fixture_id':str(fixture_id)}
        rankings=base.state_doc(conn,'probability_rankings.json') or {}
        rank_rows=[];seen=set()
        for group in ('max_probability','best_value'):
            for row in rankings.get(group) or []:
                if str(row.get('api_fixture_id') or '')!=str(fixture_id):continue
                key=(str(row.get('rule') or ''),str(row.get('api_fixture_id') or ''),str(row.get('selection') or ''))
                if key in seen:continue
                seen.add(key);rank_rows.append(row)
        return 200,{
            'fixture_id':str(fixture_id),'identity':identity,'attention_card':card,
            'value_radar':{'items':[r for r in radar_document(conn)['items'] if str(r.get('api_fixture_id'))==str(fixture_id)],'research_only':True,'creates_signal':False},
            'canonical':payload['canonical'],'watch':payload['watch'],'challengers':payload['challengers'],
            'context':payload['context'],'lifecycle':payload['lifecycle'],'exposure':payload['exposure'],'odds':payload['odds'],
            'probability':{'predictions':payload['probability_predictions'],'active_rankings':rank_rows,'strategy_mutation':False,'stake_changes':False},
            'markets':{
                'team_totals':{'openers':payload['team_total_openers'],'snapshots':payload['team_total_snapshots'],'closes':payload['team_total_closes']},
                'double_chance':{'openers':payload['double_chance_openers'],'snapshots':payload['double_chance_snapshots'],'closes':payload['double_chance_closes']},
                'european_handicap':{'openers':payload['european_handicap_openers'],'snapshots':payload['european_handicap_snapshots'],'closes':payload['european_handicap_closes']},
                'dnb':{'openers':payload['dnb_openers'],'snapshots':payload['dnb_snapshots'],'closes':payload['dnb_closes']},
            },
            'settlements':payload['settlements'],'read_only':True,'creates_signal':False,
        }

def radar_document(conn):
    doc=base.state_doc(conn,'value_radar_current.json') or {}
    return {'status':doc.get('status','NO_DATA'),'generated_at_utc':doc.get('generated_at_utc'),
            'model_version':doc.get('model_version'),'items':doc.get('items') or [],
            'policy':doc.get('policy') or {},'read_only':True,'research_only':True,'creates_signal':False}

def value_radar_payload(limit=50):
    try:limit=max(1,min(100,int(limit)))
    except (ValueError,TypeError):limit=50
    with closing(base.connect()) as conn:
        payload=radar_document(conn)
        payload['count']=len(payload['items'])
        payload['items']=payload['items'][:limit]
        payload['limit']=limit
        return 200,payload

def performance_payload():
    with base.connect() as conn:
        canonical=base.state_doc(conn,'forward_performance.json') or {}
        watch=base.state_doc(conn,'watch_performance.json') or {}
        readiness=base.state_doc(conn,'core_market_readiness.json') or {}
        rankings=base.state_doc(conn,'probability_rankings.json') or {}
        probability_performance=base.state_doc(conn,'probability_performance.json') or {}
        probability_meta=base.state_doc(conn,'stage75_last_run.json') or {}
        research_settlement_rows=0
        if base.table_exists(conn,'core_market_settlements'):
            research_settlement_rows=conn.execute('SELECT COUNT(*) AS n FROM core_market_settlements').fetchone()['n']
        active=str(rankings.get('status') or '').upper()=='OK'
        max_probability=rankings.get('max_probability') or []
        best_value=rankings.get('best_value') or []
        return 200,{
            'scope':'prospective operational performance; historical research kept separate',
            'canonical':canonical,'watch':watch,'core_market_readiness':readiness,
            'research_market_settlement_rows':research_settlement_rows,
            'probability_module':{
                'status':'ACTIVE_FORWARD_MONITORING' if active else 'NOT_READY',
                'model_version':rankings.get('model_version') or probability_meta.get('model_version'),
                'max_probability_ranking_available':bool(max_probability),'value_ranking_available':bool(best_value),
                'max_probability':max_probability,'best_value':best_value,
                'forward_performance':probability_performance,'stage75_meta':probability_meta,
                'policy':{'canonical_only':True,'watch_excluded':True,'stake_changes':False,'predictions_frozen_prematch':True,'historical_backfill':'FORBIDDEN','paper_execution_is_not_proof_real_bet':True}
            },'read_only':True,
        }

def _read_text(path):
    try:
        with open(path,'r',encoding='utf-8') as f:return f.read().strip()
    except OSError:return ''

def _load_json(path,default):
    try:
        with open(path,'r',encoding='utf-8') as f:return json.load(f)
    except (OSError,json.JSONDecodeError):return default

def _atomic_json(path,obj):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=os.path.basename(path)+'.',dir=os.path.dirname(path))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(obj,f,ensure_ascii=False,separators=(',',':'));f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        try:os.unlink(tmp)
        except FileNotFoundError:pass

def _meminfo():
    out={}
    try:
        with open('/proc/meminfo','r',encoding='utf-8') as f:
            for line in f:
                k,v=line.split(':',1);parts=v.strip().split();out[k]=int(parts[0])*1024 if parts else 0
    except OSError:return {}
    return out

def runtime_payload():
    db_path=os.path.abspath(str(base.DB));disk_root=os.path.dirname(db_path) or '.'
    try:du=shutil.disk_usage(disk_root)
    except OSError:du=shutil.disk_usage('.')
    mem=_meminfo();total=mem.get('MemTotal',0);avail=mem.get('MemAvailable',0)
    try:load1,load5,load15=os.getloadavg()
    except OSError:load1=load5=load15=0.0
    try:
        with open('/proc/uptime','r',encoding='utf-8') as f:host_uptime=float(f.read().split()[0])
    except (OSError,ValueError,IndexError):host_uptime=None
    try:db_stat=os.stat(db_path);db_size=db_stat.st_size;db_mtime=db_stat.st_mtime
    except OSError:db_size=0;db_mtime=None
    release=_read_text('/opt/pbk/data/release_commit') or os.getenv('PBK_RELEASE_COMMIT','') or 'UNTRACKED'
    return 200,{
        'status':'OK','api_version':'1.5','release_commit':release,
        'api_process_uptime_seconds':round(max(0,time.time()-STARTED_AT),1),
        'host_uptime_seconds':round(host_uptime,1) if host_uptime is not None else None,
        'load_average_1m':round(load1,3),'load_average_5m':round(load5,3),'load_average_15m':round(load15,3),
        'memory_total_mb':round(total/1048576,1) if total else None,'memory_available_mb':round(avail/1048576,1) if avail else None,
        'disk_total_gb':round(du.total/1073741824,2),'disk_free_gb':round(du.free/1073741824,2),
        'db_size_mb':round(db_size/1048576,2),'db_mtime_epoch':db_mtime,'read_only':True,
    }

def push_status_payload():
    public_key=_read_text(VAPID_PUBLIC)
    subs=_load_json(PUSH_SUBS,[])
    if not isinstance(subs,list):subs=[]
    return 200,{
        'enabled':bool(public_key),'public_key':public_key,'subscription_count':len(subs),
        'status':'READY' if public_key else 'NOT_PROVISIONED',
        'strategy_mutation':False,'football_api_calls':0,
    }

def _valid_subscription(sub):
    if not isinstance(sub,dict):return False
    endpoint=str(sub.get('endpoint') or '')
    keys=sub.get('keys') or {}
    return endpoint.startswith('https://') and isinstance(keys,dict) and bool(keys.get('p256dh')) and bool(keys.get('auth'))

def push_subscribe(body):
    sub=(body or {}).get('subscription') if isinstance(body,dict) else None
    if not _valid_subscription(sub):return 400,{'error':'INVALID_PUSH_SUBSCRIPTION'}
    entries=_load_json(PUSH_SUBS,[])
    if not isinstance(entries,list):entries=[]
    endpoint=sub['endpoint'];now=datetime.now(timezone.utc).isoformat()
    entries=[e for e in entries if not isinstance(e,dict) or (e.get('subscription') or {}).get('endpoint')!=endpoint]
    entries.append({'subscription':sub,'created_at_utc':now})
    entries=entries[-20:]
    _atomic_json(PUSH_SUBS,entries)
    return 200,{'status':'SUBSCRIBED','subscription_count':len(entries),'strategy_mutation':False,'football_api_calls':0}

def push_unsubscribe(body):
    endpoint=str((body or {}).get('endpoint') or '') if isinstance(body,dict) else ''
    if not endpoint:return 400,{'error':'ENDPOINT_REQUIRED'}
    entries=_load_json(PUSH_SUBS,[])
    if not isinstance(entries,list):entries=[]
    kept=[e for e in entries if not isinstance(e,dict) or (e.get('subscription') or {}).get('endpoint')!=endpoint]
    _atomic_json(PUSH_SUBS,kept)
    return 200,{'status':'UNSUBSCRIBED','subscription_count':len(kept),'strategy_mutation':False,'football_api_calls':0}

def notification_title(row,category):
    teams=f"{row.get('home_team') or '—'} — {row.get('away_team') or '—'}";tag=row.get('rule_or_stage') or ''
    if category=='SIGNAL': return f"Новый {tag or 'R'}: {teams}"
    if category=='WATCH': return f"{tag or 'WATCH'} crossing: {teams}"
    if category=='LINEUP': return f"Составы / ротация: {teams}"
    if category=='SETTLEMENT': return f"Результат: {teams}"
    if category=='FIXTURE': return f"Изменение матча: {teams}"
    return teams

def notification_body(row,category):
    parts=[];selection=row.get('selection') or ''
    if selection:parts.append(selection)
    odds=row.get('odds');bookmaker=row.get('bookmaker') or ''
    if odds not in (None,''):parts.append(f"{odds}"+(f" @ {bookmaker}" if bookmaker else ''))
    status=row.get('status') or ''
    if category in {'SETTLEMENT','FIXTURE'} and status:parts.append(status)
    details=row.get('details') or ''
    if details:parts.append(details)
    return ' · '.join(str(x) for x in parts if x)

def notifications_payload(limit=100):
    limit=max(1,min(int(limit or 100),200));items=[]
    with base.connect() as conn:
        if base.table_exists(conn,'lifecycle_events'):
            cols=set(base.columns(conn,'lifecycle_events'));required={'entity_id','event_type','event_time_utc'}
            if required.issubset(cols):
                rows=conn.execute('SELECT * FROM lifecycle_events ORDER BY event_time_utc DESC LIMIT 500').fetchall()
                for raw in rows:
                    row=base.enrich(raw);event_type=str(row.get('event_type') or '');spec=NOTIFICATION_EVENTS.get(event_type);category=None;severity=None
                    if spec:category,severity=spec
                    elif event_type=='CONTEXT_SNAPSHOT' and 'lineups=YES' in str(row.get('details') or '').upper():category,severity='LINEUP','high'
                    if not category:continue
                    event_time=str(row.get('event_time_utc') or '');entity_id=str(row.get('entity_id') or '');nid='|'.join([entity_id,event_time,event_type])
                    items.append({'id':nid,'category':category,'severity':severity,'event_type':event_type,'event_time_utc':event_time,
                        'fixture_id':str(row.get('api_fixture_id') or ''),'league':row.get('league') or '','home_team':row.get('home_team') or '',
                        'away_team':row.get('away_team') or '','rule_or_stage':row.get('rule_or_stage') or '',
                        'title':notification_title(row,category),'body':notification_body(row,category)})
                    if len(items)>=limit:break
        health=base.state_doc(conn,'system_health.json') or {};hstatus=str(health.get('status') or '').upper();issues=health.get('issues') or []
        if hstatus and hstatus not in {'HEALTHY','OK'}:
            if issues:
                for idx,issue in enumerate(issues[:20]):
                    if isinstance(issue,dict):sev=str(issue.get('severity') or issue.get('status') or 'WARN').upper();body=str(issue.get('message') or issue.get('issue') or issue.get('details') or issue);stage=str(issue.get('stage') or '')
                    else:sev='WARN';body=str(issue);stage=''
                    items.append({'id':f"SYSTEM|{health.get('generated_at_utc') or ''}|{idx}|{body}",'category':'SYSTEM','severity':'high' if sev in {'CRITICAL','ERROR','FAIL'} else 'medium','event_type':'SYSTEM_HEALTH','event_time_utc':health.get('generated_at_utc') or '','fixture_id':'','league':'','home_team':'','away_team':'','rule_or_stage':stage,'title':f"Системное предупреждение{': '+stage if stage else ''}",'body':body})
            else:
                items.append({'id':f"SYSTEM|{health.get('generated_at_utc') or ''}|{hstatus}",'category':'SYSTEM','severity':'high','event_type':'SYSTEM_HEALTH','event_time_utc':health.get('generated_at_utc') or '','fixture_id':'','league':'','home_team':'','away_team':'','rule_or_stage':'','title':f"Состояние системы: {hstatus}",'body':'Проверь раздел Health перед использованием сигналов.'})
    items.sort(key=lambda x:x.get('event_time_utc') or '',reverse=True);items=items[:limit]
    summary={k:sum(1 for x in items if x['category']==k) for k in ('SIGNAL','WATCH','LINEUP','SETTLEMENT','FIXTURE','SYSTEM')}
    _,ps=push_status_payload();push_live=bool(ps.get('enabled') and ps.get('subscription_count'))
    return 200,{'items':items,'summary':summary,'count':len(items),'delivery':{
        'in_app':True,'external_push':push_live,
        'external_push_status':'ACTIVE' if push_live else ('READY_TO_SUBSCRIBE' if ps.get('enabled') else 'NOT_PROVISIONED'),
        'subscription_count':ps.get('subscription_count',0),
        'policy':'No extra football API calls. Notifications are derived from lifecycle and system-health data already collected.'},'read_only':True}

def dispatch(path_with_query):
    u=urlparse(path_with_query);path=u.path.rstrip('/') or '/';q=parse_qs(u.query,keep_blank_values=True)
    if path=='/v1/match':return aggregate_match((q.get('fixture_id') or [''])[0])
    if path=='/v1/performance':return performance_payload()
    if path=='/v1/value-radar':return value_radar_payload((q.get('limit') or ['50'])[0])
    if path=='/v1/runtime':return runtime_payload()
    if path=='/v1/push/status':return push_status_payload()
    if path=='/v1/notifications':
        try:limit=int((q.get('limit') or ['100'])[0])
        except ValueError:limit=100
        return notifications_payload(limit)
    return base.dispatch(path_with_query)

def dispatch_post(path,body):
    p=urlparse(path).path.rstrip('/') or '/'
    if p=='/v1/push/subscribe':return push_subscribe(body)
    if p=='/v1/push/unsubscribe':return push_unsubscribe(body)
    return 404,{'error':'NOT_FOUND'}

class Handler(BaseHTTPRequestHandler):
    server_version='PBKAppAPI/1.5'
    def _reply(self,status,payload):
        raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        try:status,payload=dispatch(self.path)
        except FileNotFoundError as e:status,payload=503,{'error':'DATA_LAYER_UNAVAILABLE','detail':str(e)}
        except Exception as e:status,payload=500,{'error':'INTERNAL_ERROR','detail':str(e)}
        self._reply(status,payload)
    def do_POST(self):
        try:
            length=int(self.headers.get('Content-Length','0') or 0)
            if length<0 or length>65536:return self._reply(413,{'error':'PAYLOAD_TOO_LARGE'})
            raw=self.rfile.read(length) if length else b'{}';body=json.loads(raw.decode('utf-8')) if raw else {}
            status,payload=dispatch_post(self.path,body)
        except json.JSONDecodeError:status,payload=400,{'error':'INVALID_JSON'}
        except Exception as e:status,payload=500,{'error':'INTERNAL_ERROR','detail':str(e)}
        self._reply(status,payload)
    def log_message(self,fmt,*args):
        if os.getenv('PBK_API_ACCESS_LOG','0')=='1':super().log_message(fmt,*args)

def self_test():
    code=base.self_test()
    if code:return code
    with base.connect() as conn:
        att=base.state_doc(conn,'attention_board.json') or {};candidates=(att.get('market_cards') or [])+(att.get('canonical') or [])+(att.get('watch') or []);fid=str((candidates[0] if candidates else {}).get('fixture_id') or '')
    if not fid:print(json.dumps({'status':'FAIL','reason':'no fixture available for match-detail self-test'}));return 1
    status,p=aggregate_match(fid);match_ok=status==200 and p.get('fixture_id')==fid and p.get('read_only') is True and isinstance(p.get('markets'),dict) and isinstance(p.get('probability'),dict)
    perf_status,perf=performance_payload();pm=perf.get('probability_module') or {};perf_ok=perf_status==200 and 'canonical' in perf and 'watch' in perf and perf.get('read_only') is True and pm.get('status') in {'ACTIVE_FORWARD_MONITORING','NOT_READY'}
    note_status,notes=notifications_payload(100);note_ok=note_status==200 and isinstance(notes.get('items'),list) and notes.get('read_only') is True and notes.get('delivery',{}).get('in_app') is True
    run_status,runtime=runtime_payload();runtime_ok=run_status==200 and runtime.get('status')=='OK' and runtime.get('api_version')=='1.5'
    push_status,push=push_status_payload();push_ok=push_status==200 and 'enabled' in push and push.get('football_api_calls')==0
    radar_status,radar=value_radar_payload()
    radar_ok=radar_status==200 and isinstance(radar.get('items'),list) and radar.get('creates_signal') is False and p.get('value_radar',{}).get('creates_signal') is False
    ok=match_ok and perf_ok and note_ok and runtime_ok and push_ok and radar_ok
    print(json.dumps({'status':'OK' if ok else 'FAIL','match_detail_fixture_id':fid,'http_status':status,'canonical_rows':len(p.get('canonical') or []),'watch_rows':len(p.get('watch') or []),'probability_prediction_rows':len((p.get('probability') or {}).get('predictions') or []),'performance_http_status':perf_status,'notifications_http_status':note_status,'notification_rows':len(notes.get('items') or []),'runtime_http_status':run_status,'runtime_api_version':runtime.get('api_version'),'push_status':push.get('status'),'probability_module':pm.get('status'),'read_only':p.get('read_only')},ensure_ascii=False))
    return 0 if ok else 1

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--self-test',action='store_true');ap.add_argument('--host',default=os.getenv('PBK_API_HOST','127.0.0.1'));ap.add_argument('--port',type=int,default=int(os.getenv('PBK_API_PORT','8787')));a=ap.parse_args()
    if a.self_test:raise SystemExit(self_test())
    server=ThreadingHTTPServer((a.host,a.port),Handler);print(f'PBK App API serving http://{a.host}:{a.port} from {base.DB}',flush=True);server.serve_forever()
if __name__=='__main__':main()
