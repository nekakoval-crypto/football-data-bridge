#!/usr/bin/env python3
"""Stage74 app API: Stage73-compatible read-only API plus app aggregations."""
from __future__ import annotations
import argparse, json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import stage73_internal_api as base

TABLES={
    'canonical':'canonical_signals',
    'watch':'watch_signals',
    'challengers':'challenger_signals',
    'context':'context_latest',
    'lifecycle':'lifecycle_events',
    'exposure':'exposure_positions',
    'odds':'odds_snapshots',
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
    for candidate in ('captured_at_utc','event_at_utc','event_time_utc','kickoff_utc','line','home_handicap_line'):
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
        return 200,{
            'fixture_id':str(fixture_id),
            'identity':identity,
            'attention_card':card,
            'canonical':payload['canonical'],
            'watch':payload['watch'],
            'challengers':payload['challengers'],
            'context':payload['context'],
            'lifecycle':payload['lifecycle'],
            'exposure':payload['exposure'],
            'odds':payload['odds'],
            'markets':{
                'team_totals':{'openers':payload['team_total_openers'],'snapshots':payload['team_total_snapshots'],'closes':payload['team_total_closes']},
                'double_chance':{'openers':payload['double_chance_openers'],'snapshots':payload['double_chance_snapshots'],'closes':payload['double_chance_closes']},
                'european_handicap':{'openers':payload['european_handicap_openers'],'snapshots':payload['european_handicap_snapshots'],'closes':payload['european_handicap_closes']},
                'dnb':{'openers':payload['dnb_openers'],'snapshots':payload['dnb_snapshots'],'closes':payload['dnb_closes']},
            },
            'settlements':payload['settlements'],
            'read_only':True,
            'creates_signal':False,
        }

def performance_payload():
    with base.connect() as conn:
        canonical=base.state_doc(conn,'forward_performance.json') or {}
        watch=base.state_doc(conn,'watch_performance.json') or {}
        readiness=base.state_doc(conn,'core_market_readiness.json') or {}
        research_settlement_rows=0
        if base.table_exists(conn,'core_market_settlements'):
            research_settlement_rows=conn.execute('SELECT COUNT(*) AS n FROM core_market_settlements').fetchone()['n']
        return 200,{
            'scope':'prospective operational performance; historical research kept separate',
            'canonical':canonical,
            'watch':watch,
            'core_market_readiness':readiness,
            'research_market_settlement_rows':research_settlement_rows,
            'probability_module':{
                'status':'NOT_VALIDATED_YET',
                'max_probability_ranking_available':False,
                'value_ranking_available':False,
                'policy':'Do not invent model probabilities. Rankings activate only after a separately validated probability model exists.'
            },
            'read_only':True,
        }

def notification_title(row,category):
    teams=f"{row.get('home_team') or '—'} — {row.get('away_team') or '—'}"
    tag=row.get('rule_or_stage') or ''
    if category=='SIGNAL': return f"Новый {tag or 'R'}: {teams}"
    if category=='WATCH': return f"{tag or 'WATCH'} crossing: {teams}"
    if category=='LINEUP': return f"Составы / ротация: {teams}"
    if category=='SETTLEMENT': return f"Результат: {teams}"
    if category=='FIXTURE': return f"Изменение матча: {teams}"
    return teams

def notification_body(row,category):
    parts=[]
    selection=row.get('selection') or ''
    if selection: parts.append(selection)
    odds=row.get('odds')
    bookmaker=row.get('bookmaker') or ''
    if odds not in (None,''):
        parts.append(f"{odds}"+(f" @ {bookmaker}" if bookmaker else ''))
    status=row.get('status') or ''
    if category in {'SETTLEMENT','FIXTURE'} and status: parts.append(status)
    details=row.get('details') or ''
    if details: parts.append(details)
    return ' · '.join(str(x) for x in parts if x)

def notifications_payload(limit=100):
    limit=max(1,min(int(limit or 100),200))
    items=[]
    with base.connect() as conn:
        if base.table_exists(conn,'lifecycle_events'):
            cols=set(base.columns(conn,'lifecycle_events'))
            required={'entity_id','event_type','event_time_utc'}
            if required.issubset(cols):
                rows=conn.execute('SELECT * FROM lifecycle_events ORDER BY event_time_utc DESC LIMIT 500').fetchall()
                for raw in rows:
                    row=base.enrich(raw)
                    event_type=str(row.get('event_type') or '')
                    spec=NOTIFICATION_EVENTS.get(event_type)
                    category=None;severity=None
                    if spec:
                        category,severity=spec
                    elif event_type=='CONTEXT_SNAPSHOT' and 'lineups=YES' in str(row.get('details') or '').upper():
                        category,severity='LINEUP','high'
                    if not category: continue
                    event_time=str(row.get('event_time_utc') or '')
                    entity_id=str(row.get('entity_id') or '')
                    nid='|'.join([entity_id,event_time,event_type])
                    items.append({
                        'id':nid,
                        'category':category,
                        'severity':severity,
                        'event_type':event_type,
                        'event_time_utc':event_time,
                        'fixture_id':str(row.get('api_fixture_id') or ''),
                        'league':row.get('league') or '',
                        'home_team':row.get('home_team') or '',
                        'away_team':row.get('away_team') or '',
                        'rule_or_stage':row.get('rule_or_stage') or '',
                        'title':notification_title(row,category),
                        'body':notification_body(row,category),
                    })
                    if len(items)>=limit: break
        health=base.state_doc(conn,'system_health.json') or {}
        hstatus=str(health.get('status') or '').upper()
        issues=health.get('issues') or []
        if hstatus and hstatus not in {'HEALTHY','OK'}:
            if issues:
                for idx,issue in enumerate(issues[:20]):
                    if isinstance(issue,dict):
                        sev=str(issue.get('severity') or issue.get('status') or 'WARN').upper()
                        body=str(issue.get('message') or issue.get('issue') or issue.get('details') or issue)
                        stage=str(issue.get('stage') or '')
                    else:
                        sev='WARN';body=str(issue);stage=''
                    items.append({
                        'id':f"SYSTEM|{health.get('generated_at_utc') or ''}|{idx}|{body}",
                        'category':'SYSTEM','severity':'high' if sev in {'CRITICAL','ERROR','FAIL'} else 'medium',
                        'event_type':'SYSTEM_HEALTH','event_time_utc':health.get('generated_at_utc') or '',
                        'fixture_id':'','league':'','home_team':'','away_team':'','rule_or_stage':stage,
                        'title':f"Системное предупреждение{': '+stage if stage else ''}",'body':body,
                    })
            else:
                items.append({
                    'id':f"SYSTEM|{health.get('generated_at_utc') or ''}|{hstatus}",
                    'category':'SYSTEM','severity':'high','event_type':'SYSTEM_HEALTH','event_time_utc':health.get('generated_at_utc') or '',
                    'fixture_id':'','league':'','home_team':'','away_team':'','rule_or_stage':'',
                    'title':f"Состояние системы: {hstatus}",'body':'Проверь раздел Health перед использованием сигналов.',
                })
    items.sort(key=lambda x:x.get('event_time_utc') or '',reverse=True)
    items=items[:limit]
    summary={k:sum(1 for x in items if x['category']==k) for k in ('SIGNAL','WATCH','LINEUP','SETTLEMENT','FIXTURE','SYSTEM')}
    return 200,{
        'items':items,
        'summary':summary,
        'count':len(items),
        'delivery':{
            'in_app':True,
            'external_push':False,
            'external_push_status':'PENDING_SERVER',
            'policy':'No extra football API calls. Notifications are derived from lifecycle and system-health data already collected.'
        },
        'read_only':True,
    }

def dispatch(path_with_query):
    u=urlparse(path_with_query);path=u.path.rstrip('/') or '/';q=parse_qs(u.query,keep_blank_values=True)
    if path=='/v1/match':return aggregate_match((q.get('fixture_id') or [''])[0])
    if path=='/v1/performance':return performance_payload()
    if path=='/v1/notifications':
        try:limit=int((q.get('limit') or ['100'])[0])
        except ValueError:limit=100
        return notifications_payload(limit)
    return base.dispatch(path_with_query)

class Handler(BaseHTTPRequestHandler):
    server_version='PBKAppAPI/1.2'
    def do_GET(self):
        try:status,payload=dispatch(self.path)
        except FileNotFoundError as e:status,payload=503,{'error':'DATA_LAYER_UNAVAILABLE','detail':str(e)}
        except Exception as e:status,payload=500,{'error':'INTERNAL_ERROR','detail':str(e)}
        raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def log_message(self,fmt,*args):
        if os.getenv('PBK_API_ACCESS_LOG','0')=='1':super().log_message(fmt,*args)

def self_test():
    code=base.self_test()
    if code:return code
    with base.connect() as conn:
        att=base.state_doc(conn,'attention_board.json') or {}
        candidates=(att.get('market_cards') or [])+(att.get('canonical') or [])+(att.get('watch') or [])
        fid=str((candidates[0] if candidates else {}).get('fixture_id') or '')
    if not fid:
        print(json.dumps({'status':'FAIL','reason':'no fixture available for match-detail self-test'}));return 1
    status,p=aggregate_match(fid);match_ok=status==200 and p.get('fixture_id')==fid and p.get('read_only') is True and isinstance(p.get('markets'),dict)
    perf_status,perf=performance_payload();perf_ok=perf_status==200 and 'canonical' in perf and 'watch' in perf and perf.get('read_only') is True
    note_status,notes=notifications_payload(100);note_ok=note_status==200 and isinstance(notes.get('items'),list) and notes.get('read_only') is True and notes.get('delivery',{}).get('in_app') is True
    ok=match_ok and perf_ok and note_ok
    print(json.dumps({'status':'OK' if ok else 'FAIL','match_detail_fixture_id':fid,'http_status':status,'canonical_rows':len(p.get('canonical') or []),'watch_rows':len(p.get('watch') or []),'lifecycle_rows':len(p.get('lifecycle') or []),'performance_http_status':perf_status,'notifications_http_status':note_status,'notification_rows':len(notes.get('items') or []),'probability_module':(perf.get('probability_module') or {}).get('status'),'read_only':p.get('read_only')},ensure_ascii=False))
    return 0 if ok else 1

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--self-test',action='store_true');ap.add_argument('--host',default=os.getenv('PBK_API_HOST','127.0.0.1'));ap.add_argument('--port',type=int,default=int(os.getenv('PBK_API_PORT','8787')));a=ap.parse_args()
    if a.self_test:raise SystemExit(self_test())
    server=ThreadingHTTPServer((a.host,a.port),Handler);print(f'PBK App API serving http://{a.host}:{a.port} from {base.DB}',flush=True);server.serve_forever()
if __name__=='__main__':main()
