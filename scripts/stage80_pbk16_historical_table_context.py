#!/usr/bin/env python3
"""Stage80 — PBK16 provider-free historical pre-match table context V2.

V2 consumes the durable PBK16 domestic phase audit instead of inferring phase
semantics from generic round-name patterns.

Safe reconstruction rules:
- TABLE_PHASE + REGULAR rows are reconstructed from strictly earlier UTC dates;
- TABLE_PHASE rows that require a season-format contract are fail-closed because
  split phases can halve/reset/carry points differently by league/season;
- POST_TABLE_PLAYOFF rows are excluded from league-table reconstruction;
- unresolved awarded/WO table results taint the remaining regular table state
  for that league-season instead of silently assuming a points outcome;
- same-day results never leak into another fixture on that UTC date.

This layer still does NOT claim official-table equivalence. League-specific
head-to-head tiebreaks and exact title/relegation/Europe motivation remain out
of authority until explicit season contracts are added.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

VERSION="PBK_STAGE80_PBK16_HISTORICAL_TABLE_CONTEXT_V2"
RANK_TIEBREAK_CONTRACT="POINTS_GD_GF_TEAMNAME_RESEARCH_APPROX_V1"
PHASE_AUDIT_CONTRACT="PBK16_2017_2025_PROVIDER_ROUND_LABELS_V1"

FIELDS=[
    "domestic_fixture_id","provider_league_id","league_name","country","season",
    "round","kickoff_utc","date_utc","status",
    "home_team_id","home_team","away_team_id","away_team",
    "phase_role","phase_family","table_result_policy",
    "season_format_contract_required","context_status","phase_audit_contract",
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


def is_true(v):
    return str(v or "").strip().lower() in {"1","true","yes","y"}


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


def empty_state():
    return {"played":0,"points":0,"gf":0,"ga":0}


def ranked(states):
    rows=[]
    for team,state in states.items():
        if int(state["played"])<=0:
            continue
        gf=int(state["gf"]); ga=int(state["ga"])
        rows.append({
            "team":team,
            "played":int(state["played"]),
            "points":int(state["points"]),
            "gf":gf,"ga":ga,"gd":gf-ga,
        })
    rows.sort(key=lambda r:(-r["points"],-r["gd"],-r["gf"],r["team"]))
    for i,row in enumerate(rows,1):
        row["rank"]=i
    return rows


def apply_played_result(row,states):
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


def audit_index(audit_rows):
    out={}
    duplicates=0
    invalid=0
    for row in audit_rows:
        fid=sval(row,"fixture_id")
        if not fid:
            invalid+=1
            continue
        if fid in out:
            duplicates+=1
            continue
        if (
            sval(row,"phase_role") not in {"TABLE_PHASE","POST_TABLE_PLAYOFF"}
            or sval(row,"table_result_policy") not in {
                "PLAYED_RESULT_USABLE",
                "NOT_PLAYED_EXCLUDE",
                "AWARDED_RESULT_REQUIRES_RULE_EVIDENCE",
                "NOT_FOR_LEAGUE_TABLE_RECONSTRUCTION",
            }
        ):
            invalid+=1
        out[fid]=row
    return out,duplicates,invalid


def safe_status(audit,scope_tainted,format_blocked):
    role=sval(audit,"phase_role")
    family=sval(audit,"phase_family")
    policy=sval(audit,"table_result_policy")
    requires=is_true(audit.get("season_format_contract_required"))

    if role=="POST_TABLE_PLAYOFF":
        return "POST_TABLE_PLAYOFF_EXCLUDED_FROM_TABLE"
    if role!="TABLE_PHASE":
        return "BLOCKED_UNKNOWN_PHASE"
    if requires or family!="REGULAR":
        return "BLOCKED_TABLE_PHASE_REQUIRES_SEASON_FORMAT_CONTRACT"
    if format_blocked:
        return "BLOCKED_AFTER_UNMODELED_TABLE_PHASE"
    if scope_tainted:
        return "BLOCKED_PRIOR_AWARDED_RESULT_UNRESOLVED"
    if policy=="AWARDED_RESULT_REQUIRES_RULE_EVIDENCE":
        return "VALID_PREMATCH_AWARDED_RESULT_WILL_TAINT"
    if policy=="NOT_PLAYED_EXCLUDE":
        return "VALID_PREMATCH_NOT_PLAYED_NO_STATE_MUTATION"
    if policy=="PLAYED_RESULT_USABLE":
        return "VALID_REGULAR_RESULTS_DERIVED"
    return "BLOCKED_UNSUPPORTED_RESULT_POLICY"


def project(source_rows,audit_rows):
    domestic=[r for r in source_rows if sval(r,"competition_role")=="DOMESTIC_LEAGUE"]
    ids=[sval(r,"fixture_id") for r in domestic if sval(r,"fixture_id")]
    duplicate_ids=len(ids)-len(set(ids))
    audit, audit_duplicates, audit_invalid=audit_index(audit_rows)

    source_id_set=set(ids)
    audit_id_set=set(audit)
    missing_audit=source_id_set-audit_id_set
    extra_audit=audit_id_set-source_id_set

    parsed=[]
    invalid_dt=0
    for idx,row in enumerate(domestic):
        fid=sval(row,"fixture_id")
        dt=parse_dt(row.get("kickoff_utc"))
        if dt is None:
            invalid_dt+=1
            continue
        league=sval(row,"provider_competition_id")
        season=sval(row,"season")
        parsed.append((league,season,dt.date().isoformat(),dt,idx,row,audit.get(fid)))

    # The league participant universe comes from every TABLE_PHASE row. Appendix
    # playoff teams from lower divisions are excluded by the phase audit.
    core_teams=defaultdict(set)
    for league,season,day,dt,idx,row,arow in parsed:
        if not arow or sval(arow,"phase_role")!="TABLE_PHASE":
            continue
        h=sval(row,"home_team_id") or sval(row,"home_team")
        a=sval(row,"away_team_id") or sval(row,"away_team")
        if h: core_teams[(league,season)].add(h)
        if a: core_teams[(league,season)].add(a)

    groups=defaultdict(list)
    for item in parsed:
        league,season,day,dt,idx,row,arow=item
        groups[(league,season,day)].append((dt,idx,row,arow))

    states_by_scope={}
    tainted_by_scope=defaultdict(bool)
    format_blocked_by_scope=defaultdict(bool)
    out=[]
    invalid_played_results=0

    for key in sorted(groups,key=lambda x:(x[0],x[1],x[2])):
        league,season,day=key
        scope=(league,season)
        states=states_by_scope.setdefault(scope,{})
        day_rows=sorted(groups[key],key=lambda x:(x[0],x[1]))

        # Project every fixture before applying any result from this UTC date.
        for dt,idx,row,arow in day_rows:
            fid=sval(row,"fixture_id")
            if arow is None:
                status="BLOCKED_MISSING_PHASE_AUDIT"
                role=family=policy=""
                requires=False
            else:
                role=sval(arow,"phase_role")
                family=sval(arow,"phase_family")
                policy=sval(arow,"table_result_policy")
                requires=is_true(arow.get("season_format_contract_required"))
                status=safe_status(
                    arow,
                    tainted_by_scope[scope],
                    format_blocked_by_scope[scope],
                )

            safe=status in {
                "VALID_REGULAR_RESULTS_DERIVED",
                "VALID_PREMATCH_AWARDED_RESULT_WILL_TAINT",
                "VALID_PREMATCH_NOT_PLAYED_NO_STATE_MUTATION",
            }
            h=sval(row,"home_team_id") or sval(row,"home_team")
            a=sval(row,"away_team_id") or sval(row,"away_team")
            table=ranked(states) if safe else []
            hr=row_for(table,h) if safe else None
            ar=row_for(table,a) if safe else None
            core_count=len(core_teams.get(scope,set()))
            full=safe and bool(core_count) and len(table)==core_count

            def v(r,key,default=""):
                return default if r is None else r.get(key,default)

            out.append({
                "domestic_fixture_id":fid,
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
                "phase_role":role,"phase_family":family,"table_result_policy":policy,
                "season_format_contract_required":btext(requires),
                "context_status":status,
                "phase_audit_contract":PHASE_AUDIT_CONTRACT,
                "core_participant_teams":core_count,
                "table_teams_with_history":len(table) if safe else "",
                "full_table_available":btext(full),
                "home_played_pre":v(hr,"played",0) if safe else "",
                "away_played_pre":v(ar,"played",0) if safe else "",
                "home_points_pre":v(hr,"points",0) if safe else "",
                "away_points_pre":v(ar,"points",0) if safe else "",
                "home_ppg_pre":ppg(v(hr,"points",0),v(hr,"played",0)) if safe else "",
                "away_ppg_pre":ppg(v(ar,"points",0),v(ar,"played",0)) if safe else "",
                "home_gf_pre":v(hr,"gf",0) if safe else "",
                "away_gf_pre":v(ar,"gf",0) if safe else "",
                "home_ga_pre":v(hr,"ga",0) if safe else "",
                "away_ga_pre":v(ar,"ga",0) if safe else "",
                "home_gd_pre":v(hr,"gd",0) if safe else "",
                "away_gd_pre":v(ar,"gd",0) if safe else "",
                "home_rank_pre":v(hr,"rank","") if safe else "",
                "away_rank_pre":v(ar,"rank","") if safe else "",
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

        # Apply results only after all same-day projections are complete.
        for dt,idx,row,arow in day_rows:
            if arow is None:
                continue
            role=sval(arow,"phase_role")
            family=sval(arow,"phase_family")
            policy=sval(arow,"table_result_policy")
            requires=is_true(arow.get("season_format_contract_required"))

            if role=="TABLE_PHASE" and (requires or family!="REGULAR"):
                format_blocked_by_scope[scope]=True
                continue
            if role!="TABLE_PHASE" or format_blocked_by_scope[scope]:
                continue
            if tainted_by_scope[scope]:
                continue
            if policy=="PLAYED_RESULT_USABLE":
                if not apply_played_result(row,states):
                    invalid_played_results+=1
                    tainted_by_scope[scope]=True
            elif policy=="AWARDED_RESULT_REQUIRES_RULE_EVIDENCE":
                tainted_by_scope[scope]=True
            elif policy=="NOT_PLAYED_EXCLUDE":
                continue
            else:
                tainted_by_scope[scope]=True

    out.sort(key=lambda r:(r["kickoff_utc"],r["provider_league_id"],r["domestic_fixture_id"]))
    return out,{
        "source_domestic_rows":len(domestic),
        "output_rows":len(out),
        "unique_domestic_fixture_ids":len(source_id_set),
        "duplicate_domestic_fixture_ids":duplicate_ids,
        "audit_rows":len(audit_rows),
        "audit_unique_fixture_ids":len(audit_id_set),
        "audit_duplicate_fixture_ids":audit_duplicates,
        "audit_invalid_rows":audit_invalid,
        "source_without_phase_audit":len(missing_audit),
        "phase_audit_without_source":len(extra_audit),
        "invalid_kickoff_rows":invalid_dt,
        "invalid_played_result_rows":invalid_played_results,
    }


def run(source,phase_audit,out_csv,meta_out):
    rows=read_csv(source)
    audit_rows=read_csv(phase_audit)
    projected,diag=project(rows,audit_rows)

    leagues={r["provider_league_id"] for r in projected}
    countries={r["country"] for r in projected}
    cells={(r["provider_league_id"],r["season"]) for r in projected}
    statuses=Counter(r["context_status"] for r in projected)
    roles=Counter(r["phase_role"] for r in projected)
    safe_statuses={
        "VALID_REGULAR_RESULTS_DERIVED",
        "VALID_PREMATCH_AWARDED_RESULT_WILL_TAINT",
        "VALID_PREMATCH_NOT_PLAYED_NO_STATE_MUTATION",
    }
    safe_rows=sum(r["context_status"] in safe_statuses for r in projected)
    full=sum(
        r["context_status"] in safe_statuses and r["full_table_available"]=="true"
        for r in projected
    )
    format_blocked=sum(
        r["context_status"] in {
            "BLOCKED_TABLE_PHASE_REQUIRES_SEASON_FORMAT_CONTRACT",
            "BLOCKED_AFTER_UNMODELED_TABLE_PHASE",
        }
        for r in projected
    )
    post_table=statuses.get("POST_TABLE_PLAYOFF_EXCLUDED_FROM_TABLE",0)
    prior_awarded=statuses.get("BLOCKED_PRIOR_AWARDED_RESULT_UNRESOLVED",0)

    status="OK" if (
        diag["source_domestic_rows"]==40989
        and diag["output_rows"]==40989
        and diag["unique_domestic_fixture_ids"]==40989
        and diag["duplicate_domestic_fixture_ids"]==0
        and diag["audit_rows"]==40989
        and diag["audit_unique_fixture_ids"]==40989
        and diag["audit_duplicate_fixture_ids"]==0
        and diag["audit_invalid_rows"]==0
        and diag["source_without_phase_audit"]==0
        and diag["phase_audit_without_source"]==0
        and diag["invalid_kickoff_rows"]==0
        and len(leagues)==16
        and len(countries)==16
        and len(cells)==143
        and roles==Counter({"TABLE_PHASE":40731,"POST_TABLE_PLAYOFF":258})
        and post_table==258
        and all(r["exact_title_relegation_motivation_allowed"]=="false" for r in projected)
    ) else "ATTENTION"

    meta={
        "version":VERSION,"generated_at_utc":iso_now(),"status":status,
        **diag,
        "domestic_league_ids":len(leagues),"countries":len(countries),
        "captured_league_season_cells":len(cells),
        "phase_role_counts":dict(sorted(roles.items())),
        "context_status_counts":dict(sorted(statuses.items())),
        "safe_regular_prematch_rows":safe_rows,
        "safe_regular_rows_with_full_table":full,
        "blocked_table_phase_rows":format_blocked,
        "post_table_playoff_rows":post_table,
        "blocked_prior_awarded_result_rows":prior_awarded,
        "phase_audit_contract":PHASE_AUDIT_CONTRACT,
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
    p.add_argument("--phase-audit",required=True)
    p.add_argument("--out-csv",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.source,a.phase_audit,a.out_csv,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
