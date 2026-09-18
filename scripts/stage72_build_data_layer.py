#!/usr/bin/env python3
"""Stage 72 — deterministic PBK unified SQLite data layer.

CSV/JSON operational files remain audit/source-of-truth during migration.
This script builds a disposable, reproducible SQLite database for Stage73/API
and future PC/Android clients. No API calls. Formation research appends a separate
context-only journal; strategy and settlement source ledgers are never changed.
"""
from __future__ import annotations
import csv, json, os, re, sqlite3, hashlib
import formation_research
from datetime import datetime, timezone
from pathlib import Path
from stage75_value_radar import read_jsonl, EVENT_FIELDS
import standings_motivation as motivation

OPS=Path(os.getenv('OPS_DIR','ops'))
OUT=Path(os.getenv('STAGE72_DB_PATH','build/pbk_unified.sqlite'))
META=OPS/'stage72_last_run.json';SCHEMA=OPS/'stage72_schema.json';SCHEMA_VERSION='15'
STANDINGS_FIELDS=['snapshot_id','provider_league_id','league_name','season','observed_at_utc',
                  'team_id','team_name','team_logo_url','rank','points','played','win','draw',
                  'lose','goals_for','goals_against','goals_diff','form','group_name',
                  'description','source']
MOTIVATION_FIELDS=['fixture_id','provider_league_id','season','kickoff_utc','snapshot_id',
                   'snapshot_observed_at_utc','home_team_id','away_team_id','home_rank','away_rank',
                   'home_points','away_points','home_primary_context','away_primary_context',
                   'home_pressure','away_pressure','home_season_phase','away_season_phase',
                   'motivation_status','coverage_status','available','no_lookahead','limitations_json',
                   'home_objectives_json','away_objectives_json','home_reason_codes_json',
                   'away_reason_codes_json','payload_json']
CORE_ALIASES={
    'competitions':'stage71_league_catalog.csv','canonical_signals':'user_forward_view.csv','challenger_signals':'stage71_challenger_forward.csv','watch_signals':'stage65_watch_ledger.csv','lifecycle_events':'signal_lifecycle_events.csv','exposure_positions':'exposure_map.csv','context_latest':'context_latest.csv','odds_snapshots':'odds_snapshots.csv',
    'screen_matches':'latest_screen.csv','match_result_snapshots':'stage61_market_snapshots.csv','match_total_snapshots':'stage62_ou_snapshots.csv','btts_snapshots':'stage63_btts_snapshots.csv',
    'team_total_openers':'stage71c_team_total_openers.csv','team_total_snapshots':'stage71c_team_total_snapshots.csv','team_total_closes':'stage71c_team_total_closes.csv',
    'double_chance_openers':'stage71e_double_chance_openers.csv','double_chance_snapshots':'stage71e_double_chance_snapshots.csv','double_chance_closes':'stage71e_double_chance_closes.csv',
    'european_handicap_openers':'stage71f_eh_openers.csv','european_handicap_snapshots':'stage71f_eh_snapshots.csv','european_handicap_closes':'stage71f_eh_closes.csv',
    'dnb_openers':'stage71g_dnb_openers.csv','dnb_snapshots':'stage71g_dnb_snapshots.csv','dnb_closes':'stage71g_dnb_closes.csv',
    'core_market_settlements':'stage71i_market_settlements.csv',
    'probability_predictions':'stage75_probability_predictions.csv','probability_settlements':'stage75_probability_settlements.csv',
}
CURRENT_ROUND_LEAGUE_FIELDS=['provider_league_id','league_name','country','country_flag_url','league_logo_url','season','round','observed_at_utc','status','error']
CURRENT_ROUND_FIXTURE_FIELDS=['fixture_id','provider_league_id','league_name','country','country_flag_url','league_logo_url','season','round','kickoff_utc','home_team','home_team_logo_url','away_team','away_team_logo_url','status','source_status','score_home','score_away','observed_at_utc','live_observed_at_utc','live_freshness_status','elapsed','red_cards_home','red_cards_away']
JSON_DOCS=['attention_board.json','daily_brief.json','forward_performance.json','watch_performance.json','watch_promotion_gate.json','system_health.json','exposure_summary.json','stage71_challenger_board.json','signal_lifecycle_cards.json','stage71b_fonbet_coverage.json','stage71c_last_run.json','stage71e_last_run.json','stage71f_last_run.json','stage71g_last_run.json','stage71i_last_run.json','probability_rankings.json','probability_performance.json','stage75_last_run.json']
def now_iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
JSON_DOCS.append('value_radar_current.json')
JSON_DOCS.extend([
    'team_style_validation_readiness.json',
    'team_style_dimension_validation_statistics.json',
    'matchup_validation_gate.json',
])
TODAY_STATUSES = {
    'NS': 'scheduled', 'TBD': 'scheduled', 'SCHEDULED': 'scheduled',
    '1H': 'live', 'HT': 'live', '2H': 'live', 'ET': 'live', 'BT': 'live',
    'P': 'live',
    'LIVE': 'live', 'FT': 'finished', 'AET': 'finished', 'PEN': 'finished',
    'SETTLED': 'finished',
    'PST': 'postponed', 'POSTPONED': 'postponed',
    'CANC': 'cancelled', 'CANCELLED': 'cancelled',
    'SUSP': 'suspended',
    'INT': 'interrupted',
    'ABD': 'abandoned',
    'AWD': 'awarded',
    'WO': 'walkover',
}
def safe(s):
    s=re.sub(r'[^0-9A-Za-z_]+','_',str(s)).strip('_').lower()
    if not s:s='unnamed'
    if s[0].isdigit():s='c_'+s
    return s
def read_csv(path):
    if not path.exists():return [],[]
    with path.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);rows=list(r);return list(r.fieldnames or []),rows
def create_text_table(conn,table,fields,rows):
    table=safe(table);conn.execute(f'DROP TABLE IF EXISTS "{table}"');used={};cols=[];mapping=[]
    for field in fields:
        base=safe(field);n=used.get(base,0);used[base]=n+1;col=base if n==0 else f'{base}_{n+1}';cols.append(col);mapping.append((field,col))
    if not cols:conn.execute(f'CREATE TABLE "{table}" (_empty TEXT)');return 0,[]
    column_sql=', '.join(f'"{c}" TEXT' for c in cols)
    insert_columns=', '.join(f'"{c}"' for c in cols)
    placeholders=', '.join('?' for _ in cols)
    conn.execute(f'CREATE TABLE "{table}" ({column_sql})')
    q=f'INSERT INTO "{table}" ({insert_columns}) VALUES ({placeholders})'
    conn.executemany(q,[[r.get(orig,'') for orig,col in mapping] for r in rows])
    for candidate in ('api_fixture_id','fixture_id','forward_id','research_id','watch_id','signal_id','prediction_id','market_key','settlement_key','kickoff_utc','league','family','market_family','rule','status','settlement_status','team_side','line','home_handicap_line'):
        if candidate in cols:
            try:conn.execute(f'CREATE INDEX "idx_{table}_{candidate}" ON "{table}" ("{candidate}")')
            except sqlite3.OperationalError:pass
    return len(rows),cols
def file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def today_status(value, default='unknown'):
    return TODAY_STATUSES.get(str(value or '').strip().upper(), default)
def today_value(row, *names):
    for name in names:
        value=row.get(name)
        if value not in (None,''):
            return value
    return None
def today_observed(row):
    return today_value(row, 'observed_at_utc', 'captured_at_utc', 'screened_at_utc',
                       'paper_user_execution_at_utc')
def today_sort_key(candidate):
    observed=today_observed(candidate) or ''
    source_order={'fixture_events.csv': 3, 'latest_screen.csv': 2, 'user_forward_view.csv': 1}
    return observed, source_order.get(candidate.get('_source',''), 0)
def today_projection(ops, today):
    """Build a read-only current-day view from already-collected operational files."""
    sources={}
    for filename in ('latest_screen.csv','user_forward_view.csv'):
        fields,rows=read_csv(ops/filename)
        for row in rows:
            fid=str(today_value(row,'api_fixture_id','fixture_id') or '').strip()
            kickoff=today_value(row,'kickoff_utc')
            match_date=today_value(row,'match_date') or (str(kickoff)[:10] if kickoff else '')
            if not fid or match_date != today: continue
            item={k:v for k,v in row.items() if v not in (None,'')}
            if not item.get('kickoff_utc') and item.get('match_date') and item.get('kickoff_time'):
                item['kickoff_utc']=f"{item['match_date']}T{item['kickoff_time']}:00Z"
            item['_source']=filename
            sources.setdefault(fid,[]).append(item)
    fields,events=read_csv(ops/'fixture_events.csv')
    for event in events:
        fid=str(event.get('api_fixture_id') or '').strip()
        if not fid: continue
        if event.get('event_type') == 'STATUS_CHANGE':
            event_item=dict(event)
            event_item['_source']='fixture_events.csv'
            sources.setdefault(fid,[]).append(event_item)
    output=[]
    for fid,candidates in sources.items():
        candidates.sort(key=today_sort_key)
        newest=candidates[-1]
        row={}
        for candidate in candidates:
            for key,value in candidate.items():
                if not key.startswith('_') and value not in (None,''):
                    row[key]=value
        kickoff=today_value(row,'kickoff_utc')
        if not kickoff:continue
        if kickoff and str(kickoff)[:10] != today:continue
        raw_status=today_value(newest,'new_value','fixture_status','status')
        status=today_status(raw_status, 'unknown')
        observed=today_observed(newest) or today_observed(row)
        score={'home': today_value(row,'home_goals','final_home_goals','score_home'),
               'away': today_value(row,'away_goals','final_away_goals','score_away')}
        if score['home'] is None and score['away'] is None:score=None
        output.append({'fixture_id':fid,'competition':today_value(row,'league','competition'),
                       'home_team':today_value(row,'home_team'),'away_team':today_value(row,'away_team'),
                       'kickoff_utc':kickoff,'status':status,'source_status':raw_status or None,
                       'score':score,'observed_at_utc':observed,'source':newest.get('_source')})
    return sorted(output,key=lambda r:(r.get('kickoff_utc') or '',r['fixture_id']))
def create_today_table(conn, rows):
    fields=['fixture_id','competition','home_team','away_team','kickoff_utc','status','source_status','score','observed_at_utc','source']
    text=[{k:(json.dumps(r[k],ensure_ascii=False,sort_keys=True) if isinstance(r[k],dict) else (r[k] or '')) for k in fields} for r in rows]
    return create_text_table(conn,'today_matches',fields,text)
def parse_utc(value):
    try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc)
    except (TypeError,ValueError):return None
def merge_live_overlay(base_rows, overlay_rows):
    overlays={str(row.get('fixture_id') or ''):row for row in overlay_rows}
    dynamic=('status','source_status','score_home','score_away','elapsed','observed_at_utc','live_observed_at_utc','live_freshness_status','red_cards_home','red_cards_away')
    merged=[]
    for base in base_rows:
        row=dict(base);overlay=overlays.get(str(base.get('fixture_id') or ''))
        bt=parse_utc(row.get('observed_at_utc'));ot=parse_utc((overlay or {}).get('observed_at_utc'))
        if overlay and ot and (not bt or ot>bt):
            terminal=row.get('status')=='finished';regresses_terminal=terminal and overlay.get('status') in {'live','suspended','interrupted'}
            if not regresses_terminal:
                for key in dynamic:
                    if key in overlay:row[key]=overlay[key]
        if row.get('status') in {'live','suspended','interrupted'}:
            observed=parse_utc(row.get('live_observed_at_utc') or row.get('observed_at_utc'))
            row['live_freshness_status']='fresh' if observed and (datetime.now(timezone.utc)-observed).total_seconds()<=2400 else 'stale'
        else:row['live_freshness_status']=row.get('live_freshness_status') or 'unknown'
        merged.append(row)
    return merged
def create_current_round_tables(conn, ops):
    league_fields,league_rows=read_csv(ops/'current_round_leagues.csv');fixture_fields,fixture_rows=read_csv(ops/'current_round_fixtures.csv')
    if not league_fields:league_fields=CURRENT_ROUND_LEAGUE_FIELDS
    if not fixture_fields:fixture_fields=CURRENT_ROUND_FIXTURE_FIELDS
    league_count,_=create_text_table(conn,'current_round_leagues',league_fields,league_rows)
    _,overlay_rows=read_csv(ops/'live_fixture_overlay.csv');fixture_rows=merge_live_overlay(fixture_rows,overlay_rows)
    fixture_fields=list(dict.fromkeys(fixture_fields+['live_observed_at_utc','live_freshness_status','elapsed','red_cards_home','red_cards_away']))
    fixture_count,_=create_text_table(conn,'current_round_matches',fixture_fields,fixture_rows)
    return league_count,fixture_count

def _standings_timestamp(value):
    try:
        parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError,ValueError):return None

def validate_standings_rows(rows):
    groups={};invalid_snapshots=set()
    for row in rows:
        snapshot=str(row.get('snapshot_id') or '').strip()
        if snapshot:groups.setdefault(snapshot,[]).append(row)
        league=str(row.get('provider_league_id') or '').strip();season=str(row.get('season') or '').strip();observed=str(row.get('observed_at_utc') or '').strip();team=str(row.get('team_id') or '').strip();timestamp=_standings_timestamp(observed)
        if not snapshot or not league or not season or not observed or not timestamp or not team:
            if snapshot:invalid_snapshots.add(snapshot)
    valid=[]
    for snapshot,raw_items in groups.items():
        items=[]
        for row in raw_items:
            timestamp=_standings_timestamp(row.get('observed_at_utc'))
            if timestamp is not None:items.append((row,timestamp,str(row.get('provider_league_id') or '').strip(),str(row.get('season') or '').strip(),str(row.get('team_id') or '').strip()))
        if snapshot in invalid_snapshots:continue
        keys={(x[2],x[3],x[1]) for x in items};teams=[x[4] for x in items]
        if len(keys)!=1 or len(teams)!=len(set(teams)):continue
        valid.extend(x[0] for x in items)
    return valid

def create_standings_table(conn, ops):
    _,rows=read_csv(ops/'standings_snapshots.csv');rows=validate_standings_rows(rows)
    columns=', '.join(f'"{safe(field)}" TEXT' for field in STANDINGS_FIELDS)
    conn.execute('DROP TABLE IF EXISTS standings_snapshots');conn.execute(f'CREATE TABLE standings_snapshots ({columns})')
    conn.executemany(f'INSERT INTO standings_snapshots VALUES ({",".join("?" for _ in STANDINGS_FIELDS)})',[[row.get(field,'') for field in STANDINGS_FIELDS] for row in rows])
    for name in ('provider_league_id','season','observed_at_utc','snapshot_id','team_id'):
        conn.execute(f'CREATE INDEX idx_standings_snapshots_{name} ON standings_snapshots ("{name}")')
    return len(rows)

def select_standings_as_of(conn, provider_league_id, season, as_of_utc):
    cutoff=_standings_timestamp(as_of_utc)
    if cutoff is None:return None
    result=conn.execute('SELECT * FROM standings_snapshots WHERE provider_league_id=? AND season=?',(str(provider_league_id),str(season)))
    rows_raw=result.fetchall();names=[description[0] for description in result.description] if result.description else [];rows=[dict(zip(names,row)) for row in rows_raw]
    eligible=[row for row in rows if (_standings_timestamp(row['observed_at_utc']) and _standings_timestamp(row['observed_at_utc'])<=cutoff)]
    if not eligible:return None
    latest=max(_standings_timestamp(row['observed_at_utc']) for row in eligible);snapshots={row['snapshot_id'] for row in eligible if _standings_timestamp(row['observed_at_utc'])==latest}
    if len(snapshots)!=1:return None
    snapshot_id=next(iter(snapshots))
    return [dict(row) for row in eligible if row['snapshot_id']==snapshot_id]

def standings_as_of_fixture(conn, provider_league_id, season, kickoff_utc):
    return select_standings_as_of(conn, provider_league_id, season, kickoff_utc)

def _cursor_dicts(cursor):
    names=[item[0] for item in cursor.description] if cursor.description else []
    return [dict(zip(names,row)) for row in cursor.fetchall()]

def create_fixture_motivation_table(conn):
    rows=[];violations=0
    fixtures=_cursor_dicts(conn.execute('SELECT * FROM current_round_matches ORDER BY kickoff_utc, fixture_id')) if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='current_round_matches'").fetchone() else []
    for fixture in fixtures:
        snapshot=standings_as_of_fixture(conn,fixture.get('provider_league_id'),fixture.get('season'),fixture.get('kickoff_utc'))
        payload=motivation.analyze_fixture(fixture,snapshot)
        context=payload.get('standings_context') or {};home=payload.get('home') or {};away=payload.get('away') or {};coverage=payload.get('coverage') or {}
        observed=context.get('snapshot_observed_at_utc');kickoff=fixture.get('kickoff_utc')
        if observed and kickoff:
            ot,kt=parse_utc(observed),parse_utc(kickoff)
            if ot and kt and ot>kt:violations+=1
        hs=home.get('standings') or {};as_=away.get('standings') or {}
        row={
            'fixture_id':fixture.get('fixture_id'),'provider_league_id':fixture.get('provider_league_id'),'season':fixture.get('season'),'kickoff_utc':kickoff,
            'snapshot_id':context.get('snapshot_id'),'snapshot_observed_at_utc':observed,
            'home_team_id':hs.get('team_id'),'away_team_id':as_.get('team_id'),'home_rank':hs.get('rank'),'away_rank':as_.get('rank'),'home_points':hs.get('points'),'away_points':as_.get('points'),
            'home_primary_context':home.get('primary_context'),'away_primary_context':away.get('primary_context'),'home_pressure':home.get('pressure') or 'UNKNOWN','away_pressure':away.get('pressure') or 'UNKNOWN',
            'home_season_phase':home.get('season_phase') or 'UNKNOWN','away_season_phase':away.get('season_phase') or 'UNKNOWN','motivation_status':coverage.get('motivation_status') or 'UNKNOWN','coverage_status':coverage.get('status') or 'UNKNOWN',
            'available':'1' if coverage.get('available') else '0','no_lookahead':'1',
            'limitations_json':json.dumps(coverage.get('limitations') or [],ensure_ascii=False,sort_keys=True),
            'home_objectives_json':json.dumps(home.get('objectives') or [],ensure_ascii=False,sort_keys=True),
            'away_objectives_json':json.dumps(away.get('objectives') or [],ensure_ascii=False,sort_keys=True),
            'home_reason_codes_json':json.dumps(home.get('reason_codes') or [],ensure_ascii=False,sort_keys=True),
            'away_reason_codes_json':json.dumps(away.get('reason_codes') or [],ensure_ascii=False,sort_keys=True),
            'payload_json':json.dumps(payload,ensure_ascii=False,sort_keys=True),
        }
        rows.append(row)
    count,_=create_text_table(conn,'fixture_motivation',MOTIVATION_FIELDS,rows)
    if violations:raise RuntimeError(f'historical standings leakage detected: {violations}')
    return count,violations

def main():
    built=now_iso();OUT.parent.mkdir(parents=True,exist_ok=True);OPS.mkdir(parents=True,exist_ok=True)
    if OUT.exists():OUT.unlink()
    conn=sqlite3.connect(OUT);conn.execute('PRAGMA journal_mode=DELETE');conn.execute('PRAGMA foreign_keys=ON');conn.execute('CREATE TABLE pbk_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)');conn.execute('CREATE TABLE source_manifest (source_name TEXT PRIMARY KEY, source_type TEXT, row_count INTEGER, sha256 TEXT)');missing=[]
    for p in sorted(OPS.glob('*.csv')):
        fields,rows=read_csv(p);count,_=create_text_table(conn,'raw_'+safe(p.stem),fields,rows);conn.execute('INSERT INTO source_manifest VALUES (?,?,?,?)',(p.name,'csv',count,file_sha(p)))
    stable_counts={}
    for table,filename in CORE_ALIASES.items():
        p=OPS/filename
        if not p.exists():missing.append(filename);create_text_table(conn,table,[],[]);stable_counts[table]=0;continue
        fields,rows=read_csv(p);count,_=create_text_table(conn,table,fields,rows);stable_counts[table]=count
    radar_path=OPS/'stage75_value_radar.jsonl';_,radar_rows=read_jsonl(radar_path);radar_fields=EVENT_FIELDS+sorted({k for r in radar_rows for k in r}-set(EVENT_FIELDS));text_rows=[{k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(list,dict,bool)) else ('' if v is None else str(v)) for k,v in r.items()} for r in radar_rows]
    stable_counts['value_radar_events'],_=create_text_table(conn,'value_radar_events',radar_fields,text_rows)
    for field in ('radar_id','radar_kind','first_crossed_at_utc'):conn.execute(f'CREATE INDEX "idx_value_radar_events_{field}" ON value_radar_events ("{field}")')
    if radar_path.exists():conn.execute('INSERT INTO source_manifest VALUES (?,?,?,?)',(radar_path.name,'jsonl',len(radar_rows),file_sha(radar_path)))
    conn.execute('CREATE TABLE state_documents (name TEXT PRIMARY KEY, payload_json TEXT NOT NULL, sha256 TEXT NOT NULL)')
    for name in JSON_DOCS:
        p=OPS/name
        if not p.exists():continue
        raw=p.read_text(encoding='utf-8-sig')
        try:json.loads(raw)
        except Exception:continue
        conn.execute('INSERT INTO state_documents VALUES (?,?,?)',(name,raw,file_sha(p)));conn.execute('INSERT OR REPLACE INTO source_manifest VALUES (?,?,?,?)',(name,'json',1,file_sha(p)))
    today_rows=today_projection(OPS,built[:10]);stable_counts['today_matches'],_=create_today_table(conn,today_rows);stable_counts['current_round_leagues'],stable_counts['current_round_matches']=create_current_round_tables(conn,OPS);stable_counts['standings_snapshots']=create_standings_table(conn,OPS)
    if not (OPS/'standings_snapshots.csv').exists():missing.append('standings_snapshots.csv')
    stable_counts['fixture_motivation'],leakage_violations=create_fixture_motivation_table(conn)
    audit_events=formation_research.capture(conn,OPS/'formation_research.jsonl',built)
    stable_counts['formation_research_events']=formation_research.project(conn,audit_events)
    meta={'schema_version':SCHEMA_VERSION,'built_at_utc':built,'source_policy':'ops CSV/JSON remain audit source; SQLite is reproducible projection'};conn.executemany('INSERT INTO pbk_meta VALUES (?,?)',meta.items());conn.commit();integrity=conn.execute('PRAGMA integrity_check').fetchone()[0];tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")];manifest_rows=conn.execute('SELECT COUNT(*) FROM source_manifest').fetchone()[0];conn.close()
    status='OK' if integrity=='ok' and stable_counts.get('competitions')==16 and leakage_violations==0 else 'WARN';payload={'run_at_utc':built,'status':status,'schema_version':SCHEMA_VERSION,'db_path':str(OUT),'db_bytes':OUT.stat().st_size,'db_sha256':file_sha(OUT),'integrity_check':integrity,'tables':len(tables),'manifest_sources':manifest_rows,'stable_counts':stable_counts,'missing_stable_sources':missing,'historical_leakage_violations':leakage_violations,'api_calls':0};META.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');SCHEMA.write_text(json.dumps({'schema_version':SCHEMA_VERSION,'stable_tables':list(CORE_ALIASES)+['current_round_leagues','current_round_matches','standings_snapshots','fixture_motivation','formation_research_events'],'json_state_documents':JSON_DOCS,'raw_csv_policy':'every ops/*.csv is imported as raw_<filename_stem> with TEXT columns'},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(payload,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
