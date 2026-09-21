#!/usr/bin/env python3
"""PBK checklist item 11 — player synergy research foundation.

Provider-free, retrospective, fail-closed.

Builds descriptive pair / trio / positional-line co-start associations from the
same historical official-XI universe used by the Stage80 player layer, plus a
strictly-prior walk-forward feature table for later market-adjusted validation.

This stage DOES NOT claim causal chemistry, predictive probability authority,
value, eligibility or stake authority.  Historical lineups were retrieved
retrospectively, so even strictly-prior chronology remains
RETROSPECTIVE_CHRONOLOGY_ONLY rather than PREMATCH_FROZEN.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

OPS = Path(os.getenv("OPS_DIR", "ops"))
LINEUPS = OPS / "historical_lineup_snapshots.csv"
FIXTURES = OPS / "pbk16_all_competition_fixture_history.csv"

PAIR_OUT = OPS / "player_synergy_pair_research.csv"
TRIO_OUT = OPS / "player_synergy_trio_research.csv"
LINE_OUT = OPS / "player_synergy_line_research.csv"
ANTI_OUT = OPS / "player_anti_synergy_research.csv"
WF_OUT = OPS / "player_synergy_walk_forward.csv"
READINESS_OUT = OPS / "player_synergy_readiness.json"

VERSION = "PBK_PLAYER_SYNERGY_RESEARCH_V1"
PAIR_MIN_SAMPLE = 5
TRIO_MIN_SAMPLE = 4
LINE_MIN_SAMPLE = 4
MIN_MEMBER_BASELINE = 5

COMBO_FIELDS = [
    "team_id","team_name","combo_type","position_group","member_ids","member_names",
    "member_count","co_starts","co_points_mean","co_goal_diff_mean",
    "member_baseline_points_mean","member_baseline_goal_diff_mean",
    "points_delta_vs_member_baseline","goal_diff_delta_vs_member_baseline",
    "eligible","association_direction","anti_synergy_candidate",
    "sample_reason","causal_claim","temporal_authority","research_only",
    "creates_signal","probability_mutation","eligibility_mutation","stake_changes",
]

ANTI_FIELDS = [
    "team_id","team_name","combo_type","position_group","member_ids","member_names",
    "co_starts","points_delta_vs_member_baseline","goal_diff_delta_vs_member_baseline",
    "anti_synergy_candidate","validation_authority","research_only",
]

WF_FIELDS = [
    "fixture_id","kickoff_utc","team_id","team_name","side",
    "pair_candidates","pair_eligible_prior","pair_prior_sample_mean",
    "pair_points_delta_mean","pair_points_delta_min","pair_points_delta_max",
    "trio_candidates","trio_eligible_prior","trio_prior_sample_mean",
    "trio_points_delta_mean","trio_points_delta_min","trio_points_delta_max",
    "line_candidates","line_eligible_prior","line_prior_sample_mean",
    "line_points_delta_mean","line_points_delta_min","line_points_delta_max",
    "anti_pair_prior_count","anti_trio_prior_count","anti_line_prior_count",
    "team_points","team_goal_diff","outcome_known_after_match_only",
    "strictly_prior_combo_history_only","temporal_authority",
    "prematch_observation_time_known","validation_authority","research_only",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def read_csv(path: Path) -> list[dict[str,str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields: list[str], rows: list[dict[str,Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    os.replace(tmp,path)


def write_json(path: Path, payload: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    os.replace(tmp,path)


def sval(row: dict[str,Any], *keys: str) -> str:
    for k in keys:
        v=row.get(k)
        if v not in (None,""):
            return str(v).strip()
    return ""


def fnum(v: Any) -> float|None:
    try:
        n=float(str(v).strip())
    except (TypeError,ValueError):
        return None
    return n if math.isfinite(n) else None


def parse_dt(v: Any) -> datetime|None:
    if not v:
        return None
    try:
        x=datetime.fromisoformat(str(v).replace("Z","+00:00"))
    except (TypeError,ValueError):
        return None
    if x.tzinfo is None:
        return None
    return x.astimezone(timezone.utc)


def parse_xi(value: Any) -> list[dict[str,str]]:
    try:
        raw=json.loads(value) if isinstance(value,str) else value
    except (TypeError,ValueError,json.JSONDecodeError):
        return []
    if not isinstance(raw,list) or len(raw)!=11:
        return []
    out=[]; seen=set()
    for item in raw:
        if not isinstance(item,dict):
            return []
        p=item.get("player") if isinstance(item.get("player"),dict) else item
        pid=str(p.get("id") or p.get("player_id") or "").strip()
        name=str(p.get("name") or p.get("player_name") or "").strip()
        pos=str(p.get("pos") or p.get("position") or "").strip().upper()
        if not pid or pid in seen:
            return []
        seen.add(pid)
        if pos.startswith("GK"): pos="G"
        elif pos.startswith("D"): pos="D"
        elif pos.startswith("M"): pos="M"
        elif pos.startswith("F") or pos.startswith("A"): pos="F"
        elif pos not in {"G","D","M","F"}: pos=""
        out.append({"player_id":pid,"player_name":name,"position_group":pos})
    return out


def fixture_outcomes(rows: list[dict[str,str]]) -> dict[str,dict[str,float]]:
    out={}
    for row in rows:
        fid=sval(row,"fixture_id")
        status=sval(row,"status","latest_status").upper()
        hg=fnum(row.get("home_goals") if row.get("home_goals") not in (None,"") else row.get("final_score_home"))
        ag=fnum(row.get("away_goals") if row.get("away_goals") not in (None,"") else row.get("final_score_away"))
        if not fid or hg is None or ag is None or status not in {"FT","AET","PEN","FINISHED"}:
            continue
        out[fid]={
            "home_points":3 if hg>ag else (1 if hg==ag else 0),
            "away_points":3 if ag>hg else (1 if hg==ag else 0),
            "home_gd":hg-ag,
            "away_gd":ag-hg,
        }
    return out


def historical_team_rows(lineups: list[dict[str,str]], outcomes: dict[str,dict[str,float]]) -> dict[str,list[dict[str,Any]]]:
    by_team=defaultdict(list); seen=set()
    for row in lineups:
        fid=sval(row,"fixture_id")
        tid=sval(row,"team_id")
        side=sval(row,"side").upper()
        kickoff=sval(row,"kickoff_utc")
        xi=parse_xi(row.get("starting_xi_json"))
        if not fid or not tid or side not in {"HOME","AWAY"} or len(xi)!=11 or fid not in outcomes:
            continue
        key=(fid,tid)
        if key in seen: continue
        seen.add(key)
        result=outcomes[fid]
        by_team[tid].append({
            "fixture_id":fid,
            "kickoff_utc":kickoff,
            "kickoff_dt":parse_dt(kickoff),
            "team_id":tid,
            "team_name":sval(row,"team_name"),
            "side":side,
            "formation":sval(row,"formation"),
            "xi":xi,
            "points":result["home_points" if side=="HOME" else "away_points"],
            "gd":result["home_gd" if side=="HOME" else "away_gd"],
        })
    floor=datetime.min.replace(tzinfo=timezone.utc)
    for rows in by_team.values():
        rows.sort(key=lambda r:((r["kickoff_dt"] or floor),r["fixture_id"]))
    return by_team


def combo_key(combo_type: str, members: list[dict[str,str]], position_group: str="") -> tuple[str,str,tuple[str,...]]:
    return combo_type,position_group,tuple(sorted(p["player_id"] for p in members))


def line_combos(xi: list[dict[str,str]]) -> list[tuple[str,list[dict[str,str]]]]:
    groups=defaultdict(list)
    for p in xi:
        if p["position_group"] in {"D","M","F"}:
            groups[p["position_group"]].append(p)
    return [(g,players) for g,players in sorted(groups.items()) if len(players)>=2]


def combinations_for_xi(xi: list[dict[str,str]]) -> list[tuple[str,str,list[dict[str,str]]]]:
    out=[]
    for members in itertools.combinations(xi,2):
        out.append(("PAIR","",list(members)))
    for members in itertools.combinations(xi,3):
        out.append(("TRIO","",list(members)))
    for group,members in line_combos(xi):
        out.append(("LINE",group,list(members)))
    return out


def min_sample(combo_type: str) -> int:
    return {"PAIR":PAIR_MIN_SAMPLE,"TRIO":TRIO_MIN_SAMPLE,"LINE":LINE_MIN_SAMPLE}[combo_type]


def stats_mean(rows: list[tuple[float,float]]) -> tuple[float|None,float|None]:
    if not rows: return None,None
    return mean(x[0] for x in rows), mean(x[1] for x in rows)


def association_from_history(
    team_name: str,
    key: tuple[str,str,tuple[str,...]],
    names: dict[str,str],
    combo_hist: dict[tuple[str,str,tuple[str,...]],list[tuple[float,float]]],
    player_hist: dict[str,list[tuple[float,float]]],
) -> dict[str,Any]:
    ctype,pos,ids=key
    crows=combo_hist.get(key,[])
    co_pts,co_gd=stats_mean(crows)
    member_pts=[]; member_gd=[]; member_ok=True
    for pid in ids:
        rows=player_hist.get(pid,[])
        if len(rows)<MIN_MEMBER_BASELINE:
            member_ok=False
        p,g=stats_mean(rows)
        if p is not None: member_pts.append(p)
        if g is not None: member_gd.append(g)
    base_pts=mean(member_pts) if len(member_pts)==len(ids) else None
    base_gd=mean(member_gd) if len(member_gd)==len(ids) else None
    eligible=len(crows)>=min_sample(ctype) and member_ok and base_pts is not None and base_gd is not None
    pd=(co_pts-base_pts) if eligible and co_pts is not None else None
    gd=(co_gd-base_gd) if eligible and co_gd is not None else None
    if not eligible:
        direction="UNKNOWN"
    elif pd>0 and gd>0:
        direction="POSITIVE"
    elif pd<0 and gd<0:
        direction="NEGATIVE"
    elif abs(pd)<1e-12 and abs(gd)<1e-12:
        direction="NEUTRAL"
    else:
        direction="MIXED"
    anti=bool(eligible and pd<0 and gd<0)
    return {
        "combo_type":ctype,
        "position_group":pos,
        "member_ids":"|".join(ids),
        "member_names":"|".join(names.get(i,i) for i in ids),
        "member_count":len(ids),
        "co_starts":len(crows),
        "co_points_mean":round(co_pts,3) if co_pts is not None else "",
        "co_goal_diff_mean":round(co_gd,3) if co_gd is not None else "",
        "member_baseline_points_mean":round(base_pts,3) if base_pts is not None else "",
        "member_baseline_goal_diff_mean":round(base_gd,3) if base_gd is not None else "",
        "points_delta_vs_member_baseline":round(pd,3) if pd is not None else "",
        "goal_diff_delta_vs_member_baseline":round(gd,3) if gd is not None else "",
        "eligible":"true" if eligible else "false",
        "association_direction":direction,
        "anti_synergy_candidate":"true" if anti else "false",
        "sample_reason":"OK" if eligible else f"INSUFFICIENT_PRIOR_SAMPLE_COMBO_{len(crows)}_MEMBER_MIN_{MIN_MEMBER_BASELINE}",
        "causal_claim":"false",
        "temporal_authority":"RETROSPECTIVE_ONLY",
        "research_only":"true",
        "creates_signal":"false",
        "probability_mutation":"false",
        "eligibility_mutation":"false",
        "stake_changes":"false",
    }


def summary_for_current(
    combo_type: str,
    current_keys: list[tuple[str,str,tuple[str,...]]],
    combo_hist: dict[tuple[str,str,tuple[str,...]],list[tuple[float,float]]],
    player_hist: dict[str,list[tuple[float,float]]],
) -> dict[str,Any]:
    deltas=[]; samples=[]; anti=0
    for key in current_keys:
        crows=combo_hist.get(key,[])
        ids=key[2]
        if len(crows)<min_sample(combo_type):
            continue
        member_means=[]
        ok=True
        for pid in ids:
            rows=player_hist.get(pid,[])
            if len(rows)<MIN_MEMBER_BASELINE:
                ok=False; break
            p,_=stats_mean(rows)
            if p is None: ok=False; break
            member_means.append(p)
        if not ok: continue
        cp,_=stats_mean(crows)
        if cp is None: continue
        delta=cp-mean(member_means)
        deltas.append(delta); samples.append(len(crows))
        combo_gd=mean(x[1] for x in crows)
        member_gd=mean(mean(x[1] for x in player_hist[pid]) for pid in ids)
        if delta<0 and combo_gd-member_gd<0:
            anti+=1
    prefix={"PAIR":"pair","TRIO":"trio","LINE":"line"}[combo_type]
    return {
        f"{prefix}_candidates":len(current_keys),
        f"{prefix}_eligible_prior":len(deltas),
        f"{prefix}_prior_sample_mean":round(mean(samples),3) if samples else "",
        f"{prefix}_points_delta_mean":round(mean(deltas),3) if deltas else "",
        f"{prefix}_points_delta_min":round(min(deltas),3) if deltas else "",
        f"{prefix}_points_delta_max":round(max(deltas),3) if deltas else "",
        f"anti_{prefix}_prior_count":anti,
    }


def build() -> tuple[list[dict[str,Any]],list[dict[str,Any]],list[dict[str,Any]],list[dict[str,Any]],list[dict[str,Any]]]:
    lineups=read_csv(LINEUPS)
    outcomes=fixture_outcomes(read_csv(FIXTURES))
    teams=historical_team_rows(lineups,outcomes)

    final_rows=[]
    wf_rows=[]

    for tid,fixtures in teams.items():
        combo_hist=defaultdict(list)
        player_hist=defaultdict(list)
        names={}
        team_name=fixtures[-1]["team_name"] if fixtures else tid

        for fx in fixtures:
            for p in fx["xi"]:
                names[p["player_id"]]=p["player_name"] or p["player_id"]

            current=combinations_for_xi(fx["xi"])
            keys_by_type=defaultdict(list)
            for ctype,pos,members in current:
                keys_by_type[ctype].append(combo_key(ctype,members,pos))

            wf={
                "fixture_id":fx["fixture_id"],"kickoff_utc":fx["kickoff_utc"],
                "team_id":tid,"team_name":fx["team_name"],"side":fx["side"],
                "team_points":fx["points"],"team_goal_diff":fx["gd"],
                "outcome_known_after_match_only":"YES",
                "strictly_prior_combo_history_only":"YES",
                "temporal_authority":"RETROSPECTIVE_CHRONOLOGY_ONLY",
                "prematch_observation_time_known":"NO",
                "validation_authority":"ASSOCIATION_DATASET_ONLY",
                "research_only":"YES",
            }
            for ctype in ("PAIR","TRIO","LINE"):
                wf.update(summary_for_current(ctype,keys_by_type.get(ctype,[]),combo_hist,player_hist))
            wf_rows.append(wf)

            for p in fx["xi"]:
                player_hist[p["player_id"]].append((float(fx["points"]),float(fx["gd"])))
            for ctype,pos,members in current:
                combo_hist[combo_key(ctype,members,pos)].append((float(fx["points"]),float(fx["gd"])))

        for key in sorted(combo_hist,key=lambda k:(k[0],k[1],k[2])):
            row=association_from_history(team_name,key,names,combo_hist,player_hist)
            row["team_id"]=tid; row["team_name"]=team_name
            final_rows.append(row)

    pairs=[r for r in final_rows if r["combo_type"]=="PAIR"]
    trios=[r for r in final_rows if r["combo_type"]=="TRIO"]
    lines=[r for r in final_rows if r["combo_type"]=="LINE"]
    anti=[{
        "team_id":r["team_id"],"team_name":r["team_name"],"combo_type":r["combo_type"],
        "position_group":r["position_group"],"member_ids":r["member_ids"],"member_names":r["member_names"],
        "co_starts":r["co_starts"],"points_delta_vs_member_baseline":r["points_delta_vs_member_baseline"],
        "goal_diff_delta_vs_member_baseline":r["goal_diff_delta_vs_member_baseline"],
        "anti_synergy_candidate":"true","validation_authority":"DESCRIPTIVE_ASSOCIATION_ONLY",
        "research_only":"true",
    } for r in final_rows if r["anti_synergy_candidate"]=="true"]
    return pairs,trios,lines,anti,wf_rows


def main() -> None:
    pairs,trios,lines,anti,wf=build()
    write_csv(PAIR_OUT,COMBO_FIELDS,pairs)
    write_csv(TRIO_OUT,COMBO_FIELDS,trios)
    write_csv(LINE_OUT,COMBO_FIELDS,lines)
    write_csv(ANTI_OUT,ANTI_FIELDS,anti)
    write_csv(WF_OUT,WF_FIELDS,wf)

    pair_eligible=sum(r["eligible"]=="true" for r in pairs)
    trio_eligible=sum(r["eligible"]=="true" for r in trios)
    line_eligible=sum(r["eligible"]=="true" for r in lines)
    wf_prior=sum(int(r.get("pair_eligible_prior") or 0)+int(r.get("trio_eligible_prior") or 0)+int(r.get("line_eligible_prior") or 0) for r in wf)

    payload={
        "version":VERSION,
        "run_at_utc":utc_now(),
        "status":"VALIDATION_PENDING" if (pair_eligible or trio_eligible or line_eligible) else "RESEARCH_ONLY",
        "checklist_item_11_data_engineering_foundation":"IN_PROGRESS",
        "checklist_item_11_predictive_authority":"NOT_AUTHORIZED",
        "operational_betting_authority":False,
        "creates_signal":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "outputs":{
            "pair_rows":len(pairs),"pair_eligible_rows":pair_eligible,
            "trio_rows":len(trios),"trio_eligible_rows":trio_eligible,
            "line_rows":len(lines),"line_eligible_rows":line_eligible,
            "anti_synergy_candidates":len(anti),
            "walk_forward_team_fixture_rows":len(wf),
            "walk_forward_prior_eligible_combo_exposures":wf_prior,
        },
        "governance":{
            "pair_trio_line_are_separate_dimensions":True,
            "anti_synergy_is_descriptive_not_causal":True,
            "strictly_prior_walk_forward_features":True,
            "target_outcome_excluded_from_current_fixture_features":True,
            "raw_combo_score_forbidden":True,
            "specialist_validation_required_before_decision_use":True,
        },
        "hard_blockers":[
            "HISTORICAL_LINEUPS_ARE_RETROSPECTIVE_NOT_PREMATCH_FROZEN",
            "MARKET_ADJUSTED_OUT_OF_SAMPLE_SYNERGY_VALIDATION_NOT_COMPLETED",
            "SUBSTITUTION_INTERACTION_LAYER_NOT_BUILT",
            "PAIR_TRIO_LINE_CONTEXT_CONFOUNDERS_NOT_YET_CONTROLLED",
        ],
        "closure_rule":"Item 11 may progress as a research/data foundation only. No synergy probability, EV, value, eligibility or stake authority is granted until strictly-prior features pass specialist out-of-sample validation.",
    }
    write_json(READINESS_OUT,payload)
    print(json.dumps(payload,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
