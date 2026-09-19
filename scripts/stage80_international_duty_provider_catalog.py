#!/usr/bin/env python3
"""Stage80 — API-Football senior international duty provider catalog.

One bounded /leagues provider call inventories competition-season coverage that
could support direct player-level national-team evidence.

This is source discovery only:
- candidate senior national-team competitions are pattern-selected for review;
- provider-declared lineup/player-stat coverage is preserved;
- matchday squad/minutes evidence may later be collected from fixture endpoints;
- historical call-up is NOT inferred from nationality, club roster, or this
  coverage catalog;
- no betting/model authority is created.

The raw /leagues response is archived by the shared API-Football broker whenever
PBK raw-archive storage is configured.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

VERSION="PBK_STAGE80_INTERNATIONAL_DUTY_PROVIDER_CATALOG_V1"
DEFAULT_START=2017
DEFAULT_END=2026

POSITIVE_PATTERNS=[
    ("WORLD_CUP_QUALIFICATION",r"world cup.*qualif|qualif.*world cup|\bwc qualification\b"),
    ("WORLD_CUP",r"\bworld cup\b"),
    ("EURO_QUALIFICATION",r"euro.*qualif|qualif.*euro|european championship.*qualif"),
    ("EURO_CHAMPIONSHIP",r"euro championship|european championship"),
    ("NATIONS_LEAGUE",r"nations league"),
    ("COPA_AMERICA",r"copa am[eé]rica"),
    ("AFRICA_CUP_OF_NATIONS",r"africa cup of nations"),
    ("AFRICAN_NATIONS_CHAMPIONSHIP",r"african nations championship"),
    ("ASIAN_CUP",r"\basian cup\b"),
    ("GOLD_CUP",r"gold cup"),
    ("OFC_NATIONS_CUP",r"ofc nations cup"),
    ("ARAB_CUP",r"\barab cup\b"),
    ("CONFEDERATIONS_CUP",r"confederations cup"),
    ("FRIENDLIES",r"\bfriendlies\b|international friendly"),
    ("BALTIC_CUP",r"baltic cup"),
    ("CARIBBEAN_CUP",r"caribbean cup"),
    ("CENTRAL_AMERICAN_CUP",r"central american cup|copa centroamericana"),
]
EXCLUDE_PATTERN=re.compile(
    r"women|woman|girls|\bu[- ]?(?:15|16|17|18|19|20|21|22|23)\b|"
    r"under[- ]?(?:15|16|17|18|19|20|21|22|23)|youth|olympic|"
    r"futsal|beach|club world cup|clubs?\b|champions league|"
    r"libertadores|sudamericana|afc champions|caf champions",
    re.I,
)

FIELDS=[
    "provider_league_id","competition_name","competition_type",
    "provider_country_name","provider_country_code",
    "candidate_family","selection_status","selection_reason",
    "season","season_start","season_end","current_season",
    "coverage_events","coverage_lineups",
    "coverage_fixture_statistics","coverage_player_statistics",
    "coverage_players","coverage_injuries",
    "direct_matchday_squad_evidence_possible",
    "direct_minutes_evidence_possible",
    "historical_callup_evidence_possible",
    "nationality_inference_allowed",
    "future_fixture_backfill_required",
    "research_only","operational_betting_authority","creates_signal",
    "probability_mutation","eligibility_mutation","stake_changes",
    "forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def btext(value):
    return "true" if bool(value) else "false"


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


def nested_bool(obj,*keys):
    cur=obj
    for key in keys:
        if not isinstance(cur,dict):
            return False
        cur=cur.get(key)
    return bool(cur is True)


def classify_candidate(name):
    text=str(name or "").strip()
    if not text:
        return None,"EMPTY_NAME"
    if EXCLUDE_PATTERN.search(text):
        return None,"EXCLUDED_NON_SENIOR_OR_CLUB_PATTERN"
    lower=text.lower()
    for family,pattern in POSITIVE_PATTERNS:
        if re.search(pattern,lower,re.I):
            return family,f"NAME_PATTERN:{family}"
    return None,"NO_SENIOR_NATIONAL_PATTERN"


def normalize_payload(payload,start_year=DEFAULT_START,end_year=DEFAULT_END):
    response=payload.get("response",[]) if isinstance(payload,dict) else []
    rows=[]
    candidate_competitions=set()
    total_competitions=0
    seasons_scanned=0

    for item in response:
        if not isinstance(item,dict):
            continue
        league=item.get("league") or {}
        country=item.get("country") or {}
        league_id=league.get("id")
        name=str(league.get("name") or "").strip()
        if league_id in (None,"") or not name:
            continue
        total_competitions+=1
        family,reason=classify_candidate(name)
        if not family:
            continue
        candidate_competitions.add(str(league_id))

        for season in item.get("seasons") or []:
            if not isinstance(season,dict):
                continue
            try:
                year=int(season.get("year"))
            except (TypeError,ValueError):
                continue
            if year<start_year or year>end_year:
                continue
            seasons_scanned+=1
            coverage=season.get("coverage") or {}
            fixture_cov=coverage.get("fixtures") or {}
            events=bool(fixture_cov.get("events") is True)
            lineups=bool(fixture_cov.get("lineups") is True)
            fixture_stats=bool(fixture_cov.get("statistics_fixtures") is True)
            player_stats=bool(fixture_cov.get("statistics_players") is True)
            players=bool(coverage.get("players") is True)
            injuries=bool(coverage.get("injuries") is True)

            rows.append({
                "provider_league_id":str(league_id),
                "competition_name":name,
                "competition_type":str(league.get("type") or ""),
                "provider_country_name":str(country.get("name") or ""),
                "provider_country_code":str(country.get("code") or ""),
                "candidate_family":family,
                "selection_status":"CANDIDATE_REVIEW",
                "selection_reason":reason,
                "season":year,
                "season_start":str(season.get("start") or ""),
                "season_end":str(season.get("end") or ""),
                "current_season":btext(season.get("current") is True),
                "coverage_events":btext(events),
                "coverage_lineups":btext(lineups),
                "coverage_fixture_statistics":btext(fixture_stats),
                "coverage_player_statistics":btext(player_stats),
                "coverage_players":btext(players),
                "coverage_injuries":btext(injuries),
                # /fixtures/players commonly exposes both used and unused matchday
                # players; lineups is also direct matchday evidence.
                "direct_matchday_squad_evidence_possible":btext(lineups or player_stats),
                "direct_minutes_evidence_possible":btext(player_stats),
                # A matchday lineup/appearance is not proof that a player was
                # formally called up before the match.
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

    rows.sort(key=lambda r:(r["candidate_family"],r["competition_name"],int(r["season"]),int(r["provider_league_id"])))
    return rows,{
        "provider_competitions_seen":total_competitions,
        "candidate_competitions":len(candidate_competitions),
        "candidate_season_rows":len(rows),
        "candidate_seasons_scanned":seasons_scanned,
    }


def run(out_csv,meta_out,start_year=DEFAULT_START,end_year=DEFAULT_END,broker=None):
    if broker is None:
        # Lazy import keeps provider-free unit tests independent from the
        # broker's script-style import path. Real execution is via
        # `python scripts/...py`, where the shared broker imports normally.
        from api_football_broker import ApiFootballBroker
        broker=ApiFootballBroker(max_real_calls=1,default_ttl_seconds=24*3600)
    payload=broker.get("/leagues",{},ttl_seconds=24*3600,force_refresh=True)
    rows,diag=normalize_payload(payload,start_year,end_year)
    stats=broker.stats()

    direct_minutes=sum(r["direct_minutes_evidence_possible"]=="true" for r in rows)
    matchday=sum(r["direct_matchday_squad_evidence_possible"]=="true" for r in rows)
    families=sorted({r["candidate_family"] for r in rows})
    years=sorted({int(r["season"]) for r in rows})

    status="OK" if (
        int(stats.get("real_api_calls") or 0)==1
        and diag["provider_competitions_seen"]>0
        and diag["candidate_competitions"]>0
        and len(rows)>0
        and all(r["selection_status"]=="CANDIDATE_REVIEW" for r in rows)
        and all(r["historical_callup_evidence_possible"]=="false" for r in rows)
        and all(r["nationality_inference_allowed"]=="false" for r in rows)
        and all(r["operational_betting_authority"]=="false" for r in rows)
    ) else "ATTENTION"

    meta={
        "version":VERSION,
        "generated_at_utc":iso_now(),
        "status":status,
        "provider_endpoint":"/leagues",
        "requested_season_start":int(start_year),
        "requested_season_end":int(end_year),
        **diag,
        "candidate_families":families,
        "candidate_years":years,
        "season_rows_with_direct_matchday_squad_evidence_possible":matchday,
        "season_rows_with_direct_minutes_evidence_possible":direct_minutes,
        "historical_callup_evidence_possible":False,
        "nationality_inference_allowed":False,
        "selection_status":"CANDIDATE_REVIEW",
        "selection_policy":"Broad senior-national competition name patterns with explicit youth/women/club exclusions. Human/repository allowlist verification required before fixture backfill.",
        "next_stage":"Verify competition allowlist, then backfill national-team fixtures and direct fixture-player evidence.",
        "provider_calls":int(stats.get("real_api_calls") or 0),
        "logical_requests":int(stats.get("logical_requests") or 0),
        "archive_enabled":bool(stats.get("archive_enabled")),
        "archive_backend":stats.get("archive_backend"),
        "archive_observations":int(stats.get("archive_observations") or 0),
        "archive_errors":int(stats.get("archive_errors") or 0),
        "research_only":True,
        "operational_betting_authority":False,
        "creates_signal":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "forward_journal_mutation":False,
    }
    write_csv(out_csv,rows)
    write_json(meta_out,meta)
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out-csv",default="ops/international_duty_provider_candidates.csv")
    p.add_argument("--meta-out",default="ops/stage80_international_duty_provider_catalog_last_run.json")
    p.add_argument("--start-year",type=int,default=DEFAULT_START)
    p.add_argument("--end-year",type=int,default=DEFAULT_END)
    a=p.parse_args()
    print(json.dumps(run(a.out_csv,a.meta_out,a.start_year,a.end_year),ensure_ascii=False))


if __name__=="__main__":
    main()
