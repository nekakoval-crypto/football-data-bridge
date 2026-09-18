#!/usr/bin/env python3
"""Stage80 — resumable API-Football Top-5 referee historical backfill.

Historical research/archive only. Uses the shared broker and shared daily budget.
It captures one /fixtures?league&season payload per league-season cell, persists
fixture/referee evidence, and derives league-scoped referee/team summaries.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import stage71_observation_audit as audit
from api_football_broker import ApiFootballBrokerError, get_broker, api_get

OPS = Path(os.getenv("OPS_DIR", "ops"))
CONFIG = Path("config/stage80_api_football_top5_referee_9seasons.json")
ARCHIVE = OPS / "top5_referee_fixture_history.csv"
PROFILES = OPS / "top5_referee_profiles_research.csv"
TEAM_SPLITS = OPS / "top5_referee_team_splits_research.csv"
QUERY_STATE = OPS / "stage80_top5_referee_backfill_state.csv"
META = OPS / "stage80_top5_referee_backfill_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"
VERSION = "PBK_STAGE80_API_FOOTBALL_TOP5_REFEREE_BACKFILL_V1"

FINAL = {"FT", "AET", "PEN"}

ARCHIVE_FIELDS = [
    "fixture_id","provider_league_id","league_name","country","season","round",
    "kickoff_utc","status","referee","venue_id","venue_name","venue_city",
    "home_team_id","home_team","away_team_id","away_team",
    "home_goals","away_goals","result","captured_at_utc","source",
    "historical_backfill_only","research_only","operational_betting_authority",
]
STATE_FIELDS = [
    "provider_league_id","league_name","country","season","status",
    "attempt_count","last_attempt_at_utc","fixture_rows","referee_rows","error",
]
PROFILE_FIELDS = [
    "provider_league_id","league_name","country","referee","matches","season_count",
    "first_date","last_date","unique_teams","home_wins","draws","away_wins",
    "home_win_pct","draw_pct","away_win_pct","goal_observed_matches","total_goals",
    "goals_per_observed_match","source_scope","cards_available","fouls_available",
    "penalties_available","research_only","operational_betting_authority",
]
TEAM_FIELDS = [
    "provider_league_id","league_name","country","referee","team_id","team",
    "matches","home_matches","away_matches","wins","draws","losses","win_pct",
    "draw_pct","loss_pct","points","points_per_match","goal_observed_matches",
    "goals_for","goals_against","goal_difference","first_date","last_date",
    "season_count","source_scope","cards_available","fouls_available",
    "penalties_available","research_only","operational_betting_authority",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def read_csv(path):
    if not Path(path).exists():
        return []
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    tmp.replace(path)


def write_json(path, payload):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)


def load_config(path=CONFIG):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    matrix=[
        {**league, "season":int(season)}
        for season in data["seasons"] for league in data["leagues"]
    ]
    if len(matrix) != int(data.get("expected_queries") or 0):
        raise ValueError("Top5 referee matrix size does not match expected_queries")
    return data,matrix


def state_key(row):
    return (str(row.get("provider_league_id") or ""), str(row.get("season") or ""))


def archive_key(row):
    return str(row.get("fixture_id") or "").strip()


def as_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError,ValueError):
        try:
            return int(float(value))
        except (TypeError,ValueError):
            return None


def result_code(status, home, away):
    if status not in FINAL or home is None or away is None:
        return ""
    if home>away: return "H"
    if home<away: return "A"
    return "D"


def normalize_payload(payload, spec, captured_at):
    rows=[]
    for item in payload.get("response") or []:
        fixture=item.get("fixture") or {}
        league=item.get("league") or {}
        teams=item.get("teams") or {}
        goals=item.get("goals") or {}
        fid=str(fixture.get("id") or "").strip()
        if not fid:
            continue
        home_goals=as_int(goals.get("home"))
        away_goals=as_int(goals.get("away"))
        status=str((fixture.get("status") or {}).get("short") or "").strip()
        venue=fixture.get("venue") or {}
        home=teams.get("home") or {}; away=teams.get("away") or {}
        rows.append({
            "fixture_id":fid,
            "provider_league_id":str(league.get("id") or spec["provider_league_id"]),
            "league_name":str(league.get("name") or spec["league_name"]),
            "country":str(league.get("country") or spec["country"]),
            "season":str(league.get("season") or spec["season"]),
            "round":str(league.get("round") or ""),
            "kickoff_utc":str(fixture.get("date") or ""),
            "status":status,
            "referee":str(fixture.get("referee") or "").strip(),
            "venue_id":str(venue.get("id") or ""),
            "venue_name":str(venue.get("name") or ""),
            "venue_city":str(venue.get("city") or ""),
            "home_team_id":str(home.get("id") or ""),
            "home_team":str(home.get("name") or ""),
            "away_team_id":str(away.get("id") or ""),
            "away_team":str(away.get("name") or ""),
            "home_goals":"" if home_goals is None else home_goals,
            "away_goals":"" if away_goals is None else away_goals,
            "result":result_code(status,home_goals,away_goals),
            "captured_at_utc":captured_at,
            "source":"API-Football /fixtures?league&season",
            "historical_backfill_only":"true",
            "research_only":"true",
            "operational_betting_authority":"false",
        })
    return rows


def merge_archive(existing, incoming):
    merged={archive_key(r):dict(r) for r in existing if archive_key(r)}
    for row in incoming:
        key=archive_key(row)
        if key:
            merged[key]=dict(row)
    return sorted(merged.values(), key=lambda r:(r.get("kickoff_utc",""),r.get("fixture_id","")))


def pct(n,d):
    return round(100.0*n/d,2) if d else 0.0


def rate(n,d):
    return round(n/d,3) if d else None


def date_only(value):
    return str(value or "")[:10]


def aggregate_profiles(rows):
    data={}
    for r in rows:
        referee=str(r.get("referee") or "").strip()
        if not referee: continue
        key=(str(r["provider_league_id"]),referee)
        x=data.setdefault(key,{
            "league_name":r["league_name"],"country":r["country"],"matches":0,
            "seasons":set(),"dates":[],"teams":set(),"H":0,"D":0,"A":0,
            "goal_obs":0,"total_goals":0,
        })
        x["matches"]+=1; x["seasons"].add(str(r.get("season") or ""))
        d=date_only(r.get("kickoff_utc"))
        if d: x["dates"].append(d)
        for t in ("home_team_id","away_team_id"):
            if str(r.get(t) or ""): x["teams"].add(str(r[t]))
        res=str(r.get("result") or "")
        if res in {"H","D","A"}: x[res]+=1
        hg=as_int(r.get("home_goals")); ag=as_int(r.get("away_goals"))
        if hg is not None and ag is not None:
            x["goal_obs"]+=1; x["total_goals"]+=hg+ag
    out=[]
    for (league_id,referee),x in sorted(data.items()):
        m=x["matches"]
        out.append({
            "provider_league_id":league_id,"league_name":x["league_name"],
            "country":x["country"],"referee":referee,"matches":m,
            "season_count":len([s for s in x["seasons"] if s]),
            "first_date":min(x["dates"]) if x["dates"] else "",
            "last_date":max(x["dates"]) if x["dates"] else "",
            "unique_teams":len(x["teams"]),"home_wins":x["H"],"draws":x["D"],
            "away_wins":x["A"],"home_win_pct":pct(x["H"],m),
            "draw_pct":pct(x["D"],m),"away_win_pct":pct(x["A"],m),
            "goal_observed_matches":x["goal_obs"],"total_goals":x["total_goals"],
            "goals_per_observed_match":rate(x["total_goals"],x["goal_obs"]),
            "source_scope":"TOP5_9_SEASONS_API_FOOTBALL",
            "cards_available":"false","fouls_available":"false",
            "penalties_available":"false","research_only":"true",
            "operational_betting_authority":"false",
        })
    return out


def aggregate_team_splits(rows):
    data={}
    for r in rows:
        referee=str(r.get("referee") or "").strip()
        if not referee: continue
        res=str(r.get("result") or "")
        hg=as_int(r.get("home_goals")); ag=as_int(r.get("away_goals"))
        for side in ("home","away"):
            tid=str(r.get(side+"_team_id") or "").strip()
            team=str(r.get(side+"_team") or "").strip()
            if not tid or not team: continue
            key=(str(r["provider_league_id"]),referee,tid)
            x=data.setdefault(key,{
                "league_name":r["league_name"],"country":r["country"],"team":team,
                "matches":0,"home":0,"away":0,"wins":0,"draws":0,"losses":0,
                "points":0,"goal_obs":0,"gf":0,"ga":0,"dates":[],"seasons":set(),
            })
            x["matches"]+=1; x[side]+=1; x["seasons"].add(str(r.get("season") or ""))
            d=date_only(r.get("kickoff_utc"))
            if d: x["dates"].append(d)
            won=(res=="H" and side=="home") or (res=="A" and side=="away")
            lost=(res=="A" and side=="home") or (res=="H" and side=="away")
            if won: x["wins"]+=1; x["points"]+=3
            elif res=="D": x["draws"]+=1; x["points"]+=1
            elif lost: x["losses"]+=1
            if hg is not None and ag is not None:
                x["goal_obs"]+=1
                own,opp=(hg,ag) if side=="home" else (ag,hg)
                x["gf"]+=own; x["ga"]+=opp
    out=[]
    for (league_id,referee,tid),x in sorted(data.items()):
        m=x["matches"]
        out.append({
            "provider_league_id":league_id,"league_name":x["league_name"],
            "country":x["country"],"referee":referee,"team_id":tid,"team":x["team"],
            "matches":m,"home_matches":x["home"],"away_matches":x["away"],
            "wins":x["wins"],"draws":x["draws"],"losses":x["losses"],
            "win_pct":pct(x["wins"],m),"draw_pct":pct(x["draws"],m),
            "loss_pct":pct(x["losses"],m),"points":x["points"],
            "points_per_match":rate(x["points"],m),"goal_observed_matches":x["goal_obs"],
            "goals_for":x["gf"],"goals_against":x["ga"],
            "goal_difference":x["gf"]-x["ga"],
            "first_date":min(x["dates"]) if x["dates"] else "",
            "last_date":max(x["dates"]) if x["dates"] else "",
            "season_count":len([s for s in x["seasons"] if s]),
            "source_scope":"TOP5_9_SEASONS_API_FOOTBALL",
            "cards_available":"false","fouls_available":"false",
            "penalties_available":"false","research_only":"true",
            "operational_betting_authority":"false",
        })
    return out


def state_rows_for_matrix(matrix, existing):
    by={state_key(r):dict(r) for r in existing if all(state_key(r))}
    rows=[]
    for spec in matrix:
        key=(str(spec["provider_league_id"]),str(spec["season"]))
        row=by.get(key,{f:"" for f in STATE_FIELDS})
        row.update({
            "provider_league_id":key[0],"league_name":spec["league_name"],
            "country":spec["country"],"season":key[1],
        })
        if not row.get("status"): row["status"]="PENDING"
        if not row.get("attempt_count"): row["attempt_count"]="0"
        rows.append(row)
    return rows


def protected_calls():
    return max(0,int(os.getenv("STAGE80_TOP5_REFEREE_PROTECTED_CALLS","512")))


def run(config_path=CONFIG, get=api_get, now=None):
    now=now or datetime.now(timezone.utc)
    config,matrix=load_config(config_path)
    archive=read_csv(ARCHIVE)
    state=state_rows_for_matrix(matrix,read_csv(QUERY_STATE))
    shared=audit.read(SHARED_STATE)
    budget=audit.Budget(
        get,shared,now,
        limit=int(os.getenv("STAGE80_TOP5_REFEREE_MAX_API_CALLS","45")),
        daily_limit=int(os.getenv("STAGE71_MAX_DAILY_API_CALLS","7000")),
        checkpoint=lambda s:audit.save(SHARED_STATE,s),
        protected_calls=protected_calls(),
    )

    calls_before=int(shared.get("api_day_calls") or 0)
    warnings=[]
    for row,spec in zip(state,matrix):
        if row.get("status")=="CAPTURED":
            continue
        attempted=iso_now()
        try:
            payload=budget(
                "/fixtures",
                {"league":spec["provider_league_id"],"season":spec["season"]},
                ttl_seconds=365*24*3600,
                force_refresh=False,
            )
            normalized=normalize_payload(payload,spec,attempted)
            if not normalized:
                raise RuntimeError("provider returned no fixtures")
            archive=merge_archive(archive,normalized)
            row["status"]="CAPTURED"
            row["fixture_rows"]=str(len(normalized))
            row["referee_rows"]=str(sum(bool(r.get("referee")) for r in normalized))
            row["error"]=""
        except audit.ProtectedBudgetError as exc:
            warnings.append(str(exc)); break
        except (ApiFootballBrokerError,RuntimeError,ValueError,TypeError,KeyError) as exc:
            row["status"]="ERROR"; row["error"]=str(exc); warnings.append(
                f"{spec['provider_league_id']}:{spec['season']}: {exc}"
            )
        finally:
            if row.get("last_attempt_at_utc") != attempted:
                try: row["attempt_count"]=str(int(row.get("attempt_count") or 0)+1)
                except ValueError: row["attempt_count"]="1"
                row["last_attempt_at_utc"]=attempted
            write_csv(ARCHIVE,ARCHIVE_FIELDS,archive)
            write_csv(QUERY_STATE,STATE_FIELDS,state)

    profiles=aggregate_profiles(archive)
    splits=aggregate_team_splits(archive)
    write_csv(PROFILES,PROFILE_FIELDS,profiles)
    write_csv(TEAM_SPLITS,TEAM_FIELDS,splits)
    audit.save(SHARED_STATE,shared)

    captured=sum(r.get("status")=="CAPTURED" for r in state)
    pending=len(state)-captured
    by_league={}
    for spec in config["leagues"]:
        lid=str(spec["provider_league_id"])
        rows=[r for r in archive if str(r.get("provider_league_id"))==lid]
        ref=sum(bool(str(r.get("referee") or "").strip()) for r in rows)
        by_league[lid]={
            "league_name":spec["league_name"],"rows":len(rows),"referee_rows":ref,
            "referee_coverage_pct":pct(ref,len(rows)) if rows else None,
        }
    referee_rows=sum(bool(str(r.get("referee") or "").strip()) for r in archive)
    broker_stats=get_broker().stats() if get is api_get else {}
    meta={
        "version":VERSION,"run_at_utc":iso_now(),
        "status":"OK" if pending==0 else "COLLECTING",
        "expected_queries":len(matrix),"captured_queries":captured,
        "pending_or_error_queries":pending,"archive_rows":len(archive),
        "referee_rows":referee_rows,
        "referee_coverage_pct":pct(referee_rows,len(archive)) if archive else None,
        "by_league":by_league,"profile_rows":len(profiles),
        "team_split_rows":len(splits),"provider_budget_calls":budget.calls,
        "real_api_calls":broker_stats.get("real_api_calls"),
        "daily_api_calls_before":calls_before,
        "daily_api_calls_after":int(shared.get("api_day_calls") or 0),
        "protected_calls":protected_calls(),"warnings":warnings,
        "historical_backfill_only":True,"research_only":True,
        "operational_betting_authority":False,"creates_signal":False,
        "probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,
    }
    write_json(META,meta)
    return meta


def main():
    meta=run()
    print(json.dumps(meta,ensure_ascii=False))


if __name__=="__main__":
    main()
