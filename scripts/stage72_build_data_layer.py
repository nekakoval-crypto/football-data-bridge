#!/usr/bin/env python3
"""Stage 72 — deterministic PBK unified SQLite data layer.

CSV/JSON operational files remain the audit/source-of-truth during migration.
This script builds a disposable, reproducible SQLite database for Stage73/API
and future PC/Android clients. No API calls and no mutation of source ledgers.
"""
from __future__ import annotations
import csv, json, os, re, sqlite3, hashlib
from datetime import datetime, timezone
from pathlib import Path

OPS=Path(os.getenv('OPS_DIR','ops'))
OUT=Path(os.getenv('STAGE72_DB_PATH','build/pbk_unified.sqlite'))
META=OPS/'stage72_last_run.json';SCHEMA=OPS/'stage72_schema.json';SCHEMA_VERSION='5'
CORE_ALIASES={
    'competitions':'stage71_league_catalog.csv','canonical_signals':'user_forward_view.csv','challenger_signals':'stage71_challenger_forward.csv','watch_signals':'stage65_watch_ledger.csv','lifecycle_events':'signal_lifecycle_events.csv','exposure_positions':'exposure_map.csv','context_latest':'context_latest.csv','odds_snapshots':'odds_snapshots.csv',
    'team_total_openers':'stage71c_team_total_openers.csv','team_total_snapshots':'stage71c_team_total_snapshots.csv','team_total_closes':'stage71c_team_total_closes.csv',
    'double_chance_openers':'stage71e_double_chance_openers.csv','double_chance_snapshots':'stage71e_double_chance_snapshots.csv','double_chance_closes':'stage71e_double_chance_closes.csv',
    'european_handicap_openers':'stage71f_eh_openers.csv','european_handicap_snapshots':'stage71f_eh_snapshots.csv','european_handicap_closes':'stage71f_eh_closes.csv',
    'dnb_openers':'stage71g_dnb_openers.csv','dnb_snapshots':'stage71g_dnb_snapshots.csv','dnb_closes':'stage71g_dnb_closes.csv',
}
JSON_DOCS=['attention_board.json','daily_brief.json','forward_performance.json','watch_performance.json','watch_promotion_gate.json','system_health.json','exposure_summary.json','stage71_challenger_board.json','signal_lifecycle_cards.json','stage71b_fonbet_coverage.json','stage71c_last_run.json','stage71e_last_run.json','stage71f_last_run.json','stage71g_last_run.json']
def now_iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
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
    conn.execute(f'CREATE TABLE "{table}" ({", ".join([f"\"{c}\" TEXT" for c in cols])})');q=f'INSERT INTO "{table}" ({", ".join([f"\"{c}\"" for c in cols])}) VALUES ({", ".join(["?"]*len(cols))})';conn.executemany(q,[[r.get(orig,'') for orig,col in mapping] for r in rows])
    for candidate in ('api_fixture_id','fixture_id','forward_id','research_id','watch_id','signal_id','market_key','kickoff_utc','league','family','rule','status','team_side','line','home_handicap_line'):
        if candidate in cols:
            try:conn.execute(f'CREATE INDEX "idx_{table}_{candidate}" ON "{table}" ("{candidate}")')
            except sqlite3.OperationalError:pass
    return len(rows),cols
def file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
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
    conn.execute('CREATE TABLE state_documents (name TEXT PRIMARY KEY, payload_json TEXT NOT NULL, sha256 TEXT NOT NULL)')
    for name in JSON_DOCS:
        p=OPS/name
        if not p.exists():continue
        raw=p.read_text(encoding='utf-8-sig')
        try:json.loads(raw)
        except Exception:continue
        conn.execute('INSERT INTO state_documents VALUES (?,?,?)',(name,raw,file_sha(p)));conn.execute('INSERT OR REPLACE INTO source_manifest VALUES (?,?,?,?)',(name,'json',1,file_sha(p)))
    meta={'schema_version':SCHEMA_VERSION,'built_at_utc':built,'source_policy':'ops CSV/JSON remain audit source; SQLite is reproducible projection'};conn.executemany('INSERT INTO pbk_meta VALUES (?,?)',meta.items());conn.commit();integrity=conn.execute('PRAGMA integrity_check').fetchone()[0];tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")];manifest_rows=conn.execute('SELECT COUNT(*) FROM source_manifest').fetchone()[0];conn.close()
    status='OK' if integrity=='ok' and stable_counts.get('competitions')==16 else 'WARN';payload={'run_at_utc':built,'status':status,'schema_version':SCHEMA_VERSION,'db_path':str(OUT),'db_bytes':OUT.stat().st_size,'db_sha256':file_sha(OUT),'integrity_check':integrity,'tables':len(tables),'manifest_sources':manifest_rows,'stable_counts':stable_counts,'missing_stable_sources':missing,'api_calls':0};META.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');SCHEMA.write_text(json.dumps({'schema_version':SCHEMA_VERSION,'stable_tables':CORE_ALIASES,'json_state_documents':JSON_DOCS,'raw_csv_policy':'every ops/*.csv is imported as raw_<filename_stem> with TEXT columns'},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(payload,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
