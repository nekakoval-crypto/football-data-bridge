#!/usr/bin/env python3
"""Stage80 — provider-free PBK16 domestic-league phase audit.

Classifies every captured PBK16 domestic-league fixture into:
- TABLE_PHASE: fixture belongs to the league table / split-table competition;
- POST_TABLE_PLAYOFF: qualification, relegation/promotion or other playoff after
  the table phase;
- UNKNOWN: fail-closed catch-all.

The classifier is country/season aware where provider round labels are
ambiguous (notably Scotland 2022). This script does not reconstruct standings
and does not apply any points-halving/carry rule. Any non-regular table phase is
explicitly marked as requiring a later season-format contract.

Research/governance only. No provider calls and no betting/model authority.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

VERSION="PBK_STAGE80_PBK16_DOMESTIC_PHASE_AUDIT_V1"
TRUE_VALUES={"1","true","yes","y"}

OUT_FIELDS=[
    "fixture_id","provider_league_id","league_name","country","season","round",
    "kickoff_utc","status","home_team_id","home_team","away_team_id","away_team",
    "phase_label","phase_role","phase_family","table_result_policy",
    "season_format_contract_required","included_in_future_table_reconstruction",
    "no_lookahead","historical_backfill_only","research_only",
    "operational_betting_authority","creates_signal","probability_mutation",
    "eligibility_mutation","stake_changes","forward_journal_mutation",
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
        w=csv.DictWriter(f,fieldnames=OUT_FIELDS,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def write_json(path,payload):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)


def sval(row,key):
    return str((row or {}).get(key) or "").strip()


def btext(value):
    return "true" if bool(value) else "false"


def phase_label(round_name):
    return re.sub(r"\s*-\s*\d+\s*$","",str(round_name or "").strip()).strip()


def table_phase(country,season,round_name):
    """Return (role,family) using archive-observed provider round semantics."""
    country=str(country or "").strip()
    season=int(str(season or "0") or 0)
    rd=str(round_name or "").strip()
    phase=phase_label(rd)

    if country=="Austria":
        if phase=="Regular Season": return "TABLE_PHASE","REGULAR"
        if phase in {"Championship Round","Championship Group"}: return "TABLE_PHASE","CHAMPIONSHIP_SPLIT"
        if phase=="Relegation Round":
            if season==2020 and rd=="Relegation Round":
                return "POST_TABLE_PLAYOFF","RELEGATION_PLAYOFF"
            return "TABLE_PHASE","RELEGATION_SPLIT"
        if phase=="Relegation Group": return "TABLE_PHASE","RELEGATION_SPLIT"
        if "Play-offs" in phase or phase in {"Semi-finals","Final"}: return "POST_TABLE_PLAYOFF","QUALIFICATION_PLAYOFF"

    if country=="Belgium":
        if phase=="Regular Season": return "TABLE_PHASE","REGULAR"
        if phase in {"Play-offs I","Championship Round","Championship Group"}: return "TABLE_PHASE","CHAMPIONSHIP_SPLIT"
        if phase in {"Conference League Play-off Group","Conference League Group"}: return "TABLE_PHASE","EUROPE_SPLIT"
        if phase=="Relegation Group": return "TABLE_PHASE","RELEGATION_SPLIT"
        if phase=="Relegation Round":
            if season in {2023,2024} and re.fullmatch(r"Relegation Round - [1-6]",rd):
                return "TABLE_PHASE","RELEGATION_SPLIT"
            return "POST_TABLE_PLAYOFF","RELEGATION_PLAYOFF"
        if phase in {"Conference League Play-offs - Final","Quarter-finals","Semi-finals","Final"}: return "POST_TABLE_PLAYOFF","QUALIFICATION_PLAYOFF"

    if country=="Denmark":
        if phase=="Regular Season": return "TABLE_PHASE","REGULAR"
        if phase in {"Championship Round","Championship Group"}: return "TABLE_PHASE","CHAMPIONSHIP_SPLIT"
        if phase in {"Relegation Round","Relegation Group"}: return "TABLE_PHASE","RELEGATION_SPLIT"
        if "Play-offs" in phase or phase=="Final": return "POST_TABLE_PLAYOFF","QUALIFICATION_OR_RELEGATION_PLAYOFF"

    if country=="Scotland":
        if phase in {"1st Phase","Regular Season"}: return "TABLE_PHASE","REGULAR"
        if phase in {"2nd Phase","Championship Round","Championship Group"}: return "TABLE_PHASE","CHAMPIONSHIP_OR_SPLIT"
        if phase=="Relegation Group": return "TABLE_PHASE","RELEGATION_SPLIT"
        if phase=="Relegation Round":
            # 2022 provider data mixes the lower-six split rounds (numbered 1..5)
            # with bare-label promotion/relegation playoff fixtures.
            if season in {2022,2023} and re.fullmatch(r"Relegation Round - [1-5]",rd):
                return "TABLE_PHASE","RELEGATION_SPLIT"
            return "POST_TABLE_PLAYOFF","RELEGATION_PLAYOFF"
        if phase in {"Relegation/Promotion","Quarter-finals","Semi-finals","Final"}:
            return "POST_TABLE_PLAYOFF","RELEGATION_OR_OTHER_PLAYOFF"

    if country=="Lithuania":
        if phase=="Regular Season": return "TABLE_PHASE","REGULAR"
        if phase=="Championship Round": return "TABLE_PHASE","CHAMPIONSHIP_SPLIT"
        if phase in {"Relegation Round","Final"}: return "POST_TABLE_PLAYOFF","RELEGATION_PLAYOFF"

    if country=="Poland":
        if phase=="Regular Season": return "TABLE_PHASE","REGULAR"
        if phase=="Championship Round": return "TABLE_PHASE","CHAMPIONSHIP_SPLIT"
        if phase=="Relegation Round": return "TABLE_PHASE","RELEGATION_SPLIT"

    if country in {"England","Spain","Turkey"}:
        if phase=="Regular Season": return "TABLE_PHASE","REGULAR"

    if country=="Italy":
        if phase=="Regular Season": return "TABLE_PHASE","REGULAR"
        if phase=="Relegation Decider": return "POST_TABLE_PLAYOFF","RELEGATION_DECIDER"

    if country in {"France","Germany","Latvia","Netherlands","Norway","Portugal"}:
        if phase in {"Regular Season","Regular season"}: return "TABLE_PHASE","REGULAR"
        return "POST_TABLE_PLAYOFF","POST_TABLE_PLAYOFF"

    return "UNKNOWN","UNKNOWN"


def result_policy(phase_role,status):
    status=str(status or "").strip()
    if phase_role!="TABLE_PHASE":
        return "NOT_FOR_LEAGUE_TABLE_RECONSTRUCTION"
    if status=="FT":
        return "PLAYED_RESULT_USABLE"
    if status.upper()=="CANC":
        return "NOT_PLAYED_EXCLUDE"
    if status in {"AWD","WO"}:
        return "AWARDED_RESULT_REQUIRES_RULE_EVIDENCE"
    return "UNSUPPORTED_TABLE_STATUS"


def project(rows):
    out=[]
    for row in rows:
        if sval(row,"competition_role")!="DOMESTIC_LEAGUE":
            continue
        role,family=table_phase(sval(row,"country"),sval(row,"season"),sval(row,"round"))
        policy=result_policy(role,sval(row,"status"))
        requires_contract=(role=="TABLE_PHASE" and family!="REGULAR")
        included=role=="TABLE_PHASE" and policy=="PLAYED_RESULT_USABLE"
        out.append({
            "fixture_id":sval(row,"fixture_id"),
            "provider_league_id":sval(row,"provider_competition_id"),
            "league_name":sval(row,"competition_name"),
            "country":sval(row,"country"),
            "season":sval(row,"season"),
            "round":sval(row,"round"),
            "kickoff_utc":sval(row,"kickoff_utc"),
            "status":sval(row,"status"),
            "home_team_id":sval(row,"home_team_id"),"home_team":sval(row,"home_team"),
            "away_team_id":sval(row,"away_team_id"),"away_team":sval(row,"away_team"),
            "phase_label":phase_label(sval(row,"round")),
            "phase_role":role,"phase_family":family,
            "table_result_policy":policy,
            "season_format_contract_required":btext(requires_contract),
            "included_in_future_table_reconstruction":btext(included),
            "no_lookahead":"true","historical_backfill_only":"true","research_only":"true",
            "operational_betting_authority":"false","creates_signal":"false",
            "probability_mutation":"false","eligibility_mutation":"false",
            "stake_changes":"false","forward_journal_mutation":"false",
        })
    return out


def run(source,state_path,out_csv,meta_out):
    rows=read_csv(source)
    state=read_csv(state_path)
    out=project(rows)

    role_counts=Counter(r["phase_role"] for r in out)
    policy_counts=Counter(r["table_result_policy"] for r in out)
    fixture_ids=[r["fixture_id"] for r in out if r["fixture_id"]]
    league_ids={r["provider_league_id"] for r in out if r["provider_league_id"]}
    countries={r["country"] for r in out if r["country"]}
    cells={(r["country"],r["season"]) for r in out if r["country"] and r["season"]}

    domestic_state=[r for r in state if sval(r,"competition_role")=="DOMESTIC_LEAGUE"]
    captured=[r for r in domestic_state if sval(r,"status")=="CAPTURED"]
    unavailable=[r for r in domestic_state if sval(r,"status")=="UNAVAILABLE_PROVIDER_SEASON"]
    pending=[r for r in domestic_state if sval(r,"status")=="PENDING"]
    errors=[r for r in domestic_state if sval(r,"status")=="ERROR"]

    unknown=role_counts.get("UNKNOWN",0)
    unsupported=policy_counts.get("UNSUPPORTED_TABLE_STATUS",0)
    status="OK" if (
        len(out)==40989
        and len(fixture_ids)==40989
        and len(set(fixture_ids))==40989
        and len(league_ids)==16
        and len(countries)==16
        and len(cells)==143
        and role_counts.get("TABLE_PHASE",0)==40731
        and role_counts.get("POST_TABLE_PLAYOFF",0)==258
        and unknown==0
        and policy_counts.get("PLAYED_RESULT_USABLE",0)==40097
        and policy_counts.get("NOT_PLAYED_EXCLUDE",0)==629
        and policy_counts.get("AWARDED_RESULT_REQUIRES_RULE_EVIDENCE",0)==5
        and unsupported==0
        and len(domestic_state)==144
        and len(captured)==143
        and len(unavailable)==1
        and len(pending)==0
        and len(errors)==0
        and {(sval(r,"country"),sval(r,"season")) for r in unavailable}=={("Poland","2017")}
    ) else "ATTENTION"

    meta={
        "version":VERSION,"generated_at_utc":iso_now(),"status":status,
        "source_rows":len(rows),"domestic_rows":len(out),
        "unique_domestic_fixture_ids":len(set(fixture_ids)),
        "countries":sorted(countries),"provider_league_ids":sorted(league_ids,key=lambda x:int(x)),
        "captured_league_season_cells":len(cells),
        "requested_league_season_cells":len(domestic_state),
        "captured_state_cells":len(captured),
        "provider_unavailable_state_cells":len(unavailable),
        "provider_unavailable_cells":[{"country":sval(r,"country"),"season":sval(r,"season")} for r in unavailable],
        "pending_state_cells":len(pending),"error_state_cells":len(errors),
        "phase_role_counts":dict(sorted(role_counts.items())),
        "table_result_policy_counts":dict(sorted(policy_counts.items())),
        "unknown_phase_rows":unknown,
        "unsupported_table_status_rows":unsupported,
        "table_phase_rows_requiring_season_format_contract":sum(
            r["season_format_contract_required"]=="true" for r in out
        ),
        "future_table_reconstruction_usable_rows":sum(
            r["included_in_future_table_reconstruction"]=="true" for r in out
        ),
        "phase_contract_scope":"PBK16_2017_2025_PROVIDER_ROUND_LABELS_V1",
        "points_transform_applied":False,
        "standings_reconstructed":False,
        "no_lookahead":True,"provider_calls":0,"historical_backfill_only":True,
        "research_only":True,"operational_betting_authority":False,
        "creates_signal":False,"probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,
    }
    write_csv(out_csv,out)
    write_json(meta_out,meta)
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="ops/pbk16_all_competition_fixture_history.csv")
    p.add_argument("--state",default="ops/stage80_pbk16_competition_backfill_state.csv")
    p.add_argument("--out-csv",default="ops/pbk16_domestic_phase_audit.csv")
    p.add_argument("--meta-out",default="ops/stage80_pbk16_domestic_phase_audit_last_run.json")
    a=p.parse_args()
    print(json.dumps(run(a.source,a.state,a.out_csv,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
