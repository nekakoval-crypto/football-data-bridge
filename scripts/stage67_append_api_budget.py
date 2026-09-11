#!/usr/bin/env python3
"""Append Stage71J API-Football budget checks to Stage67 health.

Read-only QA. Makes zero external API calls.
"""
from __future__ import annotations
import json, os
from pathlib import Path

OPS=Path(os.getenv('OPS_DIR','ops'))
HEALTH=OPS/'system_health.json';META=OPS/'stage67_last_run.json';MD=OPS/'system_health.md';J=OPS/'stage71j_last_run.json'
BUDGET=190

def read(p):
    try:return json.loads(p.read_text(encoding='utf-8-sig'))
    except Exception:return {}

def main():
    h=read(HEALTH);m=read(META);j=read(J)
    calls=int(j.get('real_api_calls') or 0);children=j.get('children') or []
    child_warnings=sum(int(x.get('warnings') or 0) for x in children if isinstance(x,dict))
    child_bad=[str(x.get('market_family')) for x in children if isinstance(x,dict) and str(x.get('status') or '').upper() not in {'OK','SUCCESS'}]
    issues=h.setdefault('issues',[])
    if not j:
        issues.append({'severity':'WARN','code':'API_BUDGET_META_MISSING','message':'Stage71J budget metadata missing'})
    if calls>BUDGET:
        issues.append({'severity':'CRITICAL','code':'API_BUDGET_OVERRUN','message':f'Stage71J real API calls {calls} > hard health budget {BUDGET}'})
    if child_warnings:
        issues.append({'severity':'WARN','code':'SHARED_MARKET_CAPTURE_WARNINGS','message':f'Stage71J child warnings={child_warnings}'})
    if child_bad:
        issues.append({'severity':'WARN','code':'SHARED_MARKET_CAPTURE_STATUS','message':'Stage71J non-OK children: '+', '.join(child_bad)})
    critical=sum(1 for x in issues if x.get('severity')=='CRITICAL');warns=sum(1 for x in issues if x.get('severity')=='WARN')
    overall='CRITICAL' if critical else ('WARN' if warns else 'HEALTHY')
    h['status']=overall;h.setdefault('summary',{}).update({'critical_issues':critical,'warnings':warns,'stage71j_real_api_calls':calls,'stage71j_api_budget':BUDGET,'stage71j_cache_hits':int(j.get('cache_hits') or 0),'stage71j_child_warnings':child_warnings})
    h.setdefault('policy',{})['api_budget_guard']='Stage71J >190 real calls/run = CRITICAL; child warnings = WARN'
    HEALTH.write_text(json.dumps(h,ensure_ascii=False,indent=2),encoding='utf-8')
    m.update({'system_health':overall,'critical_issues':critical,'warnings':warns,'stage71j_real_api_calls':calls,'stage71j_api_budget':BUDGET,'stage71j_cache_hits':int(j.get('cache_hits') or 0),'stage71j_child_warnings':child_warnings})
    META.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
    text=MD.read_text(encoding='utf-8-sig') if MD.exists() else ''
    text += f"\n\n## API-Football budget guard\n- Stage71J real calls: **{calls}/{BUDGET} per run**\n- Shared-cache hits: **{int(j.get('cache_hits') or 0)}**\n- Child warnings: **{child_warnings}**\n- Budget status: **{'OK' if calls<=BUDGET and not child_warnings else 'REVIEW'}**\n"
    MD.write_text(text,encoding='utf-8')
    print(json.dumps({'stage71j_real_api_calls':calls,'budget':BUDGET,'cache_hits':int(j.get('cache_hits') or 0),'child_warnings':child_warnings,'health':overall},ensure_ascii=False))

if __name__=='__main__':main()
