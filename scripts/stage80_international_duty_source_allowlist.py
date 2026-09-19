#!/usr/bin/env python3
"""Stage80 — explicit PBK international-duty source allowlist.

Consumes the provider-discovery candidate catalog and turns broad name-pattern
candidates into an explicit, auditable source selection for PBK16 player-level
international-duty research.

No provider calls are made here. Every observed candidate competition must be
either explicitly ALLOW or explicitly REJECT; unknown IDs fail closed.

Important evidence boundary:
- ALLOW means "eligible data source for later fixture/player evidence backfill";
- it does NOT mean a player was called up, travelled, appeared, or played;
- nationality remains unusable as participation evidence;
- direct minutes evidence still depends on provider-declared season coverage and
  a later fixture/player backfill.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

VERSION="PBK_STAGE80_INTERNATIONAL_DUTY_SOURCE_ALLOWLIST_V1"

ALLOWED={
    "1":"World Cup",
    "4":"Euro Championship",
    "5":"UEFA Nations League",
    "6":"Africa Cup of Nations",
    "7":"Asian Cup",
    "9":"Copa America",
    "10":"Friendlies",
    "21":"Confederations Cup",
    "22":"CONCACAF Gold Cup",
    "29":"World Cup - Qualification Africa",
    "30":"World Cup - Qualification Asia",
    "31":"World Cup - Qualification CONCACAF",
    "32":"World Cup - Qualification Europe",
    "33":"World Cup - Qualification Oceania",
    "34":"World Cup - Qualification South America",
    "35":"Asian Cup - Qualification",
    "36":"Africa Cup of Nations - Qualification",
    "37":"World Cup - Qualification Intercontinental Play-offs",
    "536":"CONCACAF Nations League",
    "806":"OFC Nations Cup",
    "808":"CONCACAF Nations League - Qualification",
    "849":"Baltic Cup",
    "858":"CONCACAF Gold Cup - Qualification",
    "860":"Arab Cup",
    "960":"Euro Championship - Qualification",
}

REJECTED={
    "19":(
        "African Nations Championship",
        "PBK16_PLAYER_INELIGIBLE_WHILE_BASED_ABROAD_CHAN_DOMESTIC_LEAGUE_ONLY",
    ),
    "1163":(
        "African Nations Championship - Qualification",
        "PBK16_PLAYER_INELIGIBLE_WHILE_BASED_ABROAD_CHAN_DOMESTIC_LEAGUE_ONLY",
    ),
    "926":(
        "Copa America Femenina",
        "WOMENS_COMPETITION_OUT_OF_PBK_MENS_SCOPE",
    ),
    "1028":(
        "CONCACAF Central American Cup",
        "CLUB_COMPETITION_NOT_NATIONAL_TEAM_DUTY",
    ),
    "1213":(
        "Kings World Cup Nations",
        "NON_FEDERATION_SENIOR_NATIONAL_TEAM_CONTOUR_OUT_OF_SCOPE",
    ),
}

ALLOW_FIELDS=[
    "provider_league_id","competition_name","competition_type",
    "provider_country_name","provider_country_code","candidate_family",
    "season","season_start","season_end","current_season",
    "coverage_events","coverage_lineups","coverage_fixture_statistics",
    "coverage_player_statistics","coverage_players","coverage_injuries",
    "direct_matchday_squad_evidence_possible","direct_minutes_evidence_possible",
    "evidence_tier","player_evidence_backfill_eligible","fixture_backfill_priority",
    "pbk_source_selection_status","pbk_source_selection_reason",
    "historical_callup_evidence_possible","nationality_inference_allowed",
    "future_fixture_backfill_required","research_only",
    "operational_betting_authority","creates_signal","probability_mutation",
    "eligibility_mutation","stake_changes","forward_journal_mutation",
]

AUDIT_FIELDS=[
    "provider_league_id","competition_name","candidate_family",
    "decision","decision_reason","season_rows",
    "matchday_evidence_season_rows","minutes_evidence_season_rows",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path,fields,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def write_json(path,payload):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)


def evidence_tier(row):
    if str(row.get("direct_minutes_evidence_possible") or "").lower()=="true":
        return "DIRECT_MINUTES"
    if str(row.get("direct_matchday_squad_evidence_possible") or "").lower()=="true":
        return "DIRECT_MATCHDAY_SQUAD"
    return "FIXTURE_ONLY"


def priority_for(tier):
    return {"DIRECT_MINUTES":1,"DIRECT_MATCHDAY_SQUAD":2,"FIXTURE_ONLY":9}[tier]


def select(rows):
    groups=defaultdict(list)
    for row in rows:
        pid=str(row.get("provider_league_id") or "").strip()
        if pid:
            groups[pid].append(row)

    allow_rows=[]
    audit_rows=[]
    unknown=[]
    name_mismatches=[]

    for pid in sorted(groups,key=lambda x:int(x)):
        items=groups[pid]
        names={str(r.get("competition_name") or "").strip() for r in items}
        if len(names)!=1:
            name_mismatches.append(pid)
            continue
        name=next(iter(names))
        family=str(items[0].get("candidate_family") or "")

        if pid in ALLOWED:
            if name!=ALLOWED[pid]:
                name_mismatches.append(pid)
                continue
            decision="ALLOW"
            reason="EXPLICIT_PBK16_SENIOR_NATIONAL_SOURCE"
            for row in items:
                tier=evidence_tier(row)
                out=dict(row)
                out.update({
                    "evidence_tier":tier,
                    "player_evidence_backfill_eligible":"true" if tier!="FIXTURE_ONLY" else "false",
                    "fixture_backfill_priority":priority_for(tier),
                    "pbk_source_selection_status":"EXPLICIT_ALLOWLIST",
                    "pbk_source_selection_reason":reason,
                    "historical_callup_evidence_possible":"false",
                    "nationality_inference_allowed":"false",
                    "future_fixture_backfill_required":"true",
                    "research_only":"true",
                    "operational_betting_authority":"false",
                    "creates_signal":"false",
                    "probability_mutation":"false",
                    "eligibility_mutation":"false",
                    "stake_changes":"false",
                    "forward_journal_mutation":"false",
                })
                allow_rows.append(out)
        elif pid in REJECTED:
            expected,reason=REJECTED[pid]
            if name!=expected:
                name_mismatches.append(pid)
                continue
            decision="REJECT"
        else:
            unknown.append(pid)
            decision="UNREVIEWED"
            reason="UNKNOWN_PROVIDER_COMPETITION_ID_FAIL_CLOSED"

        audit_rows.append({
            "provider_league_id":pid,
            "competition_name":name,
            "candidate_family":family,
            "decision":decision,
            "decision_reason":reason,
            "season_rows":len(items),
            "matchday_evidence_season_rows":sum(
                str(r.get("direct_matchday_squad_evidence_possible") or "").lower()=="true"
                for r in items
            ),
            "minutes_evidence_season_rows":sum(
                str(r.get("direct_minutes_evidence_possible") or "").lower()=="true"
                for r in items
            ),
        })

    allow_rows.sort(key=lambda r:(int(r["fixture_backfill_priority"]),int(r["season"])*-1,int(r["provider_league_id"])))
    audit_rows.sort(key=lambda r:int(r["provider_league_id"]))
    return allow_rows,audit_rows,{
        "unknown_provider_competition_ids":unknown,
        "name_mismatch_provider_competition_ids":name_mismatches,
    }


def run(source,allow_out,audit_out,meta_out):
    source_rows=read_csv(source)
    allow_rows,audit_rows,diag=select(source_rows)

    source_ids={str(r.get("provider_league_id") or "").strip() for r in source_rows if str(r.get("provider_league_id") or "").strip()}
    allow_ids={r["provider_league_id"] for r in audit_rows if r["decision"]=="ALLOW"}
    reject_ids={r["provider_league_id"] for r in audit_rows if r["decision"]=="REJECT"}
    decisions=Counter(r["decision"] for r in audit_rows)
    tiers=Counter(r["evidence_tier"] for r in allow_rows)

    status="OK" if (
        len(source_rows)==92
        and len(source_ids)==30
        and len(audit_rows)==30
        and len(allow_ids)==25
        and len(reject_ids)==5
        and not diag["unknown_provider_competition_ids"]
        and not diag["name_mismatch_provider_competition_ids"]
        and allow_ids==set(ALLOWED)
        and reject_ids==set(REJECTED)
        and len(allow_rows)==80
        and all(r["pbk_source_selection_status"]=="EXPLICIT_ALLOWLIST" for r in allow_rows)
        and all(r["historical_callup_evidence_possible"]=="false" for r in allow_rows)
        and all(r["nationality_inference_allowed"]=="false" for r in allow_rows)
        and all(r["operational_betting_authority"]=="false" for r in allow_rows)
    ) else "ATTENTION"

    meta={
        "version":VERSION,
        "generated_at_utc":iso_now(),
        "status":status,
        "source_candidate_rows":len(source_rows),
        "source_candidate_competitions_with_inrange_seasons":len(source_ids),
        "selection_audit_rows":len(audit_rows),
        "allowed_competitions":len(allow_ids),
        "rejected_competitions":len(reject_ids),
        "allowlisted_competition_season_rows":len(allow_rows),
        "decision_counts":dict(sorted(decisions.items())),
        "evidence_tier_counts":dict(sorted(tiers.items())),
        "allowlisted_matchday_evidence_season_rows":sum(
            r["direct_matchday_squad_evidence_possible"]=="true" for r in allow_rows
        ),
        "allowlisted_minutes_evidence_season_rows":sum(
            r["direct_minutes_evidence_possible"]=="true" for r in allow_rows
        ),
        "allowlisted_fixture_only_season_rows":sum(
            r["evidence_tier"]=="FIXTURE_ONLY" for r in allow_rows
        ),
        **diag,
        "historical_callup_evidence_possible":False,
        "nationality_inference_allowed":False,
        "provider_calls":0,
        "research_only":True,
        "operational_betting_authority":False,
        "creates_signal":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "forward_journal_mutation":False,
        "next_stage":"Build durable national-team fixture backfill state from the 80 allowlisted competition-season rows; prioritize DIRECT_MINUTES then DIRECT_MATCHDAY_SQUAD.",
    }
    write_csv(allow_out,ALLOW_FIELDS,allow_rows)
    write_csv(audit_out,AUDIT_FIELDS,audit_rows)
    write_json(meta_out,meta)
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="ops/international_duty_provider_candidates.csv")
    p.add_argument("--allow-out",default="ops/international_duty_source_allowlist.csv")
    p.add_argument("--audit-out",default="ops/international_duty_source_selection_audit.csv")
    p.add_argument("--meta-out",default="ops/stage80_international_duty_source_allowlist_last_run.json")
    a=p.parse_args()
    print(json.dumps(run(a.source,a.allow_out,a.audit_out,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
