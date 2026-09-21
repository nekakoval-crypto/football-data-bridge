#!/usr/bin/env python3
"""PBK checklist item 11 — synergy validation + substitution interactions.

Provider-free and fail-closed.

Phase 2 extends the item-11 research foundation in two directions:
1) exact-fixture join of strictly-prior pair/trio/line features to the durable
   PBK14 closing-market matrix for market-adjusted out-of-sample research;
2) exact player-id substitution transitions from official lineup snapshots and
   the durable match-event archive.

No probability, EV/value, eligibility or stake authority is granted here.
"""
from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

OPS=Path(os.getenv("OPS_DIR","ops"))
SYNERGY_WF=OPS/"player_synergy_walk_forward.csv"
MARKET=OPS/"pbk14_congestion_market_join_research.csv"
LINEUPS=OPS/"lineup_snapshots.csv"
EVENTS=OPS/"match_event_snapshots.csv"

MARKET_OUT=OPS/"player_synergy_market_validation.csv"
MARKET_SUMMARY=OPS/"player_synergy_market_validation_summary.json"
SUB_OUT=OPS/"player_synergy_substitution_interactions.csv"
SUB_SUMMARY=OPS/"player_synergy_substitution_summary.json"
READINESS=OPS/"player_synergy_phase2_readiness.json"

VERSION="PBK_PLAYER_SYNERGY_PHASE2_V1"

MARKET_FIELDS=[
    "fixture_id","kickoff_utc","team_id","team_name","side",
    "market_match_id","league_code","season_label",
    "market_win_odds","market_draw_odds","market_loss_odds",
    "market_no_vig_win_probability","actual_win","market_residual_win",
    "pair_eligible_prior","pair_points_delta_mean",
    "trio_eligible_prior","trio_points_delta_mean",
    "line_eligible_prior","line_points_delta_mean",
    "congestion_72h","previous_thursday",
    "chronological_bucket","research_only","validation_authority",
]
SUB_FIELDS=[
    "fixture_id","kickoff_utc","team_id","team_name","side",
    "elapsed","extra","out_player_id","out_player_name","in_player_id","in_player_name",
    "out_was_starter","in_was_starter","official_xi_known",
    "transition_key","event_observed_at_utc",
    "temporal_authority","validation_authority","research_only",
]


def read_csv(path: Path) -> list[dict[str,str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields: list[str], rows: list[dict[str,Any]]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    os.replace(tmp,path)


def write_json(path: Path, payload: dict[str,Any]) -> None:
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    os.replace(tmp,path)


def sval(row: dict[str,Any], key: str) -> str:
    return str((row or {}).get(key) or "").strip()


def fnum(value: Any) -> float|None:
    try:
        x=float(str(value).strip())
    except (TypeError,ValueError):
        return None
    return x if math.isfinite(x) else None


def bval(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1","true","yes","y"}


def parse_dt(value: Any) -> datetime|None:
    try:
        x=datetime.fromisoformat(str(value or "").replace("Z","+00:00"))
    except (TypeError,ValueError):
        return None
    if x.tzinfo is None:
        return None
    return x.astimezone(timezone.utc)


def parse_xi(value: Any) -> set[str]:
    try:
        raw=json.loads(value) if isinstance(value,str) else value
    except (TypeError,ValueError,json.JSONDecodeError):
        return set()
    if not isinstance(raw,list):
        return set()
    out=set()
    for item in raw:
        if not isinstance(item,dict): continue
        p=item.get("player") if isinstance(item.get("player"),dict) else item
        pid=str(p.get("id") or p.get("player_id") or "").strip()
        if pid: out.add(pid)
    return out if len(out)==11 else set()


def choose_odds(row: dict[str,str], side: str) -> tuple[float|None,float|None,float|None]:
    if side=="HOME":
        win=("avg_close_home","b365_close_home")
        loss=("avg_close_away","b365_close_away")
    else:
        win=("avg_close_away","b365_close_away")
        loss=("avg_close_home","b365_close_home")
    draw=("avg_close_draw","b365_close_draw")
    def first(keys):
        for k in keys:
            v=fnum(row.get(k))
            if v is not None and v>1:
                return v
        return None
    return first(win),first(draw),first(loss)


def no_vig_win(win: float, draw: float, loss: float) -> float:
    raw=[1.0/win,1.0/draw,1.0/loss]
    return raw[0]/sum(raw)


def market_index(rows: list[dict[str,str]]) -> dict[str,dict[str,str]]:
    out={}
    for row in rows:
        fid=sval(row,"api_fixture_id")
        if not fid: continue
        status=sval(row,"mapping_status").upper()
        if status not in {"AUTO","HIGH"}: continue
        if bval(row.get("fuzzy_string_matching_used")): continue
        if not bval(row.get("one_to_one_verified")): continue
        out[fid]=row
    return out


def actual_win(row: dict[str,str], side: str) -> int|None:
    result=sval(row,"ft_result").upper()
    if result not in {"H","D","A"}:
        return None
    return int((side=="HOME" and result=="H") or (side=="AWAY" and result=="A"))


def chronology_bucket(kickoff: str, ordered: list[str]) -> str:
    if not ordered:
        return ""
    try:
        idx=ordered.index(kickoff)
    except ValueError:
        return ""
    frac=(idx+1)/len(ordered)
    if frac<=0.6: return "TRAIN_EARLY"
    if frac<=0.8: return "VALIDATION_MIDDLE"
    return "HOLDOUT_LATE"


def build_market_validation(wf_rows: list[dict[str,str]], market_rows: list[dict[str,str]]) -> list[dict[str,Any]]:
    market=market_index(market_rows)
    kickoffs=sorted({sval(r,"kickoff_utc") for r in wf_rows if sval(r,"kickoff_utc")})
    out=[]
    for row in wf_rows:
        fid=sval(row,"fixture_id")
        side=sval(row,"side").upper()
        m=market.get(fid)
        if m is None or side not in {"HOME","AWAY"}:
            continue
        win,draw,loss=choose_odds(m,side)
        outcome=actual_win(m,side)
        if None in (win,draw,loss,outcome):
            continue
        p=no_vig_win(win,draw,loss)
        out.append({
            "fixture_id":fid,"kickoff_utc":sval(row,"kickoff_utc"),
            "team_id":sval(row,"team_id"),"team_name":sval(row,"team_name"),"side":side,
            "market_match_id":sval(m,"historical_match_id"),
            "league_code":sval(m,"league_code"),"season_label":sval(m,"season_label"),
            "market_win_odds":round(win,4),"market_draw_odds":round(draw,4),"market_loss_odds":round(loss,4),
            "market_no_vig_win_probability":round(p,6),"actual_win":outcome,
            "market_residual_win":round(outcome-p,6),
            "pair_eligible_prior":sval(row,"pair_eligible_prior"),
            "pair_points_delta_mean":sval(row,"pair_points_delta_mean"),
            "trio_eligible_prior":sval(row,"trio_eligible_prior"),
            "trio_points_delta_mean":sval(row,"trio_points_delta_mean"),
            "line_eligible_prior":sval(row,"line_eligible_prior"),
            "line_points_delta_mean":sval(row,"line_points_delta_mean"),
            "congestion_72h":"YES" if any(bval(m.get(k)) for k in [
                "either_team_prev_nonleague_within_72h",
                "either_team_prev_uefa_within_72h",
                "either_team_prev_domestic_cup_within_72h"]) else "NO",
            "previous_thursday":"YES" if bval(m.get("either_team_previous_nonleague_was_thursday")) else "NO",
            "chronological_bucket":chronology_bucket(sval(row,"kickoff_utc"),kickoffs),
            "research_only":"YES","validation_authority":"MARKET_ADJUSTED_ASSOCIATION_ONLY",
        })
    return out


def pearson(xs: list[float], ys: list[float]) -> float|None:
    if len(xs)<3 or len(xs)!=len(ys):
        return None
    mx,my=mean(xs),mean(ys)
    num=sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    dx=sum((x-mx)**2 for x in xs)
    dy=sum((y-my)**2 for y in ys)
    if dx<=0 or dy<=0: return None
    return num/math.sqrt(dx*dy)


def dimension_summary(rows: list[dict[str,Any]], prefix: str) -> dict[str,Any]:
    feature=f"{prefix}_points_delta_mean"
    by_bucket={}
    for bucket in ("TRAIN_EARLY","VALIDATION_MIDDLE","HOLDOUT_LATE"):
        xs=[]; ys=[]
        subset=[r for r in rows if r["chronological_bucket"]==bucket]
        for r in subset:
            x=fnum(r.get(feature)); y=fnum(r.get("market_residual_win"))
            if x is not None and y is not None:
                xs.append(x); ys.append(y)
        corr=pearson(xs,ys)
        by_bucket[bucket]={
            "rows":len(xs),
            "pearson_feature_vs_market_residual":round(corr,6) if corr is not None else None,
            "mean_market_residual":round(mean(ys),6) if ys else None,
        }
    train=by_bucket["TRAIN_EARLY"]["pearson_feature_vs_market_residual"]
    hold=by_bucket["HOLDOUT_LATE"]["pearson_feature_vs_market_residual"]
    same_sign=bool(train is not None and hold is not None and train*hold>0)
    return {"feature":feature,"buckets":by_bucket,"train_holdout_same_sign":same_sign}


def latest_official_lineups(rows: list[dict[str,str]]) -> dict[tuple[str,str],dict[str,Any]]:
    best={}
    for row in rows:
        fid=sval(row,"fixture_id"); tid=sval(row,"team_id")
        if not fid or not tid or sval(row,"official_lineup").upper() not in {"YES","TRUE","1"}:
            continue
        xi=parse_xi(row.get("starting_xi_json"))
        if len(xi)!=11:
            continue
        captured=parse_dt(row.get("captured_at_utc"))
        kickoff=parse_dt(row.get("kickoff_utc"))
        if captured is None or kickoff is None or captured>kickoff:
            continue
        key=(fid,tid)
        if key not in best or captured>best[key]["captured"]:
            best[key]={
                "captured":captured,"kickoff_utc":sval(row,"kickoff_utc"),
                "team_name":sval(row,"team_name"),"side":sval(row,"side").upper(),"xi":xi,
            }
    return best


def build_substitutions(lineup_rows: list[dict[str,str]], event_rows: list[dict[str,str]]) -> list[dict[str,Any]]:
    lineups=latest_official_lineups(lineup_rows)
    out=[]
    for e in event_rows:
        et=sval(e,"event_type").lower()
        if et not in {"subst","substitution"}:
            continue
        fid=sval(e,"fixture_id"); tid=sval(e,"team_id")
        out_id=sval(e,"player_id"); in_id=sval(e,"assist_id")
        if not fid or not tid or not out_id or not in_id:
            continue
        lu=lineups.get((fid,tid))
        xi=(lu or {}).get("xi",set())
        out.append({
            "fixture_id":fid,"kickoff_utc":(lu or {}).get("kickoff_utc") or sval(e,"kickoff_utc"),
            "team_id":tid,"team_name":sval(e,"team_name") or (lu or {}).get("team_name",""),
            "side":(lu or {}).get("side",""),
            "elapsed":sval(e,"elapsed"),"extra":sval(e,"extra"),
            "out_player_id":out_id,"out_player_name":sval(e,"player_name"),
            "in_player_id":in_id,"in_player_name":sval(e,"assist_name"),
            "out_was_starter":"YES" if out_id in xi else ("NO" if lu else "UNKNOWN"),
            "in_was_starter":"YES" if in_id in xi else ("NO" if lu else "UNKNOWN"),
            "official_xi_known":"YES" if lu else "NO",
            "transition_key":f"{tid}:{out_id}->{in_id}",
            "event_observed_at_utc":sval(e,"observed_at_utc"),
            "temporal_authority":"POSTMATCH_FACTUAL",
            "validation_authority":"DESCRIPTIVE_SUBSTITUTION_INTERACTION_ONLY",
            "research_only":"YES",
        })
    return out


def main() -> None:
    market_rows=build_market_validation(read_csv(SYNERGY_WF),read_csv(MARKET))
    write_csv(MARKET_OUT,MARKET_FIELDS,market_rows)

    dim={p:dimension_summary(market_rows,p) for p in ("pair","trio","line")}
    summary={
        "version":VERSION,"run_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "joined_team_fixture_rows":len(market_rows),
        "dimensions":dim,
        "market_baseline_control":True,
        "congestion_flags_preserved":True,
        "out_of_sample_buckets":["VALIDATION_MIDDLE","HOLDOUT_LATE"],
        "operational_betting_authority":False,
        "research_only":True,
    }
    write_json(MARKET_SUMMARY,summary)

    subs=build_substitutions(read_csv(LINEUPS),read_csv(EVENTS))
    write_csv(SUB_OUT,SUB_FIELDS,subs)
    sub_summary={
        "version":VERSION,
        "substitution_rows":len(subs),
        "rows_with_official_xi":sum(r["official_xi_known"]=="YES" for r in subs),
        "starter_out_rows":sum(r["out_was_starter"]=="YES" for r in subs),
        "bench_in_rows":sum(r["in_was_starter"]=="NO" for r in subs),
        "unique_transition_keys":len({r["transition_key"] for r in subs}),
        "temporal_authority":"POSTMATCH_FACTUAL",
        "operational_betting_authority":False,
        "research_only":True,
    }
    write_json(SUB_SUMMARY,sub_summary)

    holdout_rows=sum(1 for r in market_rows if r["chronological_bucket"]=="HOLDOUT_LATE")
    market_complete=len(market_rows)>=50 and holdout_rows>=10
    sub_complete=len(subs)>0
    payload={
        "version":VERSION,
        "status":"VALIDATION_PENDING",
        "checklist_item_11_data_engineering_foundation":"IN_PROGRESS",
        "checklist_item_11_predictive_authority":"NOT_AUTHORIZED",
        "operational_betting_authority":False,
        "creates_signal":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "market_adjusted_oos_research_completed":market_complete,
        "substitution_interaction_dataset_built":sub_complete,
        "evidence":{
            "market_join_rows":len(market_rows),
            "holdout_rows":holdout_rows,
            "substitution_rows":len(subs),
            "substitution_rows_with_official_xi":sum(r["official_xi_known"]=="YES" for r in subs),
            "pair_train_holdout_same_sign":dim["pair"]["train_holdout_same_sign"],
            "trio_train_holdout_same_sign":dim["trio"]["train_holdout_same_sign"],
            "line_train_holdout_same_sign":dim["line"]["train_holdout_same_sign"],
        },
        "resolved_or_reduced_blockers":{
            "MARKET_ADJUSTED_OUT_OF_SAMPLE_SYNERGY_VALIDATION_NOT_COMPLETED":"RESOLVED_AS_RESEARCH_GATE" if market_complete else "STILL_BLOCKED_INSUFFICIENT_OVERLAP",
            "SUBSTITUTION_INTERACTION_LAYER_NOT_BUILT":"RESOLVED_AS_DESCRIPTIVE_DATASET" if sub_complete else "STILL_BLOCKED_NO_EXACT_EVENT_LINEUP_OVERLAP",
            "PAIR_TRIO_LINE_CONTEXT_CONFOUNDERS_NOT_YET_CONTROLLED":"PARTIALLY_REDUCED_MARKET_BASELINE_PLUS_CONGESTION_FLAGS",
        },
        "hard_blockers":[
            "HISTORICAL_LINEUPS_ARE_RETROSPECTIVE_NOT_PREMATCH_FROZEN",
            "FULL_CONTEXT_CONFOUNDER_CONTROL_NOT_COMPLETED",
            "SYNERGY_SPECIALIST_PROBABILITY_MODEL_NOT_VALIDATED",
            "SUBSTITUTION_INTERACTIONS_ARE_POSTMATCH_FACTUAL_NOT_PREMATCH_FEATURES",
        ],
        "closure_rule":"Phase 2 may close market-adjusted association and substitution-data engineering gates only. Predictive synergy authority remains forbidden until a specialist model is validated on genuine prematch evidence.",
    }
    write_json(READINESS,payload)
    print(json.dumps(payload,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
