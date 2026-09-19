#!/usr/bin/env python3
"""Stage80 — PBK16 provider-free historical pre-match table context.

Builds one deterministic row for every captured PBK16 domestic-league fixture
from the existing 40,989-row archive.

Safe scope:
- regular/core league fixtures: reconstruct points/played/PPG/GF/GA/GD/rank
  from strictly earlier calendar dates in the same provider league + season;
- non-regular provider phases (championship/relegation/playoff/finals/etc):
  fail closed as BLOCKED_NONREGULAR_PHASE_UNMODELED.

This layer intentionally does NOT claim official-table equivalence because
league-specific tiebreaks and post-split point adjustments are not yet fully
encoded for PBK16. It also does not infer title/relegation/Europe motivation.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

VERSION="PBK_STAGE80_PBK16_HISTORICAL_TABLE_CONTEXT_V1"
FINAL={"FT","AET","PEN"}
PHASE_PATTERNS=[
    re.compile(r"championship",re.I),
    re.compile(r"relegation",re.I),
    re.compile(r"play[- ]?off",re.I),
    re.compile(r"\bgroup\b",re.I),
    re.compile(r"\bfinals?\b",re.I),
    re.compile(r"conference",re.I),
    re.compile(r"promotion|demotion",re.I),
    re.compile(r"split",re.I),
]
RANK_TIEBREAK_CONTRACT="POINTS_GD_GF_TEAMNAME_RESEARCH_APPROX_V1"

FIELDS=[
    "domestic_fixture_id","provider_league_id","league_name","country","season",
    "round","kickoff_utc","date_utc","status",
    "home_team_id","home_team","away_team_id","away_team",
    "phase_class","context_status","phase_detection_contract",
    "core_participant_teams","table_teams_with_history","full_table_available",
    "home_played_pre","away_played_pre","home_points_pre","away_points_pre",
    "home_ppg_pre","away_ppg_pre","home_gf_pre","away_gf_pre",
    "home_ga_pre","away_ga_pre","home_gd_pre","away_gd_pre",
    "home_rank_pre","away_rank_pre",
    "rank_tiebreak_contract","official_table_equivalence",
    "exact_title_relegation_motivation_allowed","europe_status",
    "same_day_results_excluded","no_lookahead","historical_backfill_only",
    "research_only","operational_betting_authority","creates_signal",
    "probability_mutation","eligibility_mutation","stake_changes",
    "forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def write_json(path,payload):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)


def sval(row,key):
    return str((row or {}).get(key) or "").strip()


def as_int(v):
    try:
        return int(float(str(v).strip()))
    except (TypeError,ValueError):
        return None


def btext(v):
    return "true" if bool(v) else "false"


def parse_dt(v):
    try:
        dt=datetime.fromisoformat(str(v or "").replace("Z","+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (TypeError,ValueError):
        return None


def is_nonregular_round(label):
    s=str(label or "").strip()
    return bool(s) and any(p.search(s) for p in PHASE_PATTERNS)


def phase_class(row):
    return "NONREGULAR_PHASE" if is_nonregular_round(sval(row,"round")) else "REGULAR_CORE"


def empty_state():
    return {"played":0,"points":0,"gf":0,"ga":0}


def ranked(states):
    rows=[]
    for team,state in states.items():
        if int(state["played"])<=0:
            continue
        gf=int(state["gf"]); ga=int(state["ga"])
        rows.append({
            "team":team,"played":int(state["played"]),"points":int(state["points"]),
            "gf":gf,"ga":ga,"gd":gf-ga,
        })
    rows.sort(key=lambda r:(-r["points"],-r["gd"],-r["gf"],r["team"]))
    for i,r in enumerate(rows,1):
        r["rank"]=i
    return rows


def apply_result(row,states):
    if sval(row,"status").upper() not in FINAL:
        return True
    hg=as_int(row.get("home_goals")); ag=as_int(row.get("away_goals"))
    h=sval(row,"home_team_id") or sval(row,"home_team")
    a=sval(row,"away_team_id") or sval(row,"away_team")
    if hg is None or ag is None or not h or not a:
        return False
    states.setdefault(h,empty_state()); states.setdefault(a,empty_state())
    hs=states[h]; aas=states[a]
    hs["played"]+=1; aas["played"]+=1
    hs["gf"]+=hg; hs["ga"]+=ag
    aas["gf"]+=ag; aas["ga"]+=hg
    if hg>ag:
        hs["points"]+=3
    elif ag>hg:
        aas["points"]+=3
    else:
        hs["points"]+=1; aas["points"]+=1
    return True


def row_for(table,team):
    return next((r for r in table if r["team"]==team),None)


def ppg(points,played):
    if not played:
        return ""
    return round(float(points)/float(played),5)


def project(source_rows):
    domestic=[r for r in source_rows if sval(r,"competition_role")=="DOMESTIC_LEAGUE"]
    ids=[sval(r,"fixture_id") for r in domestic if sval(r,"fixture_id")]
    duplicate_ids=len(ids)-len(set(ids))

    parsed=[]
    invalid_dt=0
    for idx,row in enumerate(domestic):
        dt=parse_dt(row.get("kickoff_utc"))
        if dt is None:
            invalid_dt+=1
            continue
        league=sval(row,"provider_competition_id")
        season=sval(row,"season")
        parsed.append((league,season,dt.date().isoformat(),dt,idx,row))

    # Core participant universe from regular/core rows only.
    core_teams=defaultdict(set)
    for league,season,day,dt,idx,row in parsed:
        if phase_class(row)!="REGULAR_CORE":
            continue
        h=sval(row,"home_team_id") or sval(row,"home_team")
        a=sval(row,"away_team_id") or sval(row,"away_team")
        if h: core_teams[(league,season)].add(h)
        if a: core_teams[(league,season)].add(a)

    groups=defaultdict(list)
    for item in parsed:
        league,season,day,dt,idx,row=item
        groups[(league,season,day)].append((dt,idx,row))

    states_by_scope={}
    out=[]
    invalid_results=0
    for key in sorted(groups,key=lambda x:(x[0],x[1],x[2])):
        league,season,day=key
        states=states_by_scope.setdefault((league,season),{})
        day_rows=sorted(groups[key],key=lambda x:(x[0],x[1]))

        # Project all fixtures before applying any result from this UTC date.
        for dt,idx,row in day_rows:
            h=sval(row,"home_team_id") or sval(row,"home_team")
            a=sval(row,"away_team_id") or sval(row,"away_team")
            pclass=phase_class(row)
            table=ranked(states)
            hr=row_for(table,h); ar=row_for(table,a)
            core_count=len(core_teams.get((league,season),set()))
            full=bool(core_count) and len(table)==core_count
            blocked=(pclass!="REGULAR_CORE")
            status="BLOCKED_NONREGULAR_PHASE_UNMODELED" if blocked else "VALID_REGULAR_RESULTS_DERIVED"

            def v(r,key,default=""):
                return default if r is None else r.get(key,default)

            out.append({
                "domestic_fixture_id":sval(row,"fixture_id"),
                "provider_league_id":league,
                "league_name":sval(row,"competition_name"),
                "country":sval(row,"country"),
                "season":season,
                "round":sval(row,"round"),
                "kickoff_utc":sval(row,"kickoff_utc"),
                "date_utc":day,
                "status":sval(row,"status"),
                "home_team_id":sval(row,"home_team_id"),"home_team":sval(row,"home_team"),
                "away_team_id":sval(row,"away_team_id"),"away_team":sval(row,"away_team"),
                "phase_class":pclass,"context_status":status,
                "phase_detection_contract":"ROUND_LABEL_NONREGULAR_MARKERS_V1",
                "core_participant_teams":core_count,
                "table_teams_with_history":len(table),
                "full_table_available":btext(full),
                "home_played_pre":v(hr,"played",0),"away_played_pre":v(ar,"played",0),
                "home_points_pre":v(hr,"points",0),"away_points_pre":v(ar,"points",0),
                "home_ppg_pre":ppg(v(hr,"points",0),v(hr,"played",0)),
                "away_ppg_pre":ppg(v(ar,"points",0),v(ar,"played",0)),
                "home_gf_pre":v(hr,"gf",0),"away_gf_pre":v(ar,"gf",0),
                "home_ga_pre":v(hr,"ga",0),"away_ga_pre":v(ar,"ga",0),
                "home_gd_pre":v(hr,"gd",0),"away_gd_pre":v(ar,"gd",0),
                "home_rank_pre":"" if blocked else v(hr,"rank",""),
                "away_rank_pre":"" if blocked else v(ar,"rank",""),
                "rank_tiebreak_contract":RANK_TIEBREAK_CONTRACT,
                "official_table_equivalence":"false",
                "exact_title_relegation_motivation_allowed":"false",
                "europe_status":"UNKNOWN_BY_DESIGN",
                "same_day_results_excluded":"true","no_lookahead":"true",
                "historical_backfill_only":"true","research_only":"true",
                "operational_betting_authority":"false","creates_signal":"false",
                "probability_mutation":"false","eligibility_mutation":"false",
                "stake_changes":"false","forward_journal_mutation":"false",
            })

        # Only regular/core final results update this V1 table state.
        for dt,idx,row in day_rows:
            if phase_class(row)!="REGULAR_CORE":
                continue
            if not apply_result(row,states):
                invalid_results+=1

    out.sort(key=lambda r:(r["kickoff_utc"],r["provider_league_id"],r["domestic_fixture_id"]))
    return out,{
        "source_domestic_rows":len(domestic),
        "output_rows":len(out),
        "unique_domestic_fixture_ids":len(set(ids)),
        "duplicate_domestic_fixture_ids":duplicate_ids,
        "invalid_kickoff_rows":invalid_dt,
        "invalid_regular_result_rows":invalid_results,
    }


def run(source,out_csv,meta_out):
    rows=read_csv(source)
    projected,diag=project(rows)
    leagues={r["provider_league_id"] for r in projected}
    countries={r["country"] for r in projected}
    cells={(r["provider_league_id"],r["season"]) for r in projected}
    regular=sum(r["phase_class"]=="REGULAR_CORE" for r in projected)
    blocked=sum(r["context_status"]=="BLOCKED_NONREGULAR_PHASE_UNMODELED" for r in projected)
    full=sum(
        r["context_status"]=="VALID_REGULAR_RESULTS_DERIVED"
        and r["full_table_available"]=="true"
        for r in projected
    )
    status="OK" if (
        diag["source_domestic_rows"]==40989
        and diag["output_rows"]==40989
        and diag["unique_domestic_fixture_ids"]==40989
        and diag["duplicate_domestic_fixture_ids"]==0
        and diag["invalid_kickoff_rows"]==0
        and len(leagues)==16
        and len(countries)==16
        and len(cells)==143
        and all(r["exact_title_relegation_motivation_allowed"]=="false" for r in projected)
    ) else "ATTENTION"

    meta={
        "version":VERSION,"generated_at_utc":iso_now(),"status":status,
        **diag,
        "domestic_league_ids":len(leagues),"countries":len(countries),
        "captured_league_season_cells":len(cells),
        "regular_core_rows":regular,
        "blocked_nonregular_phase_rows":blocked,
        "regular_rows_with_full_table":full,
        "phase_detection_contract":"ROUND_LABEL_NONREGULAR_MARKERS_V1",
        "rank_tiebreak_contract":RANK_TIEBREAK_CONTRACT,
        "official_table_equivalence":False,
        "exact_title_relegation_motivation_allowed":False,
        "europe_status":"UNKNOWN_BY_DESIGN",
        "same_day_results_excluded":True,"no_lookahead":True,
        "provider_calls":0,"historical_backfill_only":True,"research_only":True,
        "operational_betting_authority":False,"creates_signal":False,
        "probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,
    }
    write_csv(out_csv,projected)
    write_json(meta_out,meta)
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out-csv",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.source,a.out_csv,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
