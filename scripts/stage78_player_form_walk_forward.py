#!/usr/bin/env python3
from __future__ import annotations
import csv,json,os
from collections import defaultdict
from pathlib import Path
from statistics import mean

OPS=Path(os.getenv("OPS_DIR","ops"))
GRADES=OPS/"player_grade_snapshots.csv"
HISTORY=OPS/"pbk16_all_competition_fixture_history.csv"
OUT=OPS/"player_form_walk_forward.csv"
META=OPS/"stage78_player_form_walk_forward_last_run.json"
VERSION="PBK_STAGE78_PLAYER_FORM_WALK_FORWARD_V1"
FIELDS=["fixture_id","kickoff_utc","country","competition_name","season","team_id","team_name","side","player_id","player_name","position_group","sample_3","form_3","sample_5","form_5","sample_10","form_10","season_sample","season_mean","last_grade","trend_3_vs_10","deviation_last_vs_season","team_points","team_goal_diff","team_result","prior_rows_max_kickoff_utc","prior_rows_max_observed_at_utc","no_lookahead","research_only","creates_signal","probability_mutation","eligibility_mutation","stake_changes","forward_journal_mutation"]

def read_csv(path):
    if not path.exists(): return []
    with path.open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))

def num(v):
    try:return float(v) if v not in (None,"") else None
    except:return None

def avg(rows,n):
    vals=[num(r.get("overall_grade")) for r in rows[:n]]
    vals=[v for v in vals if v is not None]
    return len(vals),(round(mean(vals),4) if vals else None)

def outcome(fx,team_id):
    hg,ag=num(fx.get("home_goals")),num(fx.get("away_goals"))
    if hg is None or ag is None:return None
    tid=str(team_id or "")
    if tid==str(fx.get("home_team_id") or ""):gf,ga,side,name=hg,ag,"HOME",fx.get("home_team")
    elif tid==str(fx.get("away_team_id") or ""):gf,ga,side,name=ag,hg,"AWAY",fx.get("away_team")
    else:return None
    return {"points":3 if gf>ga else (1 if gf==ga else 0),"goal_diff":gf-ga,"result":"W" if gf>ga else ("D" if gf==ga else "L"),"side":side,"team_name":name}

def build(grades,fixtures):
    fx={str(r.get("fixture_id") or ""):r for r in fixtures if r.get("fixture_id")}
    groups=defaultdict(list); joined=0; skipped_no_fixture=0
    for r in grades:
        f=fx.get(str(r.get("fixture_id") or ""))
        if not f: skipped_no_fixture+=1; continue
        pid=str(r.get("player_id") or ""); season=str(f.get("season") or "")
        if not pid or not season: continue
        x=dict(r);x["_fx"]=f;groups[(pid,season)].append(x);joined+=1
    out=[];leakage=0;skipped_no_side=0
    for rows in groups.values():
        rows.sort(key=lambda r:(str(r.get("kickoff_utc") or ""),str(r.get("fixture_id") or "")))
        for i,target in enumerate(rows):
            f=target["_fx"];tk=str(target.get("kickoff_utc") or f.get("kickoff_utc") or "")
            if not tk:continue
            oc=outcome(f,target.get("team_id"))
            if not oc: skipped_no_side+=1; continue
            prior=[r for r in rows[:i] if str(r.get("kickoff_utc") or "")<tk and (not str(r.get("observed_at_utc") or "") or str(r.get("observed_at_utc") or "")<=tk) and num(r.get("overall_grade")) is not None]
            prior.sort(key=lambda r:str(r.get("kickoff_utc") or ""),reverse=True)
            if any(str(r.get("kickoff_utc") or "")>=tk or (str(r.get("observed_at_utc") or "") and str(r.get("observed_at_utc") or "")>tk) for r in prior): leakage+=1; continue
            s3,f3=avg(prior,3);s5,f5=avg(prior,5);s10,f10=avg(prior,10)
            sv=[num(r.get("overall_grade")) for r in prior if num(r.get("overall_grade")) is not None]
            sm=round(mean(sv),4) if sv else None;lg=num(prior[0].get("overall_grade")) if prior else None
            out.append({"fixture_id":target.get("fixture_id"),"kickoff_utc":tk,"country":f.get("country"),"competition_name":f.get("competition_name"),"season":f.get("season"),"team_id":target.get("team_id"),"team_name":oc["team_name"],"side":oc["side"],"player_id":target.get("player_id"),"player_name":target.get("player_name"),"position_group":target.get("position_group"),"sample_3":s3,"form_3":f3,"sample_5":s5,"form_5":f5,"sample_10":s10,"form_10":f10,"season_sample":len(sv),"season_mean":sm,"last_grade":lg,"trend_3_vs_10":round(f3-f10,4) if s3>=3 and s10>=10 else None,"deviation_last_vs_season":round(lg-sm,4) if lg is not None and sm is not None else None,"team_points":oc["points"],"team_goal_diff":round(oc["goal_diff"],4),"team_result":oc["result"],"prior_rows_max_kickoff_utc":max((str(r.get("kickoff_utc") or "") for r in prior),default=""),"prior_rows_max_observed_at_utc":max((str(r.get("observed_at_utc") or "") for r in prior),default=""),"no_lookahead":"true","research_only":"true","creates_signal":"false","probability_mutation":"false","eligibility_mutation":"false","stake_changes":"false","forward_journal_mutation":"false"})
    meta={"version":VERSION,"grade_rows":len(grades),"joined_grade_rows":joined,"output_rows":len(out),"form3_full_window_rows":sum(int(r["sample_3"])>=3 for r in out),"form5_full_window_rows":sum(int(r["sample_5"])>=5 for r in out),"form10_full_window_rows":sum(int(r["sample_10"])>=10 for r in out),"leakage_violations":leakage,"skipped_no_fixture":skipped_no_fixture,"skipped_no_team_side":skipped_no_side,"provider_calls":0,"research_only":True,"no_lookahead":True,"creates_signal":False,"probability_mutation":False,"eligibility_mutation":False,"stake_changes":False,"forward_journal_mutation":False}
    return out,meta

def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction="ignore");w.writeheader();w.writerows(rows)
    tmp.replace(path)

def main():
    rows,meta=build(read_csv(GRADES),read_csv(HISTORY));write_csv(OUT,rows);META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
