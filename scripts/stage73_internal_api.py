#!/usr/bin/env python3
"""Stage 73 — read-only PBK HTTP API over the Stage72 SQLite projection."""
from __future__ import annotations
import argparse, json, os, sqlite3
from formation_research import read_audit
from stage97_style_matchup_today_live import build_today_live_style_context
from contextlib import closing
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
    if d.get('market_family')=='DRAW_NO_BET':
        d.setdefault('selection_a_ru','Ф1(0)');d.setdefault('selection_b_ru','Ф2(0)')
    if d.get('market_family')=='DOUBLE_CHANCE':
        d.setdefault('selection_a_ru','1Х');d.setdefault('selection_b_ru','Х2');d.setdefault('selection_c_ru','12')
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
def today_payload(conn):
    generated=dict(conn.execute('SELECT key,value FROM pbk_meta').fetchall()).get('built_at_utc')
    rows=[]
    if table_exists(conn,'today_matches'):
        for raw in conn.execute('SELECT * FROM today_matches ORDER BY kickoff_utc ASC, fixture_id ASC').fetchall():
            row=dict(raw)
            try:row['score']=json.loads(row.get('score') or 'null')
            except (TypeError,ValueError):row['score']=None
            observed=row.get('observed_at_utc') or None;freshness='unknown'
            if observed and generated:
                try:
                    age=(datetime.fromisoformat(generated.replace('Z','+00:00'))-datetime.fromisoformat(observed.replace('Z','+00:00'))).total_seconds();freshness='fresh' if 0<=age<=21600 else ('stale' if age>21600 else 'unknown')
                except ValueError:freshness='unknown'
            row.update({'freshness_status':freshness,'observed_at_utc':observed,'score':row.get('score')})

            style_fixture = None
            if table_exists(conn, 'current_round_matches'):
                current = conn.execute(
                    'SELECT * FROM current_round_matches WHERE fixture_id=? LIMIT 1',
                    (str(row.get('fixture_id') or ''),),
                ).fetchone()
                if current:
                    style_fixture = dict(current)

            row['style_matchup'] = (
                build_today_live_style_context(
                    conn,
                    style_fixture,
                )
                if style_fixture
                else {
                    'version': 'PBK_STAGE97_STYLE_MATCHUP_TODAY_LIVE_V1',
                    'fixture_id': str(row.get('fixture_id') or ''),
                    'available': False,
                    'style_status': 'DATA_WAITING',
                    'matchup_status': 'DATA_WAITING',
                    'research_only': True,
                    'provider_polling': False,
                    'creates_signal': False,
                    'probability_mutation': False,
                    'eligibility_mutation': False,
                }
            )
            rows.append(row)
    return {'api_version':API_VERSION,'day_basis':'UTC','day_definition':'projection day is the UTC date of the Stage72 build timestamp','date_utc':generated[:10] if generated else None,'generated_at_utc':generated,'matches':rows,'coverage':{'live_completeness_guaranteed':False,'source':'Stage53/Stage54 operational data projected by Stage72','limitations':['Current PBK sources do not provide a complete real-time LIVE feed.']},'freshness':{'status':'unknown' if not generated else 'known','generated_at_utc':generated,'per_match_field':'freshness_status'},'read_only':True,'provider_polling':False}

def motivation_compact(conn,fixture_id):
    empty={'available':False,'home_primary_context':None,'away_primary_context':None,
           'home_pressure':'UNKNOWN','away_pressure':'UNKNOWN',
           'snapshot_observed_at_utc':None,'no_lookahead':True,'status':'UNKNOWN'}
    if not fixture_id or not table_exists(conn,'fixture_motivation'):return empty
    row=conn.execute('SELECT * FROM fixture_motivation WHERE fixture_id=?',(str(fixture_id),)).fetchone()
    if not row:return empty
    item=dict(row)
    return {'available':item.get('available')=='1',
            'home_primary_context':item.get('home_primary_context') or None,
            'away_primary_context':item.get('away_primary_context') or None,
            'home_pressure':item.get('home_pressure') or 'UNKNOWN',
            'away_pressure':item.get('away_pressure') or 'UNKNOWN',
            'snapshot_observed_at_utc':item.get('snapshot_observed_at_utc') or None,
            'no_lookahead':item.get('no_lookahead')=='1',
            'status':item.get('coverage_status') or 'UNKNOWN'}

def current_rounds_payload(conn):
    generated=dict(conn.execute('SELECT key,value FROM pbk_meta').fetchall()).get('built_at_utc');leagues=[]
    if table_exists(conn,'current_round_leagues'):
        league_rows=conn.execute('SELECT * FROM current_round_leagues ORDER BY rowid').fetchall()
        for league in league_rows:
            item={key:dict(league).get(key) or None for key in ('provider_league_id','league_name','country','country_flag_url','league_logo_url','season','round','observed_at_utc','status','error')};item['matches']=[]
            if table_exists(conn,'current_round_matches') and item['provider_league_id']:
                rows=conn.execute('SELECT * FROM current_round_matches WHERE provider_league_id=? ORDER BY kickoff_utc ASC, fixture_id ASC',(str(item['provider_league_id']),)).fetchall()
                for raw in rows:
                    row=dict(raw)
                    try:
                        home=row.pop('score_home',None);away=row.pop('score_away',None);home=None if home in (None,'') else int(home) if str(home).lstrip('-').isdigit() else home;away=None if away in (None,'') else int(away) if str(away).lstrip('-').isdigit() else away;row['score']={'home':home,'away':away} if home is not None or away is not None else None
                    except (TypeError,ValueError):row['score']=None
                    for key in ('fixture_id','kickoff_utc','home_team','home_team_logo_url','away_team','away_team_logo_url','status','source_status','elapsed','observed_at_utc','live_observed_at_utc','live_freshness_status','red_cards_home','red_cards_away'):row.setdefault(key,None)
                    for key in ('red_cards_home','red_cards_away'):
                        value=row.get(key);row[key]=int(value) if str(value).isdigit() else None
                    match={key:(row.get(key) or None) for key in ('fixture_id','kickoff_utc','home_team','home_team_logo_url','away_team','away_team_logo_url','status','source_status','elapsed','score','observed_at_utc','live_observed_at_utc','live_freshness_status','red_cards_home','red_cards_away')}
                    match['motivation']=motivation_compact(conn,row.get('fixture_id'))
                    match['style_matchup']=build_today_live_style_context(
                        conn,
                        row,
                    )
                    item['matches'].append(match)
            leagues.append(item)
    return {'api_version':API_VERSION,'generated_at_utc':generated,'leagues':leagues,'read_only':True,'provider_polling':False,'coverage':{'partial_leagues_possible':any(row.get('status')!='available' for row in leagues),'source':'current_round_leagues/current_round_matches SQLite projection'}}

def standings_payload(conn,q):
    league=qfirst(q,'provider_league_id');season=qfirst(q,'season');built=dict(conn.execute('SELECT key,value FROM pbk_meta').fetchall()).get('built_at_utc');base={'api_version':API_VERSION,'provider_league_id':league,'season':season,'requested_as_of_utc':qfirst(q,'as_of_utc') or built,'snapshot_id':None,'snapshot_observed_at_utc':None,'available':False,'no_lookahead':True,'age_seconds_at_cutoff':None,'source':None,'teams':[]}
    if not league or not season:base.update({'error':'MISSING_STANDINGS_SCOPE'});return 400,base
    cutoff=base['requested_as_of_utc']
    try:
        parsed_cutoff=datetime.fromisoformat(str(cutoff).replace('Z','+00:00'))
        if parsed_cutoff.tzinfo is None:raise ValueError('timezone required')
        cutoff_dt=parsed_cutoff.astimezone(timezone.utc)
    except (TypeError,ValueError):base.update({'error':'INVALID_AS_OF_UTC'});return 400,base
    if not table_exists(conn,'standings_snapshots'):return 200,base
    rows=conn.execute('SELECT * FROM standings_snapshots WHERE provider_league_id=? AND season=?',(str(league),str(season))).fetchall();eligible=[]
    for row in rows:
        try:observed=datetime.fromisoformat(str(row['observed_at_utc']).replace('Z','+00:00')).astimezone(timezone.utc)
        except (TypeError,ValueError):continue
        if observed<=cutoff_dt:eligible.append((observed,row))
    if not eligible:return 200,base
    latest=max(observed for observed,_ in eligible);snapshot_ids={row['snapshot_id'] for observed,row in eligible if observed==latest}
    if len(snapshot_ids)!=1:return 200,base
    snapshot_id=next(iter(snapshot_ids));selected=[dict(row) for observed,row in eligible if row['snapshot_id']==snapshot_id];teams=[]
    for row in selected:
        item={key:row.get(key) for key in ('team_id','team_name','team_logo_url','rank','points','played','win','draw','lose','goals_for','goals_against','goals_diff','form','group_name','description','source')};teams.append(item)
    teams.sort(key=lambda row:(row.get('rank') or '',row.get('team_id') or ''));base.update({'snapshot_id':snapshot_id,'snapshot_observed_at_utc':latest.isoformat().replace('+00:00','Z'),'available':True,'source':selected[0].get('source') or None,'teams':teams,'age_seconds_at_cutoff':(cutoff_dt-latest).total_seconds()});return 200,base

def motivation_payload(conn,q):
    fixture_id=qfirst(q,'fixture_id')
    if not fixture_id:return 400,{'api_version':API_VERSION,'error':'MISSING_FIXTURE_ID','read_only':True,'provider_polling':False}
    if not table_exists(conn,'fixture_motivation'):
        return 404,{'api_version':API_VERSION,'error':'UNKNOWN_FIXTURE','fixture_id':fixture_id,'read_only':True,'provider_polling':False}
    row=conn.execute('SELECT * FROM fixture_motivation WHERE fixture_id=?',(str(fixture_id),)).fetchone()
    if not row:
        known=table_exists(conn,'current_round_matches') and conn.execute('SELECT 1 FROM current_round_matches WHERE fixture_id=?',(str(fixture_id),)).fetchone()
        if known:
            return 200,{'api_version':API_VERSION,'fixture_id':fixture_id,'available':False,'no_lookahead':True,'coverage':{'available':False,'status':'UNKNOWN','limitations':['NO_STANDINGS_SNAPSHOT']},'read_only':True,'provider_polling':False}
        return 404,{'api_version':API_VERSION,'error':'UNKNOWN_FIXTURE','fixture_id':fixture_id,'read_only':True,'provider_polling':False}
    try:payload=json.loads(row['payload_json'])
    except (TypeError,ValueError,json.JSONDecodeError):
        return 500,{'api_version':API_VERSION,'error':'INVALID_MOTIVATION_PROJECTION','fixture_id':fixture_id,'read_only':True,'provider_polling':False}
    payload['api_version']=API_VERSION;payload['read_only']=True;payload['provider_polling']=False;return 200,payload

def config_doc(path,fallback):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return fallback

def challenger_observations(conn,q):
    family,league=qfirst(q,'family'),qfirst(q,'league');board=state_doc(conn,'stage71_challenger_board.json') or {};card=next((r for r in board.get('rows',[]) if r.get('family')==family and r.get('league')==league),None)
    if card is None:return 404,{'error':'UNKNOWN_CHALLENGER_CARD'}
    active=card.get('status') in {'ACTIVE','DEGRADATION_REVIEW','SUSPENSION_REVIEW'};table='canonical_signals' if active else 'challenger_signals';source='canonical' if active else 'research-only';limit=as_int(qfirst(q,'limit'),5,1,MAX_LIMIT);offset=as_int(qfirst(q,'offset'),0,0,10_000_000);payload={'items':[],'count':0,'limit':limit,'offset':offset,'source':source,'read_only':True,'available':False};cols=set(columns(conn,table)) if table_exists(conn,table) else set();family_col='rule' if active else 'family'
    if family_col not in cols:return 200,payload
    league_expr="COALESCE(NULLIF(league, ''), 'Serie A')" if active and 'league' in cols else ("'Serie A'" if active else 'league');where=f' WHERE "{family_col}" = ? AND {league_expr} = ?';args=[family,league];payload['count']=conn.execute(f'SELECT COUNT(*) FROM "{table}"'+where,args).fetchone()[0];id_col='forward_id' if active else 'research_id';rows=conn.execute(f'SELECT * FROM "{table}"'+where+f' ORDER BY julianday(kickoff_utc) DESC, "{id_col}" DESC LIMIT ? OFFSET ?',args+[limit,offset]).fetchall()
    for row in rows:
        r=enrich(row);selection=r.get('selection_ru');price_col={'П1':'trigger_b365_home','Х':'trigger_b365_draw','П2':'trigger_b365_away'}.get(selection);bookmaker=r.get('paper_user_execution_bookmaker') if active else r.get('user_bookmaker');status=r.get('status');item={key:r.get(key) or None for key in ('kickoff_utc','home_team','away_team','final_home_goals','final_away_goals')};item.update({'id':r.get(id_col),'selection':selection,'bet365_price':r.get('trigger_selected_odds') if active else r.get(price_col),'marathonbet_price':(r.get('paper_user_execution_odds') if active else r.get('user_odds')) if str(bookmaker).lower()=='marathonbet' else None,'status':'PENDING' if status=='PAPER' else status,'result':r.get('result') if status=='SETTLED' else None,'user_profit_u':r.get('user_profit_u') if status=='SETTLED' else None})
        if status!='SETTLED':item['final_home_goals']=item['final_away_goals']=None
        payload['items'].append(item)
    payload['available']=True;return 200,payload

def dispatch(path_with_query):
    u=urlparse(path_with_query);path=u.path.rstrip('/') or '/';q=parse_qs(u.query,keep_blank_values=True)
    with closing(connect()) as conn:
        if path=='/v1/challengers/observations':return challenger_observations(conn,q)
        if path=='/':return 200,{'service':'PBK Internal API','api_version':API_VERSION,'read_only':True,'docs':'/v1/meta'}
        if path in {'/health','/v1/health'}:
            meta=dict(conn.execute('SELECT key,value FROM pbk_meta').fetchall()) if table_exists(conn,'pbk_meta') else {};sh=state_doc(conn,'system_health.json') or {};return 200,{'status':'OK' if str(sh.get('status','HEALTHY')).upper()!='CRITICAL' else 'CRITICAL','api_version':API_VERSION,'db_schema_version':meta.get('schema_version'),'db_built_at_utc':meta.get('built_at_utc'),'system_health':sh.get('status','UNKNOWN'),'read_only':True}
        if path=='/v1/meta':
            meta=dict(conn.execute('SELECT key,value FROM pbk_meta').fetchall()) if table_exists(conn,'pbk_meta') else {};return 200,{'api_version':API_VERSION,'db':meta,'global_odds_cap':None,'eligibility_mutation':False}
        if path=='/v1/today':return 200,today_payload(conn)
        if path=='/v1/rounds/current':return 200,current_rounds_payload(conn)
        if path=='/v1/standings':return standings_payload(conn,q)
        if path=='/v1/motivation':return motivation_payload(conn,q)
        if path=='/v1/match-card':return __import__('match_card_v2').build_match_card(conn,qfirst(q,'fixture_id'))
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
        if path=='/v1/markets/settlements':return 200,query_table(conn,'core_market_settlements',q,{'fixture_id':'api_fixture_id','league':'league','market_family':'market_family','status':'settlement_status'},['marathon_close_a','bet365_close_a'],['kickoff_utc','api_fixture_id','market_family','settlement_key'])
        if path=='/v1/lifecycle':return 200,query_table(conn,'lifecycle_events',q,{'signal_id':'signal_id','fixture_id':'api_fixture_id','strategy':'rule'},[],['event_at_utc','signal_id'])
        if path=='/v1/exposure':return 200,query_table(conn,'exposure_positions',q,{'fixture_id':'api_fixture_id','status':'status','strategy':'rules'},[],['kickoff_utc','api_fixture_id'])
        if path=='/v1/research/formations':return 200,read_audit(conn,(q.get('team_id') or [None])[0],(q.get('fixture_id') or [None])[0])
        if path=='/v1/context':return 200,query_table(conn,'context_latest',q,{'fixture_id':'api_fixture_id'},[],['kickoff_utc','api_fixture_id'])
        if path=='/v1/odds':return 200,query_table(conn,'odds_snapshots',q,{'fixture_id':'api_fixture_id','bookmaker':'bookmaker'},['odds'],['captured_at_utc','api_fixture_id'])
        if path=='/v1/attention':return 200,(state_doc(conn,'attention_board.json') or {})
        if path=='/v1/governance':return 200,{'system_health':state_doc(conn,'system_health.json'),'exposure':state_doc(conn,'exposure_summary.json'),'watch_promotion':state_doc(conn,'watch_promotion_gate.json'),'league_challenger':state_doc(conn,'stage71_challenger_board.json'),'fonbet_coverage':state_doc(conn,'stage71b_fonbet_coverage.json'),'team_total_capture':state_doc(conn,'stage71c_last_run.json'),'double_chance_capture':state_doc(conn,'stage71e_last_run.json'),'european_handicap_capture':state_doc(conn,'stage71f_last_run.json'),'dnb_capture':state_doc(conn,'stage71g_last_run.json'),'core_market_settlement':state_doc(conn,'stage71i_last_run.json')}
        if path=='/v1/config/strategy-filter':return 200,config_doc(STRATEGY_FILTER,{'global_odds_cap':None,'groups':[],'future_ui_filters':[]})
        if path=='/v1/config/market-scope':return 200,config_doc(MARKET_SCOPE,{'status':'UNAVAILABLE','allowed_market_families':[],'deferred_market_universe':[]})
        if path=='/v1/config/core-market-registry':return 200,config_doc(CORE_MARKETS,{'scope':'UNAVAILABLE','markets':[]})
    return 404,{'error':'NOT_FOUND','path':path,'api_version':API_VERSION}

class Handler(BaseHTTPRequestHandler):
    server_version='PBKInternalAPI/1.5'
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
        '/v1/markets/settlements?limit=1':lambda p:p.get('count') is not None,
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