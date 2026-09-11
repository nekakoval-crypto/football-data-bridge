#!/usr/bin/env python3
"""Apply the preregistered Stage71 regime-change discovery path to the board."""
from __future__ import annotations
import csv, json, math, os
from collections import defaultdict
from pathlib import Path

OPS=Path(os.getenv("OPS_DIR","ops"))
BOARD=OPS/"stage71_challenger_board.csv"
FORWARD=OPS/"stage71_challenger_forward.csv"
OUT_JSON=OPS/"stage71_challenger_board.json"
OUT_MD=OPS/"stage71_challenger_board.md"
META=OPS/"stage71_last_run.json"

def read_csv(p):
    if not p.exists():return []
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def fnum(v):
    try:
        x=float(str(v).strip());return x if math.isfinite(x) else None
    except:return None
def roi(rows):
    vals=[fnum(r.get("user_profit_u")) for r in rows];vals=[x for x in vals if x is not None]
    return 100*sum(vals)/len(vals) if vals else None
def metrics(rows):
    priced=[r for r in rows if fnum(r.get("user_odds")) is not None]
    settled=[r for r in priced if r.get("status")=="SETTLED" and fnum(r.get("user_profit_u")) is not None]
    settled.sort(key=lambda r:(r.get("kickoff_utc") or "",r.get("research_id") or ""))
    c=len(settled)//2
    return {"rows":len(rows),"settled":len(settled),"coverage":100*len(priced)/len(rows) if rows else None,
            "roi":roi(settled),"first":roi(settled[:c]),"second":roi(settled[c:])}
def fmt(v):return "—" if v in (None,"") else str(v)

def main():
    rows=read_csv(BOARD); fwd=read_csv(FORWARD); by=defaultdict(list)
    for r in fwd:by[(r.get("family"),r.get("league"))].append(r)
    changed=0
    for r in rows:
        if r.get("status") in {"ACTIVE","DEGRADATION_REVIEW","SUSPENSION_REVIEW","REVIEW_ELIGIBLE","CHALLENGER"}:continue
        m=metrics(by.get((r.get("family"),r.get("league")),[]))
        r["prospective_settled"]=str(m["settled"])
        r["prospective_roi_pct"]="" if m["roi"] is None else f"{m['roi']:.3f}"
        r["prospective_first_half_roi_pct"]="" if m["first"] is None else f"{m['first']:.3f}"
        r["prospective_second_half_roi_pct"]="" if m["second"] is None else f"{m['second']:.3f}"
        r["marathonbet_coverage_pct"]="" if m["coverage"] is None else f"{m['coverage']:.3f}"
        eligible=(m["settled"]>=120 and (m["coverage"] or 0)>=90 and (m["roi"] or 0)>0 and (m["first"] or 0)>0 and (m["second"] or 0)>0)
        old=r.get("status")
        if eligible:
            r["status"]="REGIME_DISCOVERY_ELIGIBLE"
            r["blocking_reason"]="requires new preregistration and a fresh future holdout; discovery sample cannot be reused"
        elif m["rows"]>0:
            r["status"]="MONITORING"
            r["blocking_reason"]=f"fresh discovery sample {m['settled']}/120 settled; no direct promotion"
        if r.get("status")!=old:changed+=1
    if rows:
        fields=list(rows[0].keys())
        with BOARD.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    payload=json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {}
    payload["rows"]=rows;payload["regime_discovery_policy"]={"min_settled":120,"min_marathonbet_coverage_pct":90,"roi_positive":True,"both_chronological_halves_positive":True,"direct_promotion":"FORBIDDEN","fresh_holdout_required":True}
    payload["regime_discovery_eligible"]=sum(1 for r in rows if r.get("status")=="REGIME_DISCOVERY_ELIGIBLE")
    OUT_JSON.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    leaders={fam:next((r.get("league") for r in rows if r.get("family")==fam and r.get("leader")=="YES"),"нет") for fam in ("R1","R2")}
    md=["# PBK Stage71 — League & Market Challenger Board","",f"Scope: 16 лиг | текущие лидеры R1/R2: {leaders['R1']} / {leaders['R2']}","","> Лидер — описательный статус. Никакого автоматического promotion/suspension.",""]
    for fam in ("R1","R2"):
        md += [f"## {fam} | текущий лидер: **{leaders[fam]}**","","| Лига | Статус | TRAIN ROI | TEST ROI | Forward settled | Forward ROI |","|---|---|---:|---:|---:|---:|"]
        for r in [x for x in rows if x.get("family")==fam]:
            star=" 🏆" if r.get("leader")=="YES" else ""
            md.append(f"| {r.get('league')}{star} | {r.get('status')} | {fmt(r.get('train_roi_pct'))} | {fmt(r.get('test_roi_pct'))} | {fmt(r.get('prospective_settled'))} | {fmt(r.get('prospective_roi_pct'))} |")
        md.append("")
    md += ["## Regime-change path","- 120 fresh settled executable bets + >=90% Marathonbet coverage + positive total ROI + positive both chronological halves => REGIME_DISCOVERY_ELIGIBLE.","- Затем обязательна новая preregistration и **новый будущий holdout**. Эти 120 ставок повторно использовать нельзя."]
    OUT_MD.write_text("\n".join(md),encoding="utf-8")
    if META.exists():
        meta=json.loads(META.read_text(encoding="utf-8"));meta["regime_discovery_eligible"]=payload["regime_discovery_eligible"];meta["regime_overlay_status_changes"]=changed;META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"regime_discovery_eligible":payload["regime_discovery_eligible"],"status_changes":changed}))
if __name__=="__main__":main()
