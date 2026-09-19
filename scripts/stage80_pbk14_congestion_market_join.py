#!/usr/bin/env python3
"""Stage80 — PBK14 historical market × PBK16 competition-congestion join.

Only conservative AUTO/HIGH fixture identities are admitted.

The join is deterministic:
- Football-Data normalized historical market row by historical_match_id;
- PBK14 identity bridge AUTO/HIGH row by historical_match_id;
- PBK16 congestion row by API-Football domestic fixture_id.

REVIEW/UNMAPPED bridge rows are excluded by construction. Final scores used by
identity resolution never become congestion features. Congestion inputs remain
strictly prior / no-lookahead.

This is research-only and cannot create probability, EV/value, R1/R2/R3
eligibility, WATCH/promotion state, stake or Forward journal entries.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

VERSION="PBK_STAGE80_PBK14_CONGESTION_MARKET_JOIN_V1"
ELIGIBLE={"AUTO","HIGH"}

MARKET_FIELDS=[
    "historical_match_id","league_code","league_name","country","season_label",
    "date_iso","time_local","home_team","away_team",
    "ft_home_goals","ft_away_goals","ft_result",
    "b365_close_home","b365_close_draw","b365_close_away",
    "avg_close_home","avg_close_draw","avg_close_away",
    "b365_close_over_25","b365_close_under_25",
    "avg_close_over_25","avg_close_under_25",
]

CONGESTION_FIELDS=[
    "home_prev_nonleague_fixture_id","home_prev_nonleague_competition_id",
    "home_prev_nonleague_competition_name","home_prev_nonleague_competition_role",
    "home_prev_nonleague_kickoff_utc","home_hours_since_prev_nonleague",
    "home_days_since_prev_nonleague","home_prev_nonleague_was_thursday",
    "home_prev_nonleague_was_uefa","home_prev_nonleague_was_domestic_cup",
    "home_prev_nonleague_team_result","home_nonleague_matches_prev_7d",
    "home_nonleague_matches_prev_14d","home_uefa_matches_prev_7d",
    "home_domestic_cup_matches_prev_7d",
    "away_prev_nonleague_fixture_id","away_prev_nonleague_competition_id",
    "away_prev_nonleague_competition_name","away_prev_nonleague_competition_role",
    "away_prev_nonleague_kickoff_utc","away_hours_since_prev_nonleague",
    "away_days_since_prev_nonleague","away_prev_nonleague_was_thursday",
    "away_prev_nonleague_was_uefa","away_prev_nonleague_was_domestic_cup",
    "away_prev_nonleague_team_result","away_nonleague_matches_prev_7d",
    "away_nonleague_matches_prev_14d","away_uefa_matches_prev_7d",
    "away_domestic_cup_matches_prev_7d",
    "either_team_prev_nonleague_within_72h","either_team_prev_nonleague_within_96h",
    "either_team_prev_uefa_within_72h","either_team_prev_uefa_within_96h",
    "either_team_prev_domestic_cup_within_72h",
    "either_team_prev_domestic_cup_within_96h",
    "either_team_previous_nonleague_was_thursday",
]

FIELDS=[
    "historical_match_id","api_fixture_id","mapping_status","mapping_reason",
    "provider_league_id","season_start","api_kickoff_utc",
    *[x for x in MARKET_FIELDS if x!="historical_match_id"],
    *CONGESTION_FIELDS,
    "strictly_prior_fixture_evidence_only","future_schedule_used","no_lookahead",
    "identity_final_score_evidence_only","fuzzy_string_matching_used",
    "one_to_one_verified","historical_backfill_only","research_only",
    "operational_betting_authority","creates_signal","probability_mutation",
    "eligibility_mutation","stake_changes","forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def sval(row,key):
    return str((row or {}).get(key) or "").strip()


def is_true(value):
    return str(value or "").strip().lower() in {"1","true","yes","y"}


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


def unique_index(rows,key):
    out={}
    duplicates=set()
    for row in rows:
        value=sval(row,key)
        if not value:
            continue
        if value in out:
            duplicates.add(value)
        else:
            out[value]=row
    return out,duplicates


def valid_bridge_row(row):
    return (
        sval(row,"historical_match_id")
        and sval(row,"api_fixture_id")
        and sval(row,"mapping_status") in ELIGIBLE
        and sval(row,"fuzzy_string_matching_used")=="false"
        and is_true(row.get("one_to_one_verified"))
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    )


def valid_congestion_row(row):
    return (
        sval(row,"domestic_fixture_id")
        and is_true(row.get("strictly_prior_fixture_evidence_only"))
        and not is_true(row.get("future_schedule_used"))
        and is_true(row.get("no_lookahead"))
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    )


def project(markets,bridge,congestion):
    market_by_id,market_dupes=unique_index(markets,"historical_match_id")
    congestion_by_id,congestion_dupes=unique_index(congestion,"domestic_fixture_id")
    bridge_eligible=[r for r in bridge if valid_bridge_row(r)]
    bridge_by_mid,bridge_mid_dupes=unique_index(bridge_eligible,"historical_match_id")
    bridge_fixture_counts=Counter(sval(r,"api_fixture_id") for r in bridge_eligible)
    bridge_fixture_dupes={k for k,v in bridge_fixture_counts.items() if k and v>1}

    rows=[]
    missing_market=[]
    missing_congestion=[]
    for mid,b in sorted(bridge_by_mid.items()):
        fixture_id=sval(b,"api_fixture_id")
        m=market_by_id.get(mid)
        c=congestion_by_id.get(fixture_id)
        if m is None:
            missing_market.append(mid)
            continue
        if c is None:
            missing_congestion.append(fixture_id)
            continue

        out={
            "historical_match_id":mid,
            "api_fixture_id":fixture_id,
            "mapping_status":sval(b,"mapping_status"),
            "mapping_reason":sval(b,"mapping_reason"),
            "provider_league_id":sval(b,"provider_league_id"),
            "season_start":sval(b,"season_start"),
            "api_kickoff_utc":sval(b,"api_kickoff_utc"),
        }
        for field in MARKET_FIELDS:
            if field!="historical_match_id":
                out[field]=sval(m,field)
        for field in CONGESTION_FIELDS:
            out[field]=sval(c,field)
        out.update({
            "strictly_prior_fixture_evidence_only":"true",
            "future_schedule_used":"false",
            "no_lookahead":"true",
            "identity_final_score_evidence_only":"true",
            "fuzzy_string_matching_used":"false",
            "one_to_one_verified":"true",
            "historical_backfill_only":"true",
            "research_only":"true",
            "operational_betting_authority":"false",
            "creates_signal":"false",
            "probability_mutation":"false",
            "eligibility_mutation":"false",
            "stake_changes":"false",
            "forward_journal_mutation":"false",
        })
        rows.append(out)

    rows.sort(key=lambda r:(r["date_iso"],r["league_code"],r["home_team"],r["away_team"]))
    diagnostics={
        "market_rows":len(markets),
        "market_duplicate_ids":len(market_dupes),
        "bridge_rows":len(bridge),
        "bridge_eligible_rows":len(bridge_eligible),
        "bridge_eligible_unique_historical_ids":len(bridge_by_mid),
        "bridge_eligible_duplicate_historical_ids":len(bridge_mid_dupes),
        "bridge_eligible_duplicate_api_fixture_ids":len(bridge_fixture_dupes),
        "congestion_rows":len(congestion),
        "congestion_duplicate_fixture_ids":len(congestion_dupes),
        "joined_rows":len(rows),
        "missing_market_rows":len(missing_market),
        "missing_congestion_rows":len(missing_congestion),
        "missing_market_sample":missing_market[:20],
        "missing_congestion_sample":missing_congestion[:20],
    }
    return rows,diagnostics


def complete_triplet(row,keys):
    vals=[]
    for key in keys:
        raw=sval(row,key)
        try:
            val=float(raw)
        except ValueError:
            return False
        if val<=1.0:
            return False
        vals.append(val)
    return len(vals)==len(keys)


def has_close_1x2(row):
    return complete_triplet(row,["avg_close_home","avg_close_draw","avg_close_away"]) or complete_triplet(
        row,["b365_close_home","b365_close_draw","b365_close_away"]
    )


def has_close_total25(row):
    return complete_triplet(row,["avg_close_over_25","avg_close_under_25"]) or complete_triplet(
        row,["b365_close_over_25","b365_close_under_25"]
    )


def build_meta(rows,diag):
    by_league=defaultdict(int)
    by_season=defaultdict(int)
    by_mapping=Counter()
    for row in rows:
        by_league[row["league_code"]]+=1
        by_season[row["season_start"]]+=1
        by_mapping[row["mapping_status"]]+=1
    return {
        "version":VERSION,
        "generated_at_utc":iso_now(),
        **diag,
        "join_coverage_pct":round(100.0*len(rows)/diag["bridge_eligible_rows"],3) if diag["bridge_eligible_rows"] else 0.0,
        "rows_by_league":dict(sorted(by_league.items())),
        "rows_by_season_start":dict(sorted(by_season.items())),
        "rows_by_mapping_status":dict(sorted(by_mapping.items())),
        "closing_1x2_matches":sum(has_close_1x2(r) for r in rows),
        "closing_total25_matches":sum(has_close_total25(r) for r in rows),
        "rows_either_prev_nonleague_72h":sum(is_true(r.get("either_team_prev_nonleague_within_72h")) for r in rows),
        "rows_either_prev_nonleague_96h":sum(is_true(r.get("either_team_prev_nonleague_within_96h")) for r in rows),
        "rows_either_prev_uefa_72h":sum(is_true(r.get("either_team_prev_uefa_within_72h")) for r in rows),
        "rows_either_prev_uefa_96h":sum(is_true(r.get("either_team_prev_uefa_within_96h")) for r in rows),
        "rows_either_prev_cup_72h":sum(is_true(r.get("either_team_prev_domestic_cup_within_72h")) for r in rows),
        "rows_either_prev_cup_96h":sum(is_true(r.get("either_team_prev_domestic_cup_within_96h")) for r in rows),
        "rows_previous_nonleague_thursday":sum(is_true(r.get("either_team_previous_nonleague_was_thursday")) for r in rows),
        "review_unmapped_excluded":True,
        "fuzzy_string_matching_used":False,
        "strictly_prior_fixture_evidence_only":True,
        "future_schedule_used":False,
        "no_lookahead":True,
        "provider_calls":0,
        "historical_backfill_only":True,
        "research_only":True,
        "operational_betting_authority":False,
        "creates_signal":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "forward_journal_mutation":False,
    }


def run(markets_path,bridge_path,congestion_path,out_csv,meta_out):
    markets=read_csv(markets_path)
    bridge=read_csv(bridge_path)
    congestion=read_csv(congestion_path)
    rows,diag=project(markets,bridge,congestion)
    write_csv(out_csv,rows)
    meta=build_meta(rows,diag)
    Path(meta_out).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--markets",required=True)
    p.add_argument("--bridge",default="ops/pbk14_football_data_fixture_bridge.csv")
    p.add_argument("--congestion",default="ops/pbk16_competition_congestion_research.csv")
    p.add_argument("--out-csv",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.markets,a.bridge,a.congestion,a.out_csv,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
