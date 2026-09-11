#!/usr/bin/env python3
"""Append Stage67-69 governance summary to the Stage66 attention board."""
from __future__ import annotations
import json, os
from pathlib import Path

OPS=Path(os.getenv('OPS_DIR','ops'))
BOARD_JSON=OPS/'attention_board.json'; BOARD_MD=OPS/'attention_board.md'

def load(name):
    p=OPS/name
    if not p.exists(): return {}
    try:return json.loads(p.read_text(encoding='utf-8-sig'))
    except:return {}

def main():
    if not BOARD_JSON.exists(): return
    b=json.loads(BOARD_JSON.read_text(encoding='utf-8-sig'))
    health=load('system_health.json')
    exp=load('exposure_summary.json')
    gate=load('watch_promotion_gate.json')
    gov={
        'system_health': health.get('status','UNKNOWN'),
        'health_critical': (health.get('summary') or {}).get('critical_issues'),
        'health_warnings': (health.get('summary') or {}).get('warnings'),
        'logical_exposure_u': exp.get('logical_exposure_u'),
        'canonical_conflict_fixtures': exp.get('canonical_conflict_fixtures'),
        'deduplicated_overlap_u': exp.get('deduplicated_overlap_u'),
        'stage61_gate': ((gate.get('families') or {}).get('Stage61') or {}).get('status','UNKNOWN'),
        'stage62_gate': ((gate.get('families') or {}).get('Stage62') or {}).get('status','UNKNOWN'),
        'stage63_gate': ((gate.get('families') or {}).get('Stage63') or {}).get('status','UNKNOWN'),
    }
    b['governance']=gov
    BOARD_JSON.write_text(json.dumps(b,ensure_ascii=False,indent=2),encoding='utf-8')

    md=BOARD_MD.read_text(encoding='utf-8-sig') if BOARD_MD.exists() else '# PBK — Что требует внимания сейчас\n'
    md += '\n\n---\n\n## 🛡️ Состояние системы / governance\n'
    md += f"- System Health: **{gov['system_health']}** | critical {gov['health_critical']} | warnings {gov['health_warnings']}\n"
    md += f"- Логическая canonical экспозиция: **{gov['logical_exposure_u']}u** | конфликтов матчей {gov['canonical_conflict_fixtures']} | убрано дублей {gov['deduplicated_overlap_u']}u\n"
    md += f"- Promotion Gate: Stage61 **{gov['stage61_gate']}** | Stage62 **{gov['stage62_gate']}** | Stage63 **{gov['stage63_gate']}**\n"
    if (gov['canonical_conflict_fixtures'] or 0)>0:
        md += '- ⚠️ Есть canonical-конфликт: требуется manual review до любого увеличения экспозиции.\n'
    if gov['system_health']=='CRITICAL':
        md += '- 🔴 Есть критическая проблема данных: operational вывод нельзя считать полностью надёжным до разбора.\n'
    if 'REVIEW_ELIGIBLE' in {gov['stage61_gate'],gov['stage62_gate'],gov['stage63_gate']}:
        md += '- 🟡 Один из WATCH дошёл до REVIEW_ELIGIBLE: это повод для отдельного locked review, не автоматическая ставка.\n'
    BOARD_MD.write_text(md,encoding='utf-8')

if __name__=='__main__': main()
