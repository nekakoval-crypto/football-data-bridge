#!/usr/bin/env python3
"""Stage80 — historical UEFA-relevant FIFA international-window context.

Input:
  ops/pbk16_all_competition_fixture_history.csv

Output:
  one deterministic context row per PBK16 domestic-league fixture.

This V1 is calendar-level evidence only. It never infers a player's national-team
call-up, travel, appearance, minutes or return time from nationality or club.

Final tournaments are excluded from the fixed-window contour. Player-level
international participation remains UNVERIFIED until direct historical evidence
is added by a separate source.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
from collections import defaultdict
from datetime import datetime, time, timezone
from pathlib import Path

VERSION="PBK_STAGE80_PBK16_INTERNATIONAL_WINDOW_CONTEXT_V1"
CONFIG_VERSION="PBK_STAGE80_UEFA_RELEVANT_FIFA_WINDOWS_2017_2025_V1"

FIELDS=[
    "domestic_fixture_id","provider_league_id","league_name","country","season",
    "round","kickoff_utc","status","home_team_id","home_team","away_team_id","away_team",
    "nearest_window_id","window_start_utc","window_end_utc","window_max_matches",
    "window_notes","window_relation",
    "hours_to_window_start","hours_since_window_end",
    "within_72h_before_window","within_96h_before_window","within_7d_before_window",
    "within_72h_after_window","within_96h_after_window","within_7d_after_window",
    "home_domestic_matches_since_window_end_before_fixture",
    "away_domestic_matches_since_window_end_before_fixture",
    "home_first_domestic_league_match_after_window",
    "away_first_domestic_league_match_after_window",
    "both_first_domestic_league_match_after_window",
    "either_first_domestic_league_match_after_window",
    "player_level_international_status","player_level_reason",
    "final_tournaments_included","non_uefa_only_windows_included",
    "calendar_reference_version","calendar_source_count",
    "calendar_level_only","as_known_calendar_reference","no_match_result_dependency",
    "no_lookahead","provider_calls","historical_backfill_only","research_only",
    "operational_betting_authority","creates_signal","probability_mutation",
    "eligibility_mutation","stake_changes","forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def parse_dt(value):
    try:
        dt=datetime.fromisoformat(str(value or "").replace("Z","+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (TypeError,ValueError):
        return None


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def bool_text(value):
    return "true" if value else "false"


def sval(row,key):
    return str((row or {}).get(key) or "").strip()


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


def load_config(path):
    cfg=json.loads(Path(path).read_text(encoding="utf-8"))
    if cfg.get("version")!=CONFIG_VERSION:
        raise ValueError(f"unexpected config version: {cfg.get('version')}")
    windows=cfg.get("windows") or []
    if len(windows)!=39:
        raise ValueError(f"expected 39 UEFA-relevant windows, got {len(windows)}")
    out=[]
    seen=set()
    previous_end=None
    for item in windows:
        wid=str(item.get("window_id") or "").strip()
        if not wid or wid in seen:
            raise ValueError(f"invalid/duplicate window id: {wid!r}")
        seen.add(wid)
        start=datetime.combine(
            datetime.fromisoformat(item["start_date"]).date(),
            time.min,
            tzinfo=timezone.utc,
        )
        end=datetime.combine(
            datetime.fromisoformat(item["end_date"]).date(),
            time.max,
            tzinfo=timezone.utc,
        )
        if end<=start:
            raise ValueError(f"invalid window range: {wid}")
        if previous_end is not None and start<=previous_end:
            raise ValueError(f"overlapping/out-of-order windows around {wid}")
        previous_end=end
        out.append({
            "window_id":wid,
            "start":start,
            "end":end,
            "max_matches":int(item.get("max_matches") or 0),
            "notes":str(item.get("notes") or ""),
        })
    return cfg,out


def nearest_window(kickoff,windows):
    candidates=[]
    for window in windows:
        start=window["start"]; end=window["end"]
        if start<=kickoff<=end:
            relation="INSIDE"
            distance=0.0
            to_start=None
            since_end=None
        elif kickoff<start:
            relation="BEFORE"
            to_start=(start-kickoff).total_seconds()/3600.0
            since_end=None
            distance=to_start
        else:
            relation="AFTER"
            to_start=None
            since_end=(kickoff-end).total_seconds()/3600.0
            distance=since_end
        candidates.append((distance,window,relation,to_start,since_end))
    return min(candidates,key=lambda x:x[0])


def previous_window(kickoff,windows):
    ended=[w for w in windows if w["end"]<kickoff]
    return ended[-1] if ended else None


def domestic_rows(archive_rows):
    return [
        row for row in archive_rows
        if sval(row,"competition_role")=="DOMESTIC_LEAGUE"
        and sval(row,"fixture_id")
        and parse_dt(row.get("kickoff_utc")) is not None
        and sval(row,"home_team_id")
        and sval(row,"away_team_id")
    ]


def team_domestic_index(rows):
    by=defaultdict(list)
    for row in rows:
        kickoff=parse_dt(row.get("kickoff_utc"))
        fid=sval(row,"fixture_id")
        season=sval(row,"season")
        for key in ("home_team_id","away_team_id"):
            tid=sval(row,key)
            if tid:
                by[(season,tid)].append((kickoff,fid))
    for key in by:
        by[key].sort()
    return by


def count_since_window_before_fixture(index,season,team_id,window_end,kickoff,fixture_id):
    items=index.get((season,team_id),[])
    times=[x[0] for x in items]
    left=bisect.bisect_right(times,window_end)
    right=bisect.bisect_left(times,kickoff)
    count=max(0,right-left)
    return count


def project(archive_rows,cfg,windows):
    domestic=domestic_rows(archive_rows)
    idx=team_domestic_index(domestic)
    out=[]
    invalid=0

    for row in domestic:
        kickoff=parse_dt(row.get("kickoff_utc"))
        if kickoff is None:
            invalid+=1
            continue
        _,near,relation,to_start,since_end=nearest_window(kickoff,windows)
        prev=previous_window(kickoff,windows)

        home_count=""
        away_count=""
        home_first=False
        away_first=False
        if prev is not None:
            season=sval(row,"season")
            home_count=count_since_window_before_fixture(
                idx,season,sval(row,"home_team_id"),prev["end"],kickoff,sval(row,"fixture_id")
            )
            away_count=count_since_window_before_fixture(
                idx,season,sval(row,"away_team_id"),prev["end"],kickoff,sval(row,"fixture_id")
            )
            home_first=home_count==0
            away_first=away_count==0

        before_hours=to_start
        after_hours=since_end
        out.append({
            "domestic_fixture_id":sval(row,"fixture_id"),
            "provider_league_id":sval(row,"provider_competition_id"),
            "league_name":sval(row,"competition_name"),
            "country":sval(row,"country"),
            "season":sval(row,"season"),
            "round":sval(row,"round"),
            "kickoff_utc":sval(row,"kickoff_utc"),
            "status":sval(row,"status"),
            "home_team_id":sval(row,"home_team_id"),
            "home_team":sval(row,"home_team"),
            "away_team_id":sval(row,"away_team_id"),
            "away_team":sval(row,"away_team"),
            "nearest_window_id":near["window_id"],
            "window_start_utc":iso(near["start"]),
            "window_end_utc":iso(near["end"]),
            "window_max_matches":near["max_matches"],
            "window_notes":near["notes"],
            "window_relation":relation,
            "hours_to_window_start":"" if before_hours is None else round(before_hours,3),
            "hours_since_window_end":"" if after_hours is None else round(after_hours,3),
            "within_72h_before_window":bool_text(before_hours is not None and 0<=before_hours<=72),
            "within_96h_before_window":bool_text(before_hours is not None and 0<=before_hours<=96),
            "within_7d_before_window":bool_text(before_hours is not None and 0<=before_hours<=168),
            "within_72h_after_window":bool_text(after_hours is not None and 0<=after_hours<=72),
            "within_96h_after_window":bool_text(after_hours is not None and 0<=after_hours<=96),
            "within_7d_after_window":bool_text(after_hours is not None and 0<=after_hours<=168),
            "home_domestic_matches_since_window_end_before_fixture":home_count,
            "away_domestic_matches_since_window_end_before_fixture":away_count,
            "home_first_domestic_league_match_after_window":bool_text(prev is not None and home_first),
            "away_first_domestic_league_match_after_window":bool_text(prev is not None and away_first),
            "both_first_domestic_league_match_after_window":bool_text(prev is not None and home_first and away_first),
            "either_first_domestic_league_match_after_window":bool_text(prev is not None and (home_first or away_first)),
            "player_level_international_status":"UNVERIFIED",
            "player_level_reason":"Calendar proximity is not evidence of player call-up, travel, appearance, minutes, or return timing",
            "final_tournaments_included":"false",
            "non_uefa_only_windows_included":"false",
            "calendar_reference_version":cfg["version"],
            "calendar_source_count":len(cfg.get("sources") or []),
            "calendar_level_only":"true",
            "as_known_calendar_reference":"true",
            "no_match_result_dependency":"true",
            "no_lookahead":"true",
            "provider_calls":"0",
            "historical_backfill_only":"true",
            "research_only":"true",
            "operational_betting_authority":"false",
            "creates_signal":"false",
            "probability_mutation":"false",
            "eligibility_mutation":"false",
            "stake_changes":"false",
            "forward_journal_mutation":"false",
        })

    out.sort(key=lambda r:(r["kickoff_utc"],r["domestic_fixture_id"]))
    return domestic,out,invalid


def build_meta(archive_rows,domestic,rows,invalid,cfg,windows):
    league_ids={sval(r,"provider_league_id") for r in rows if sval(r,"provider_league_id")}
    window_counts=defaultdict(int)
    for row in rows:
        window_counts[row["nearest_window_id"]]+=1
    return {
        "version":VERSION,
        "generated_at_utc":iso_now(),
        "status":"OK" if len(rows)==len(domestic) and invalid==0 and len(league_ids)==16 else "ATTENTION",
        "source_archive_rows":len(archive_rows),
        "source_domestic_rows":len(domestic),
        "output_rows":len(rows),
        "unique_domestic_fixture_ids":len({r["domestic_fixture_id"] for r in rows}),
        "invalid_domestic_rows":invalid,
        "domestic_anchor_league_ids":len(league_ids),
        "calendar_version":cfg["version"],
        "calendar_windows":len(windows),
        "calendar_sources":len(cfg.get("sources") or []),
        "window_fixture_counts":dict(sorted(window_counts.items())),
        "inside_window_rows":sum(r["window_relation"]=="INSIDE" for r in rows),
        "within_72h_before_rows":sum(r["within_72h_before_window"]=="true" for r in rows),
        "within_96h_before_rows":sum(r["within_96h_before_window"]=="true" for r in rows),
        "within_7d_before_rows":sum(r["within_7d_before_window"]=="true" for r in rows),
        "within_72h_after_rows":sum(r["within_72h_after_window"]=="true" for r in rows),
        "within_96h_after_rows":sum(r["within_96h_after_window"]=="true" for r in rows),
        "within_7d_after_rows":sum(r["within_7d_after_window"]=="true" for r in rows),
        "home_first_domestic_after_window_rows":sum(r["home_first_domestic_league_match_after_window"]=="true" for r in rows),
        "away_first_domestic_after_window_rows":sum(r["away_first_domestic_league_match_after_window"]=="true" for r in rows),
        "both_first_domestic_after_window_rows":sum(r["both_first_domestic_league_match_after_window"]=="true" for r in rows),
        "either_first_domestic_after_window_rows":sum(r["either_first_domestic_league_match_after_window"]=="true" for r in rows),
        "player_level_international_status":"UNVERIFIED",
        "player_level_callup_inference":False,
        "player_level_travel_inference":False,
        "player_level_appearance_inference":False,
        "final_tournaments_included":False,
        "non_uefa_only_windows_included":False,
        "calendar_level_only":True,
        "as_known_calendar_reference":True,
        "no_match_result_dependency":True,
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


def run(source,config,out_csv,meta_out):
    archive=read_csv(source)
    cfg,windows=load_config(config)
    domestic,rows,invalid=project(archive,cfg,windows)
    write_csv(out_csv,rows)
    meta=build_meta(archive,domestic,rows,invalid,cfg,windows)
    write_json(meta_out,meta)
    return meta


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="ops/pbk16_all_competition_fixture_history.csv")
    p.add_argument("--config",default="config/stage80_fifa_uefa_windows_2017_2025.json")
    p.add_argument("--out-csv",required=True)
    p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.source,a.config,a.out_csv,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
