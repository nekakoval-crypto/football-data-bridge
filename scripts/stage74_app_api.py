#!/usr/bin/env python3
"""Stage74 app API: Stage73-compatible read-only API plus aggregated match detail."""
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

def fixture_rows(conn,table,fixture_id,limit=500):
    if not base.table_exists(conn,table): return []
    cols=set(base.columns(conn,table))
    if 'api_fixture_id' not in cols: return []
    order=''
    for candidate in ('captured_at_utc','event_at_utc','kickoff_utc','line','home_handicap_line'):
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

def dispatch(path_with_query):
    u=urlparse(path_with_query);path=u.path.rstrip('/') or '/';q=parse_qs(u.query,keep_blank_values=True)
    if path=='/v1/match':return aggregate_match((q.get('fixture_id') or [''])[0])
    return base.dispatch(path_with_query)

class Handler(BaseHTTPRequestHandler):
    server_version='PBKAppAPI/1.0'
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
    status,p=aggregate_match(fid);ok=status==200 and p.get('fixture_id')==fid and p.get('read_only') is True and isinstance(p.get('markets'),dict)
    print(json.dumps({'status':'OK' if ok else 'FAIL','match_detail_fixture_id':fid,'http_status':status,'canonical_rows':len(p.get('canonical') or []),'watch_rows':len(p.get('watch') or []),'lifecycle_rows':len(p.get('lifecycle') or []),'read_only':p.get('read_only')},ensure_ascii=False))
    return 0 if ok else 1

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--self-test',action='store_true');ap.add_argument('--host',default=os.getenv('PBK_API_HOST','127.0.0.1'));ap.add_argument('--port',type=int,default=int(os.getenv('PBK_API_PORT','8787')));a=ap.parse_args()
    if a.self_test:raise SystemExit(self_test())
    server=ThreadingHTTPServer((a.host,a.port),Handler);print(f'PBK App API serving http://{a.host}:{a.port} from {base.DB}',flush=True);server.serve_forever()
if __name__=='__main__':main()
