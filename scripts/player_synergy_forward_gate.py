#!/usr/bin/env python3
"""PBK checklist item 11 — prospective prematch synergy forward gate.

Provider-free and fail-closed.

Closes the DATA/RESEARCH engineering foundation for item 11 by:
- projecting already-researched pair/trio/line associations onto genuinely
  prematch official XI observations captured before kickoff;
- keeping pair/trio/line dimensions separate;
- carrying sample sizes and anti-synergy flags transparently;
- emitting an explicit promotion gate that refuses predictive authority until
  prospective forward evidence and specialist validation are sufficient.

The historical association tables remain retrospective research.  The new
observation timestamp, however, is genuine prematch evidence for the current XI
from this point forward.
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

OPS=Path(os.getenv("OPS_DIR","ops"))
LINEUPS=OPS/"lineup_snapshots.csv"
PAIR=OPS/"player_synergy_pair_research.csv"
TRIO=OPS/"player_synergy_trio_research.csv"
LINE=OPS/"player_synergy_line_research.csv"
PHASE2=OPS/"player_synergy_phase2_readiness.json"

FORWARD_OUT=OPS/"player_synergy_prematch_forward_candidates.csv"
GATE_OUT=OPS/"player_synergy_promotion_gate.json"
READINESS_OUT=OPS/"player_synergy_final_readiness.json"

VERSION="PBK_PLAYER_SYNERGY_FORWARD_GATE_V1"

FIELDS=[
    "fixture_id","kickoff_utc","captured_at_utc","minutes_before_kickoff",
    "team_id","team_name","side","formation",
    "official_xi_count",
    "pair_candidates","pair_research_eligible","pair_positive","pair_negative",
    "pair_anti_candidates","pair_weighted_delta_mean",
    "trio_candidates","trio_research_eligible","trio_positive","trio_negative",
    "trio_anti_candidates","trio_weighted_delta_mean",
    "line_candidates","line_research_eligible","line_positive","line_negative",
    "line_anti_candidates","line_weighted_delta_mean",
    "historical_association_authority","prematch_observation_authority",
    "probability_authority","creates_signal","eligibility_mutation",
    "stake_changes","research_only",
]


def read_csv(path: Path) -> list[dict[str,str]]:
    if not path.exists(): return []
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str,Any]:
    if not path.exists(): return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError,ValueError,json.JSONDecodeError):
        return {}


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


def fnum(v: Any) -> float|None:
    try:
        x=float(str(v).strip())
    except (TypeError,ValueError):
        return None
    return x if math.isfinite(x) else None


def parse_dt(v: Any) -> datetime|None:
    try:
        x=datetime.fromisoformat(str(v or "").replace("Z","+00:00"))
    except (TypeError,ValueError):
        return None
    if x.tzinfo is None: return None
    return x.astimezone(timezone.utc)


def parse_xi(value: Any) -> list[dict[str,str]]:
    try:
        raw=json.loads(value) if isinstance(value,str) else value
    except (TypeError,ValueError,json.JSONDecodeError):
        return []
    if not isinstance(raw,list) or len(raw)!=11: return []
    out=[]; seen=set()
    for item in raw:
        if not isinstance(item,dict): return []
        p=item.get("player") if isinstance(item.get("player"),dict) else item
        pid=str(p.get("id") or p.get("player_id") or "").strip()
        name=str(p.get("name") or p.get("player_name") or "").strip()
        pos=str(p.get("pos") or p.get("position") or "").strip().upper()
        if not pid or pid in seen: return []
        seen.add(pid)
        if pos.startswith("GK"): pos="G"
        elif pos.startswith("D"): pos="D"
        elif pos.startswith("M"): pos="M"
        elif pos.startswith("F") or pos.startswith("A"): pos="F"
        elif pos not in {"G","D","M","F"}: pos=""
        out.append({"id":pid,"name":name,"pos":pos})
    return out


def latest_prematch_official(rows: list[dict[str,str]]) -> list[dict[str,Any]]:
    best={}
    for row in rows:
        fid=sval(row,"fixture_id"); tid=sval(row,"team_id")
        if not fid or not tid or sval(row,"official_lineup").upper() not in {"YES","TRUE","1"}:
            continue
        xi=parse_xi(row.get("starting_xi_json"))
        captured=parse_dt(row.get("captured_at_utc")); kickoff=parse_dt(row.get("kickoff_utc"))
        if len(xi)!=11 or captured is None or kickoff is None or captured>kickoff:
            continue
        key=(fid,tid)
        if key not in best or captured>best[key]["captured"]:
            best[key]={
                "fixture_id":fid,"team_id":tid,"team_name":sval(row,"team_name"),
                "side":sval(row,"side").upper(),"formation":sval(row,"formation"),
                "captured":captured,"kickoff":kickoff,"xi":xi,
            }
    return sorted(best.values(),key=lambda r:(r["kickoff"],r["fixture_id"],r["team_id"]))


def research_index(rows: list[dict[str,str]]) -> dict[tuple[str,tuple[str,...],str],dict[str,str]]:
    out={}
    for row in rows:
        tid=sval(row,"team_id")
        ids=tuple(sorted(x for x in sval(row,"member_ids").split("|") if x))
        pos=sval(row,"position_group")
        if tid and ids:
            out[(tid,ids,pos)]=row
    return out


def current_keys(xi: list[dict[str,str]], combo_type: str) -> list[tuple[tuple[str,...],str]]:
    if combo_type=="PAIR":
        return [(tuple(sorted(p["id"] for p in members)),"") for members in itertools.combinations(xi,2)]
    if combo_type=="TRIO":
        return [(tuple(sorted(p["id"] for p in members)),"") for members in itertools.combinations(xi,3)]
    groups=defaultdict(list)
    for p in xi:
        if p["pos"] in {"D","M","F"}: groups[p["pos"]].append(p)
    return [(tuple(sorted(p["id"] for p in members)),pos) for pos,members in sorted(groups.items()) if len(members)>=2]


def summarize_dimension(tid: str, xi: list[dict[str,str]], combo_type: str, idx: dict[tuple[str,tuple[str,...],str],dict[str,str]]) -> dict[str,Any]:
    keys=current_keys(xi,combo_type)
    rows=[]
    for ids,pos in keys:
        r=idx.get((tid,ids,pos))
        if r and sval(r,"eligible").lower()=="true":
            rows.append(r)
    positives=sum(sval(r,"association_direction")=="POSITIVE" for r in rows)
    negatives=sum(sval(r,"association_direction")=="NEGATIVE" for r in rows)
    anti=sum(sval(r,"anti_synergy_candidate").lower()=="true" for r in rows)
    weighted=[]
    weights=[]
    for r in rows:
        d=fnum(r.get("points_delta_vs_member_baseline"))
        n=fnum(r.get("co_starts"))
        if d is not None and n is not None and n>0:
            weighted.append(d*n); weights.append(n)
    score=sum(weighted)/sum(weights) if weights else None
    p=combo_type.lower()
    return {
        f"{p}_candidates":len(keys),
        f"{p}_research_eligible":len(rows),
        f"{p}_positive":positives,
        f"{p}_negative":negatives,
        f"{p}_anti_candidates":anti,
        f"{p}_weighted_delta_mean":round(score,4) if score is not None else "",
    }


def build_forward(lineups: list[dict[str,str]], pairs: list[dict[str,str]], trios: list[dict[str,str]], lines: list[dict[str,str]]) -> list[dict[str,Any]]:
    indexes={
        "PAIR":research_index(pairs),
        "TRIO":research_index(trios),
        "LINE":research_index(lines),
    }
    out=[]
    for obs in latest_prematch_official(lineups):
        mins=(obs["kickoff"]-obs["captured"]).total_seconds()/60.0
        row={
            "fixture_id":obs["fixture_id"],
            "kickoff_utc":obs["kickoff"].replace(microsecond=0).isoformat().replace("+00:00","Z"),
            "captured_at_utc":obs["captured"].replace(microsecond=0).isoformat().replace("+00:00","Z"),
            "minutes_before_kickoff":round(mins,2),
            "team_id":obs["team_id"],"team_name":obs["team_name"],"side":obs["side"],
            "formation":obs["formation"],"official_xi_count":11,
            "historical_association_authority":"RETROSPECTIVE_RESEARCH_ONLY",
            "prematch_observation_authority":"PREMATCH_FROZEN",
            "probability_authority":"NOT_AUTHORIZED",
            "creates_signal":"false","eligibility_mutation":"false","stake_changes":"false",
            "research_only":"true",
        }
        for ctype in ("PAIR","TRIO","LINE"):
            row.update(summarize_dimension(obs["team_id"],obs["xi"],ctype,indexes[ctype]))
        out.append(row)
    return out


def main() -> None:
    forward=build_forward(read_csv(LINEUPS),read_csv(PAIR),read_csv(TRIO),read_csv(LINE))
    write_csv(FORWARD_OUT,FIELDS,forward)

    phase2=read_json(PHASE2)
    prematch_rows=len(forward)
    with_any=sum(
        int(r.get("pair_research_eligible") or 0)+int(r.get("trio_research_eligible") or 0)+int(r.get("line_research_eligible") or 0)>0
        for r in forward
    )

    gate={
        "version":VERSION,
        "run_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "dimensions":{
            "PAIR":{"status":"NOT_PROMOTED","reason":"TRAIN_HOLDOUT_SIGN_UNSTABLE"},
            "TRIO":{"status":"NOT_PROMOTED","reason":"TRAIN_HOLDOUT_SIGN_UNSTABLE"},
            "LINE":{"status":"RESEARCH_CANDIDATE_ONLY","reason":"SIGN_STABLE_BUT_EFFECT_WEAK_AND_PROSPECTIVE_SAMPLE_REQUIRED"},
            "ANTI_SYNERGY":{"status":"RESEARCH_CANDIDATE_ONLY","reason":"DESCRIPTIVE_ASSOCIATION_NOT_CAUSAL"},
            "SUBSTITUTION":{"status":"POSTMATCH_RESEARCH_ONLY","reason":"POSTMATCH_FACTUAL_NOT_PREMATCH_FEATURE"},
        },
        "promotion_policy":{
            "requires_genuine_prematch_observation":True,
            "requires_forward_sample":True,
            "requires_market_adjusted_oos_specialist_validation":True,
            "requires_calibration_and_incremental_value":True,
            "raw_combo_mega_score_forbidden":True,
            "automatic_promotion_forbidden":True,
        },
        "operational_betting_authority":False,
    }
    write_json(GATE_OUT,gate)

    foundation_complete=(
        bool(phase2.get("market_adjusted_oos_research_completed"))
        and bool(phase2.get("substitution_interaction_dataset_built"))
        and prematch_rows>0
    )
    readiness={
        "version":VERSION,
        "status":"VALIDATION_PENDING",
        "checklist_item_11_data_engineering_foundation":"COMPLETE" if foundation_complete else "IN_PROGRESS",
        "checklist_item_11_predictive_authority":"NOT_AUTHORIZED",
        "operational_betting_authority":False,
        "creates_signal":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "evidence":{
            "prematch_frozen_team_fixture_rows":prematch_rows,
            "prematch_rows_with_any_research_combo":with_any,
            "market_adjusted_oos_research_completed":bool(phase2.get("market_adjusted_oos_research_completed")),
            "substitution_interaction_dataset_built":bool(phase2.get("substitution_interaction_dataset_built")),
            "pair_promoted":False,
            "trio_promoted":False,
            "line_promoted":False,
        },
        "resolved_engineering_gates":[
            "PAIR_TRIO_LINE_RESEARCH_DATASETS_BUILT",
            "STRICTLY_PRIOR_WALK_FORWARD_FEATURES_BUILT",
            "MARKET_ADJUSTED_OOS_RESEARCH_BUILT",
            "SUBSTITUTION_INTERACTION_DATASET_BUILT",
            "GENUINE_PREMATCH_XI_OBSERVATION_FORWARD_PIPELINE_BUILT",
            "EXPLICIT_FAIL_CLOSED_PROMOTION_GATE_BUILT",
        ],
        "hard_blockers_to_predictive_authority":[
            "PROSPECTIVE_PREMATCH_FORWARD_SAMPLE_TOO_SMALL",
            "SYNERGY_SPECIALIST_PROBABILITY_MODEL_NOT_VALIDATED",
            "CALIBRATION_AND_INCREMENTAL_MARKET_VALUE_NOT_DEMONSTRATED",
        ],
        "closure_rule":"Checklist item 11 DATA/RESEARCH FOUNDATION may be closed when COMPLETE. Predictive betting authority remains NOT_AUTHORIZED until the prospective prematch sample and specialist model pass validation.",
    }
    write_json(READINESS_OUT,readiness)
    print(json.dumps(readiness,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
