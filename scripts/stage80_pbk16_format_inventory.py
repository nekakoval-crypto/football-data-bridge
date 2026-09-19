#!/usr/bin/env python3
"""Stage80 — provider-free PBK16 historical domestic-league format inventory.

This stage inventories the already-persisted PBK16 domestic-league fixture
archive before any attempt to generalize Top-5 standings/motivation logic.

It emits one row for every locked league × requested historical season cell
(16 × 9 = 144), including provider-unavailable cells. The inventory describes
observed structural shape only: participant count, fixture counts, per-team
appearance counts, round-label phase markers and whether a season looks like a
single-table candidate or a phased/split competition.

Important:
- this is NOT a standings model;
- this does NOT infer title/relegation rules;
- a balanced fixture shape does not imply that ranking/relegation semantics are
  verified;
- phased/split cells are explicitly blocked from naive Top-5 motivation math;
- provider calls = 0.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

VERSION="PBK_STAGE80_PBK16_FORMAT_INVENTORY_V1"
EXPECTED_LEAGUES=16
EXPECTED_SEASONS=list(range(2017,2026))
FINAL={"FT","AET","PEN"}

PHASE_PATTERNS=[
    ("CHAMPIONSHIP",re.compile(r"championship|champion round|title group",re.I)),
    ("RELEGATION",re.compile(r"relegation|relegation round|relegation group|play[- ]?out",re.I)),
    ("PLAYOFF",re.compile(r"play[- ]?off|playoff",re.I)),
    ("GROUP",re.compile(r"\bgroup\b|group stage",re.I)),
    ("FINALS",re.compile(r"\bfinals?\b",re.I)),
    ("CONFERENCE",re.compile(r"conference",re.I)),
    ("PROMOTION",re.compile(r"promotion|demotion",re.I)),
    ("SPLIT",re.compile(r"split",re.I)),
]

FIELDS=[
    "country","provider_league_id","league_name","season",
    "provider_season_available","backfill_status","state_provider_fixture_rows",
    "archive_rows","unique_fixture_ids","duplicate_fixture_ids",
    "finished_rows","nonfinished_rows","participant_teams",
    "min_team_archive_matches","max_team_archive_matches",
    "min_team_finished_matches","max_team_finished_matches",
    "unique_round_labels","phase_marker_types","phase_marker_round_labels",
    "has_phase_markers","balanced_archive_appearances","balanced_finished_appearances",
    "structure_class","naive_single_table_motivation_allowed",
    "exact_motivation_contract_status","inventory_only","provider_calls",
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


def btext(v):
    return "true" if bool(v) else "false"


def as_int(v):
    try:
        return int(str(v).strip())
    except (TypeError,ValueError):
        return None


def domestic_state_cells(state_rows):
    out={}
    for row in state_rows:
        if sval(row,"competition_role")!="DOMESTIC_LEAGUE":
            continue
        country=sval(row,"country")
        season=as_int(row.get("season"))
        if not country or season is None:
            continue
        key=(country,season)
        if key in out:
            raise ValueError(f"duplicate domestic state cell {key}")
        out[key]=row
    return out


def archive_domestic_cells(archive_rows):
    groups=defaultdict(list)
    for row in archive_rows:
        if sval(row,"competition_role")!="DOMESTIC_LEAGUE":
            continue
        country=sval(row,"country")
        season=as_int(row.get("season"))
        if country and season is not None:
            groups[(country,season)].append(row)
    return groups


def round_inventory(rows):
    labels=sorted({sval(r,"round") for r in rows if sval(r,"round")})
    marker_types=set()
    marker_labels=[]
    for label in labels:
        matched=False
        for name,pattern in PHASE_PATTERNS:
            if pattern.search(label):
                marker_types.add(name)
                matched=True
        if matched:
            marker_labels.append(label)
    return labels,sorted(marker_types),marker_labels


def appearances(rows,finished_only=False):
    counts=Counter()
    for r in rows:
        if finished_only and sval(r,"status").upper() not in FINAL:
            continue
        h=sval(r,"home_team_id") or sval(r,"home_team")
        a=sval(r,"away_team_id") or sval(r,"away_team")
        if h: counts[h]+=1
        if a: counts[a]+=1
    return counts


def structural_class(*,available,rows,phase_markers,archive_counts,finished_counts):
    if not available:
        return "UNAVAILABLE_PROVIDER_SEASON"
    if not rows:
        return "AVAILABLE_BUT_ARCHIVE_EMPTY"
    if phase_markers:
        return "PHASED_OR_SPLIT_CANDIDATE"
    if archive_counts and len(set(archive_counts.values()))==1:
        return "BALANCED_SINGLE_TABLE_CANDIDATE"
    if finished_counts and max(finished_counts.values())-min(finished_counts.values())<=1:
        return "NEAR_BALANCED_SINGLE_TABLE_CANDIDATE"
    return "UNBALANCED_OR_EXCEPTION_CANDIDATE"


def build(state_rows,archive_rows):
    states=domestic_state_cells(state_rows)
    archives=archive_domestic_cells(archive_rows)

    countries=sorted({country for country,_ in states})
    if len(countries)!=EXPECTED_LEAGUES:
        raise ValueError(f"expected {EXPECTED_LEAGUES} domestic leagues, got {len(countries)}")

    expected={(country,season) for country in countries for season in EXPECTED_SEASONS}
    if set(states)!=expected:
        missing=sorted(expected-set(states))
        extra=sorted(set(states)-expected)
        raise ValueError(f"state grid mismatch missing={missing[:5]} extra={extra[:5]}")

    output=[]
    for country,season in sorted(expected):
        s=states[(country,season)]
        rows=archives.get((country,season),[])
        available=sval(s,"provider_season_available").lower()=="true"
        ids=[sval(r,"fixture_id") for r in rows if sval(r,"fixture_id")]
        unique_ids=set(ids)
        finished=[r for r in rows if sval(r,"status").upper() in FINAL]
        archive_counts=appearances(rows)
        finished_counts=appearances(rows,finished_only=True)
        labels,markers,marker_labels=round_inventory(rows)

        class_name=structural_class(
            available=available,rows=rows,phase_markers=markers,
            archive_counts=archive_counts,finished_counts=finished_counts,
        )
        naive_allowed=(
            class_name in {"BALANCED_SINGLE_TABLE_CANDIDATE","NEAR_BALANCED_SINGLE_TABLE_CANDIDATE"}
            and not markers
        )
        participant_ids=set(archive_counts)

        output.append({
            "country":country,
            "provider_league_id":sval(s,"provider_competition_id"),
            "league_name":sval(s,"competition_name"),
            "season":season,
            "provider_season_available":btext(available),
            "backfill_status":sval(s,"status"),
            "state_provider_fixture_rows":sval(s,"provider_fixture_rows"),
            "archive_rows":len(rows),
            "unique_fixture_ids":len(unique_ids),
            "duplicate_fixture_ids":len(ids)-len(unique_ids),
            "finished_rows":len(finished),
            "nonfinished_rows":len(rows)-len(finished),
            "participant_teams":len(participant_ids),
            "min_team_archive_matches":min(archive_counts.values()) if archive_counts else "",
            "max_team_archive_matches":max(archive_counts.values()) if archive_counts else "",
            "min_team_finished_matches":min(finished_counts.values()) if finished_counts else "",
            "max_team_finished_matches":max(finished_counts.values()) if finished_counts else "",
            "unique_round_labels":len(labels),
            "phase_marker_types":"|".join(markers),
            "phase_marker_round_labels":" || ".join(marker_labels[:24]),
            "has_phase_markers":btext(bool(markers)),
            "balanced_archive_appearances":btext(bool(archive_counts) and len(set(archive_counts.values()))==1),
            "balanced_finished_appearances":btext(bool(finished_counts) and len(set(finished_counts.values()))==1),
            "structure_class":class_name,
            "naive_single_table_motivation_allowed":btext(naive_allowed),
            "exact_motivation_contract_status":"UNVERIFIED",
            "inventory_only":"true","provider_calls":0,
            "research_only":"true","operational_betting_authority":"false","creates_signal":"false",
            "probability_mutation":"false","eligibility_mutation":"false",
            "stake_changes":"false","forward_journal_mutation":"false",
        })

    return output


def run(state_path,archive_path,out_csv,meta_out):
    state_rows=read_csv(state_path)
    archive_rows=read_csv(archive_path)
    rows=build(state_rows,archive_rows)

    counts=Counter(r["structure_class"] for r in rows)
    marker_countries=sorted({r["country"] for r in rows if r["has_phase_markers"]=="true"})
    captured=sum(r["backfill_status"]=="CAPTURED" for r in rows)
    unavailable=sum(r["backfill_status"]=="UNAVAILABLE_PROVIDER_SEASON" for r in rows)
    dup=sum(int(r["duplicate_fixture_ids"] or 0) for r in rows)
    archive_domestic=sum(int(r["archive_rows"] or 0) for r in rows)

    status="OK" if (
        len(rows)==144
        and captured+unavailable==144
        and archive_domestic==40989
        and dup==0
        and all(r["exact_motivation_contract_status"]=="UNVERIFIED" for r in rows)
        and all(r["operational_betting_authority"]=="false" for r in rows)
    ) else "ATTENTION"

    meta={
        "version":VERSION,"generated_at_utc":iso_now(),"status":status,
        "locked_leagues":16,"historical_seasons":9,"expected_cells":144,
        "output_cells":len(rows),"captured_cells":captured,
        "unavailable_provider_season_cells":unavailable,
        "domestic_archive_rows":archive_domestic,
        "duplicate_fixture_ids":dup,
        "structure_class_counts":dict(sorted(counts.items())),
        "countries_with_phase_markers":marker_countries,
        "countries_with_phase_markers_count":len(marker_countries),
        "naive_single_table_candidate_cells":sum(
            r["naive_single_table_motivation_allowed"]=="true" for r in rows
        ),
        "exact_motivation_contract_verified_cells":0,
        "inventory_semantics":"Structural archive inventory only. No title/relegation rules inferred.",
        "provider_calls":0,"research_only":True,
        "operational_betting_authority":False,"creates_signal":False,
        "probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,
    }
    write_csv(out_csv,rows)
    write_json(meta_out,meta)
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--state",required=True)
    p.add_argument("--archive",required=True)
    p.add_argument("--out-csv",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.state,a.archive,a.out_csv,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
