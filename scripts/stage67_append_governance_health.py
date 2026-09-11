#!/usr/bin/env python3
"""Append Stage68-72 governance/data-layer checks to Stage67 health output."""
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
    ('Stage72 unified data layer','stage72_last_run.json',3.0),
]

def parse(v):
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).astimezone(timezone.utc)
    except:return None

def main():
    if not H.exists(): return
    now=datetime.now(timezone.utc).replace(microsecond=0)
    d=json.loads(H.read_text(encoding='utf-8-sig'))
    existing={x.get('file') for x in d.get('stage_health',[])}
    issues=d.setdefault('issues',[]); sh=d.setdefault('stage_health',[])
    stage_payloads={}
    for label,name,limit in CHECKS:
        if name in existing: continue
        p=OPS/name
        if not p.exists():
            sh.append({'stage':label,'file':name,'status':'MISSING','run_at_utc':None,'age_h':None,'max_age_h':limit})
            issues.append({'severity':'CRITICAL','code':'MISSING_STAGE_META','message':f'{label}: missing {name}'})
            continue
        try: x=json.loads(p.read_text(encoding='utf-8-sig')); stage_payloads[name]=x
        except Exception:
            sh.append({'stage':label,'file':name,'status':'INVALID','run_at_utc':None,'age_h':None,'max_age_h':limit})
            issues.append({'severity':'CRITICAL','code':'INVALID_STAGE_META','message':f'{label}: unreadable JSON {name}'})
            continue
        rt=parse(x.get('run_at_utc') or x.get('generated_at_utc'))
        age=(now-rt).total_seconds()/3600 if rt else None
        status='OK'
        if rt is None:
            status='NO_TIMESTAMP'; issues.append({'severity':'WARN','code':'NO_RUN_TIMESTAMP','message':f'{label}: cannot determine run timestamp'})
        elif age>limit:
            status='STALE'; sev='CRITICAL' if age>2*limit else 'WARN'; issues.append({'severity':sev,'code':'STALE_STAGE','message':f'{label}: age {age:.2f}h > {limit:.2f}h'})
        sh.append({'stage':label,'file':name,'status':status,'run_at_utc':rt.isoformat().replace('+00:00','Z') if rt else None,'age_h':round(age,3) if age is not None else None,'max_age_h':limit})

    # Stage72 semantic integrity: freshness alone is not enough for the future UI/API layer.
    s72=stage_payloads.get('stage72_last_run.json')
    if s72 is None and (OPS/'stage72_last_run.json').exists():
        try:s72=json.loads((OPS/'stage72_last_run.json').read_text(encoding='utf-8-sig'))
        except:s72=None
    if s72:
        if str(s72.get('integrity_check') or '').lower()!='ok':
            issues.append({'severity':'CRITICAL','code':'STAGE72_SQLITE_INTEGRITY','message':f"Stage72 SQLite integrity_check={s72.get('integrity_check')}"})
        competitions=int((s72.get('stable_counts') or {}).get('competitions') or 0)
        if competitions!=16:
            issues.append({'severity':'CRITICAL','code':'STAGE72_SCOPE_MISMATCH','message':f'Stage72 competitions={competitions}, expected locked scope=16'})
        missing=s72.get('missing_stable_sources') or []
        if missing:
            issues.append({'severity':'CRITICAL','code':'STAGE72_MISSING_STABLE_SOURCE','message':'Stage72 missing stable sources: '+', '.join(map(str,missing))})
        d.setdefault('summary',{})['stage72_integrity']=s72.get('integrity_check')
        d['summary']['stage72_tables']=s72.get('tables')
        d['summary']['stage72_schema_version']=s72.get('schema_version')

    critical=sum(1 for z in issues if z.get('severity')=='CRITICAL'); warns=sum(1 for z in issues if z.get('severity')=='WARN')
    overall='CRITICAL' if critical else ('WARN' if warns else 'HEALTHY')
    d['status']=overall; d.setdefault('summary',{})['critical_issues']=critical; d['summary']['warnings']=warns
    H.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    icon={'HEALTHY':'🟢','WARN':'🟠','CRITICAL':'🔴'}[overall]
    out=['# PBK System Health','',f"Обновлено UTC: {d.get('generated_at_utc','')}",f"Статус: {icon} **{overall}** | critical {critical} | warnings {warns}",'','## Ключевые проверки']
    s=d.get('summary',{}); total=s.get('active_canonical_rows',0)
    out += [f"- Активные canonical: {total}",f"- Frozen Marathonbet execution: {s.get('frozen_user_execution_rows',0)}/{total}",f"- Context coverage: {s.get('active_rows_with_context',0)}/{total}",f"- WATCH crossings накоплено: {s.get('watch_crossing_rows',0)}",f"- Stage72 Data Layer: integrity **{s.get('stage72_integrity','N/A')}** | tables {s.get('stage72_tables','N/A')} | schema v{s.get('stage72_schema_version','N/A')}",'','## Свежесть этапов']
    for z in sh:
        age='N/A' if z.get('age_h') is None else f"{z['age_h']:.2f}h"
        out.append(f"- {z.get('stage')}: **{z.get('status')}** | age {age} | limit {z.get('max_age_h')}h")
    out += ['','## Проблемы']
    if not issues: out.append('- Нет. Все проверяемые контуры выглядят согласованно.')
    else:
        for z in issues: out.append(f"- **{z.get('severity')}** `{z.get('code')}` — {z.get('message')}")
    out += ['','> Stage67 ничего не чинит автоматически и не создаёт ставки. Он только обнаруживает проблемы данных/свежести.']
    M.write_text('\n'.join(out),encoding='utf-8')
    meta=json.loads(META.read_text(encoding='utf-8-sig')) if META.exists() else {}
    meta.update({'system_health':overall,'critical_issues':critical,'warnings':warns,'stage72_integrity':s.get('stage72_integrity')})
    META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__': main()
