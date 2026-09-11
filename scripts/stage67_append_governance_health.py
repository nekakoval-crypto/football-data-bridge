#!/usr/bin/env python3
"""Append Stage68-73 governance/data-layer/API checks to Stage67 health output."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import os

OPS=Path(os.getenv('OPS_DIR','ops'))
H=OPS/'system_health.json'; M=OPS/'system_health.md'; META=OPS/'stage67_last_run.json'
CHECKS=[
    ('Stage68 exposure map','stage68_last_run.json',3.0),
    ('Stage69 promotion gate','stage69_last_run.json',3.0),
    ('Stage70 signal lifecycle','stage70_last_run.json',3.0),
    ('Stage71 league/market challenger','stage71_last_run.json',15.0),
    ('Stage71C team totals capture','stage71c_last_run.json',3.0),
    ('Stage72 unified data layer','stage72_last_run.json',3.0),
    ('Stage73 internal API','stage73_last_run.json',3.0),
]

def parse(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None

def load_json(name):
    p=OPS/name
    if not p.exists():return None
    try:return json.loads(p.read_text(encoding='utf-8-sig'))
    except:return None

def main():
    if not H.exists(): return
    now=datetime.now(timezone.utc).replace(microsecond=0)
    d=json.loads(H.read_text(encoding='utf-8-sig'))
    existing={x.get('file') for x in d.get('stage_health',[])}
    issues=d.setdefault('issues',[]); sh=d.setdefault('stage_health',[]); stage_payloads={}
    for label,name,limit in CHECKS:
        if name in existing: continue
        p=OPS/name
        if not p.exists():
            sh.append({'stage':label,'file':name,'status':'MISSING','run_at_utc':None,'age_h':None,'max_age_h':limit})
            issues.append({'severity':'CRITICAL','code':'MISSING_STAGE_META','message':f'{label}: missing {name}'})
            continue
        x=load_json(name)
        if x is None:
            sh.append({'stage':label,'file':name,'status':'INVALID','run_at_utc':None,'age_h':None,'max_age_h':limit})
            issues.append({'severity':'CRITICAL','code':'INVALID_STAGE_META','message':f'{label}: unreadable JSON {name}'})
            continue
        stage_payloads[name]=x; rt=parse(x.get('run_at_utc') or x.get('generated_at_utc')); age=(now-rt).total_seconds()/3600 if rt else None; status='OK'
        if rt is None:
            status='NO_TIMESTAMP'; issues.append({'severity':'WARN','code':'NO_RUN_TIMESTAMP','message':f'{label}: cannot determine run timestamp'})
        elif age>limit:
            status='STALE'; sev='CRITICAL' if age>2*limit else 'WARN'; issues.append({'severity':sev,'code':'STALE_STAGE','message':f'{label}: age {age:.2f}h > {limit:.2f}h'})
        sh.append({'stage':label,'file':name,'status':status,'run_at_utc':rt.isoformat().replace('+00:00','Z') if rt else None,'age_h':round(age,3) if age is not None else None,'max_age_h':limit})

    s71c=stage_payloads.get('stage71c_last_run.json') or load_json('stage71c_last_run.json')
    if s71c:
        if int(s71c.get('home_team_total_bet_id') or 0)!=16 or int(s71c.get('away_team_total_bet_id') or 0)!=17:
            issues.append({'severity':'CRITICAL','code':'STAGE71C_WRONG_MARKET','message':f"Stage71C bet ids H={s71c.get('home_team_total_bet_id')} A={s71c.get('away_team_total_bet_id')}, expected 16/17"})
        if int(s71c.get('signals_created') or 0)!=0:
            issues.append({'severity':'CRITICAL','code':'STAGE71C_SIGNAL_LEAK','message':'Stage71C raw capture must create zero betting signals'})
        if int(s71c.get('total_openers') or 0)<=0:
            issues.append({'severity':'WARN','code':'STAGE71C_NO_OPENERS','message':'Stage71C has no captured team-total openers yet'})
        d.setdefault('summary',{})['stage71c_team_total_openers']=s71c.get('total_openers')
        d['summary']['stage71c_team_total_snapshots']=s71c.get('total_snapshots')

    s72=stage_payloads.get('stage72_last_run.json') or load_json('stage72_last_run.json')
    if s72:
        if str(s72.get('integrity_check') or '').lower()!='ok':issues.append({'severity':'CRITICAL','code':'STAGE72_SQLITE_INTEGRITY','message':f"Stage72 SQLite integrity_check={s72.get('integrity_check')}"})
        counts=s72.get('stable_counts') or {}; competitions=int(counts.get('competitions') or 0)
        if competitions!=16:issues.append({'severity':'CRITICAL','code':'STAGE72_SCOPE_MISMATCH','message':f'Stage72 competitions={competitions}, expected locked scope=16'})
        if int(counts.get('team_total_openers') or 0)<=0:issues.append({'severity':'CRITICAL','code':'STAGE72_TEAM_TOTALS_MISSING','message':'Stage72 stable team_total_openers is empty'})
        missing=s72.get('missing_stable_sources') or []
        if missing:issues.append({'severity':'CRITICAL','code':'STAGE72_MISSING_STABLE_SOURCE','message':'Stage72 missing stable sources: '+', '.join(map(str,missing))})
        d.setdefault('summary',{})['stage72_integrity']=s72.get('integrity_check');d['summary']['stage72_tables']=s72.get('tables');d['summary']['stage72_schema_version']=s72.get('schema_version')

    s73=stage_payloads.get('stage73_last_run.json') or load_json('stage73_last_run.json')
    if s73:
        passed=int(s73.get('passed') or 0);total=int(s73.get('total') or 0)
        if str(s73.get('status') or '').upper()!='OK' or not total or passed!=total:issues.append({'severity':'CRITICAL','code':'STAGE73_API_CONTRACT','message':f'Stage73 API self-test {passed}/{total}, status={s73.get("status")}'})
        d.setdefault('summary',{})['stage73_api_tests']=f'{passed}/{total}';d['summary']['stage73_api_version']=s73.get('api_version')

    critical=sum(1 for z in issues if z.get('severity')=='CRITICAL');warns=sum(1 for z in issues if z.get('severity')=='WARN');overall='CRITICAL' if critical else ('WARN' if warns else 'HEALTHY')
    d['status']=overall;d.setdefault('summary',{})['critical_issues']=critical;d['summary']['warnings']=warns
    H.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    icon={'HEALTHY':'🟢','WARN':'🟠','CRITICAL':'🔴'}[overall];s=d.get('summary',{});total_active=s.get('active_canonical_rows',0)
    out=['# PBK System Health','',f"Обновлено UTC: {d.get('generated_at_utc','')}",f"Статус: {icon} **{overall}** | critical {critical} | warnings {warns}",'','## Ключевые проверки',f"- Активные canonical: {total_active}",f"- Frozen Marathonbet execution: {s.get('frozen_user_execution_rows',0)}/{total_active}",f"- Context coverage: {s.get('active_rows_with_context',0)}/{total_active}",f"- WATCH crossings накоплено: {s.get('watch_crossing_rows',0)}",f"- Team Totals capture: openers {s.get('stage71c_team_total_openers','N/A')} | snapshots {s.get('stage71c_team_total_snapshots','N/A')}",f"- Stage72 Data Layer: integrity **{s.get('stage72_integrity','N/A')}** | tables {s.get('stage72_tables','N/A')} | schema v{s.get('stage72_schema_version','N/A')}",f"- Stage73 Internal API: tests **{s.get('stage73_api_tests','N/A')}** | API {s.get('stage73_api_version','N/A')}",'','## Свежесть этапов']
    for z in sh:
        age='N/A' if z.get('age_h') is None else f"{z['age_h']:.2f}h";out.append(f"- {z.get('stage')}: **{z.get('status')}** | age {age} | limit {z.get('max_age_h')}h")
    out += ['','## Проблемы']
    if not issues:out.append('- Нет. Все проверяемые контуры выглядят согласованно.')
    else:
        for z in issues:out.append(f"- **{z.get('severity')}** `{z.get('code')}` — {z.get('message')}")
    out += ['','> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.']
    M.write_text('\n'.join(out),encoding='utf-8')
    meta=json.loads(META.read_text(encoding='utf-8-sig')) if META.exists() else {};meta.update({'system_health':overall,'critical_issues':critical,'warnings':warns,'stage71c_team_total_openers':s.get('stage71c_team_total_openers'),'stage72_integrity':s.get('stage72_integrity'),'stage73_api_tests':s.get('stage73_api_tests')});META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
