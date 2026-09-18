#!/usr/bin/env python3
"""Stage80 — resumable Top-5 non-league fixture archive + prior congestion research.

Historical archive/research only.

Collection:
- API-Football /fixtures?league=<competition>&season=<year>
- shared broker / raw archive / Stage71 daily budget
- query cells are resumable and CAPTURED cells are never recalled
- durable normalized archive keeps only fixtures involving at least one club that
  appears in a Top-5 domestic league in the same provider season

Projection:
- one row per Top-5 domestic fixture from top5_referee_fixture_history.csv
- strictly earlier *played* non-league fixtures only (FT/AET/PEN)
- no future fixture is used in V1, so Thursday->Sunday and prior cup/UEFA load
  are no-lookahead historical features
- research only; no PBK probability, EV/value, eligibility, stake or Forward authority
"""
from __future__ import annotations

import bisect
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
CONFIG = Path("config/stage80_api_football_top5_nonleague_9seasons.json")
DOMESTIC = OPS / "top5_referee_fixture_history.csv"
ARCHIVE = OPS / "top5_nonleague_fixture_history.csv"
QUERY_STATE = OPS / "stage80_top5_nonleague_backfill_state.csv"
META = OPS / "stage80_top5_nonleague_backfill_last_run.json"
CONGESTION = OPS / "top5_competition_congestion_research.csv"
CONGESTION_META = OPS / "stage80_competition_congestion_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

VERSION = "PBK_STAGE80_TOP5_NONLEAGUE_BACKFILL_V1"
CONGESTION_VERSION = "PBK_STAGE80_TOP5_COMPETITION_CONGESTION_V1"
FINAL = {"FT", "AET", "PEN"}

ARCHIVE_FIELDS = [
    "fixture_id","provider_competition_id","competition_name","competition_type",
    "competition_country","season","round","kickoff_utc","status",
    "venue_id","venue_name","venue_city",
    "home_team_id","home_team","away_team_id","away_team",
    "home_goals","away_goals","result",
    "home_is_top5_same_season","away_is_top5_same_season",
    "captured_at_utc","source","historical_backfill_only","research_only",
    "operational_betting_authority","creates_signal","probability_mutation",
    "eligibility_mutation","stake_changes","forward_journal_mutation",
]
STATE_FIELDS = [
    "provider_competition_id","competition_name","competition_type","competition_country",
    "season","status","attempt_count","last_attempt_at_utc",
    "provider_fixture_rows","relevant_fixture_rows","error",
]
SIDE_FIELDS = [
    "prev_nonleague_fixture_id","prev_nonleague_competition_id",
    "prev_nonleague_competition_name","prev_nonleague_competition_type",
    "prev_nonleague_round","prev_nonleague_kickoff_utc",
    "hours_since_prev_nonleague","days_since_prev_nonleague",
    "prev_nonleague_weekday_iso","prev_nonleague_weekday_name_utc",
    "prev_nonleague_was_thursday","prev_nonleague_was_uefa",
    "prev_nonleague_was_domestic_cup","prev_nonleague_team_result",
    "nonleague_matches_prev_7d","nonleague_matches_prev_14d",
    "uefa_matches_prev_7d","domestic_cup_matches_prev_7d",
]
CONGESTION_FIELDS = [
    "domestic_fixture_id","provider_league_id","league_name","country","season","round",
    "kickoff_utc","status","home_team_id","home_team","away_team_id","away_team",
] + ["home_"+x for x in SIDE_FIELDS] + ["away_"+x for x in SIDE_FIELDS] + [
    "either_team_prev_nonleague_within_72h","either_team_prev_nonleague_within_96h",
    "either_team_prev_uefa_within_72h","either_team_prev_uefa_within_96h",
    "either_team_prev_domestic_cup_within_72h","either_team_prev_domestic_cup_within_96h",
    "either_team_previous_nonleague_was_thursday",
    "strictly_prior_fixture_evidence_only","future_schedule_used",
    "no_lookahead","historical_backfill_only","research_only",
    "operational_betting_authority","creates_signal","probability_mutation",
    "eligibility_mutation","stake_changes","forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def parse_dt(value):
    try:
        d=datetime.fromisoformat(str(value or "").replace("Z","+00:00"))
        if d.tzinfo is None:
            return None
        return d.astimezone(timezone.utc)
    except (TypeError,ValueError):
        return None


def read_csv(path):
    path=Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig",newline="") as f:
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


def as_int(value):
    if value is None or value=="":
        return None
    try:
        return int(value)
    except (TypeError,ValueError):
        try:
            return int(float(value))
        except (TypeError,ValueError):
            return None


def load_config(path=CONFIG):
    cfg=json.loads(Path(path).read_text(encoding="utf-8"))
    matrix=[]
    for comp in cfg["competitions"]:
        for season in comp["seasons"]:
            matrix.append({
                "provider_competition_id":int(comp["provider_league_id"]),
                "competition_name":comp["competition_name"],
                "competition_type":comp["competition_type"],
                "competition_country":comp.get("country","International"),
                "season":int(season),
            })
    if len(matrix)!=int(cfg.get("expected_queries") or 0):
        raise ValueError("nonleague competition matrix size does not match expected_queries")
    return cfg,matrix


def domestic_team_membership(domestic_rows):
    membership=defaultdict(set)
    for row in domestic_rows:
        season=str(row.get("season") or "").strip()
        if not season:
            continue
        for key in ("home_team_id","away_team_id"):
            tid=str(row.get(key) or "").strip()
            if tid:
                membership[season].add(tid)
    return membership


def result_code(status,home,away):
    if status not in FINAL or home is None or away is None:
        return ""
    if home>away: return "H"
    if home<away: return "A"
    return "D"


def normalize_payload(payload,spec,captured_at,top5_ids):
    rows=[]
    provider_rows=0
    for item in payload.get("response") or []:
        provider_rows+=1
        fixture=item.get("fixture") or {}
        league=item.get("league") or {}
        teams=item.get("teams") or {}
        goals=item.get("goals") or {}
        home=teams.get("home") or {}; away=teams.get("away") or {}
        hid=str(home.get("id") or "").strip(); aid=str(away.get("id") or "").strip()
        home_top5=hid in top5_ids; away_top5=aid in top5_ids
        if not (home_top5 or away_top5):
            continue
        fid=str(fixture.get("id") or "").strip()
        if not fid:
            continue
        status=str((fixture.get("status") or {}).get("short") or "").strip()
        venue=fixture.get("venue") or {}
        hg=as_int(goals.get("home")); ag=as_int(goals.get("away"))
        rows.append({
            "fixture_id":fid,
            "provider_competition_id":str(league.get("id") or spec["provider_competition_id"]),
            "competition_name":str(league.get("name") or spec["competition_name"]),
            "competition_type":spec["competition_type"],
            "competition_country":str(league.get("country") or spec["competition_country"]),
            "season":str(league.get("season") or spec["season"]),
            "round":str(league.get("round") or ""),
            "kickoff_utc":str(fixture.get("date") or ""),
            "status":status,
            "venue_id":str(venue.get("id") or ""),
            "venue_name":str(venue.get("name") or ""),
            "venue_city":str(venue.get("city") or ""),
            "home_team_id":hid,"home_team":str(home.get("name") or ""),
            "away_team_id":aid,"away_team":str(away.get("name") or ""),
            "home_goals":"" if hg is None else hg,
            "away_goals":"" if ag is None else ag,
            "result":result_code(status,hg,ag),
            "home_is_top5_same_season":"true" if home_top5 else "false",
            "away_is_top5_same_season":"true" if away_top5 else "false",
            "captured_at_utc":captured_at,
            "source":"API-Football /fixtures?league&season",
            "historical_backfill_only":"true","research_only":"true",
            "operational_betting_authority":"false","creates_signal":"false",
            "probability_mutation":"false","eligibility_mutation":"false",
            "stake_changes":"false","forward_journal_mutation":"false",
        })
    return provider_rows,rows


def archive_key(row):
    return str(row.get("fixture_id") or "").strip()


def merge_archive(existing,incoming):
    merged={archive_key(r):dict(r) for r in existing if archive_key(r)}
    for row in incoming:
        key=archive_key(row)
        if key:
            merged[key]=dict(row)
    return sorted(
        merged.values(),
        key=lambda r:(str(r.get("kickoff_utc") or ""),str(r.get("fixture_id") or ""))
    )


def state_key(row):
    return (
        str(row.get("provider_competition_id") or ""),
        str(row.get("season") or ""),
    )


def state_rows_for_matrix(matrix,existing):
    by={state_key(r):dict(r) for r in existing if all(state_key(r))}
    rows=[]
    for spec in matrix:
        key=(str(spec["provider_competition_id"]),str(spec["season"]))
        row=by.get(key,{f:"" for f in STATE_FIELDS})
        row.update({
            "provider_competition_id":key[0],
            "competition_name":spec["competition_name"],
            "competition_type":spec["competition_type"],
            "competition_country":spec["competition_country"],
            "season":key[1],
        })
        if not row.get("status"): row["status"]="PENDING"
        if not row.get("attempt_count"): row["attempt_count"]="0"
        rows.append(row)
    return rows


def protected_calls():
    return max(0,int(os.getenv("STAGE80_TOP5_NONLEAGUE_PROTECTED_CALLS","512")))


def team_result(row,team_id):
    result=str(row.get("result") or "")
    if result not in {"H","D","A"}:
        return ""
    if result=="D": return "D"
    hid=str(row.get("home_team_id") or "")
    if (result=="H" and team_id==hid) or (result=="A" and team_id!=hid):
        return "W"
    return "L"


def build_played_index(nonleague_rows):
    by=defaultdict(list)
    for row in nonleague_rows:
        if str(row.get("status") or "") not in FINAL:
            continue
        kickoff=parse_dt(row.get("kickoff_utc"))
        season=str(row.get("season") or "").strip()
        if not kickoff or not season:
            continue
        for key in ("home_team_id","away_team_id"):
            tid=str(row.get(key) or "").strip()
            if tid:
                by[(season,tid)].append((kickoff,row))
    for key in by:
        by[key].sort(key=lambda x:(x[0],str(x[1].get("fixture_id") or "")))
    return by


def bool_text(value):
    return "true" if value else "false"


def side_context(team_id,season,kickoff,index):
    items=index.get((season,team_id),[])
    times=[x[0] for x in items]
    pos=bisect.bisect_left(times,kickoff)
    prior=items[:pos]
    prev=prior[-1] if prior else None
    out={x:"" for x in SIDE_FIELDS}
    if prev:
        prev_dt,row=prev
        hours=(kickoff-prev_dt).total_seconds()/3600.0
        out.update({
            "prev_nonleague_fixture_id":str(row.get("fixture_id") or ""),
            "prev_nonleague_competition_id":str(row.get("provider_competition_id") or ""),
            "prev_nonleague_competition_name":str(row.get("competition_name") or ""),
            "prev_nonleague_competition_type":str(row.get("competition_type") or ""),
            "prev_nonleague_round":str(row.get("round") or ""),
            "prev_nonleague_kickoff_utc":str(row.get("kickoff_utc") or ""),
            "hours_since_prev_nonleague":round(hours,3),
            "days_since_prev_nonleague":round(hours/24.0,3),
            "prev_nonleague_weekday_iso":prev_dt.isoweekday(),
            "prev_nonleague_weekday_name_utc":prev_dt.strftime("%A").upper(),
            "prev_nonleague_was_thursday":bool_text(prev_dt.isoweekday()==4),
            "prev_nonleague_was_uefa":bool_text(str(row.get("competition_type"))=="UEFA"),
            "prev_nonleague_was_domestic_cup":bool_text(str(row.get("competition_type"))=="DOMESTIC_CUP"),
            "prev_nonleague_team_result":team_result(row,team_id),
        })
    prev7=[x for x in prior if 0 < (kickoff-x[0]).total_seconds() <= 7*86400]
    prev14=[x for x in prior if 0 < (kickoff-x[0]).total_seconds() <= 14*86400]
    out["nonleague_matches_prev_7d"]=len(prev7)
    out["nonleague_matches_prev_14d"]=len(prev14)
    out["uefa_matches_prev_7d"]=sum(str(x[1].get("competition_type"))=="UEFA" for x in prev7)
    out["domestic_cup_matches_prev_7d"]=sum(str(x[1].get("competition_type"))=="DOMESTIC_CUP" for x in prev7)
    return out


def within_hours(side,kind,hours):
    raw=side.get("hours_since_prev_nonleague")
    try:
        h=float(raw)
    except (TypeError,ValueError):
        return False
    if not (0 < h <= hours):
        return False
    if kind=="ANY": return True
    if kind=="UEFA": return side.get("prev_nonleague_was_uefa")=="true"
    if kind=="DOMESTIC_CUP": return side.get("prev_nonleague_was_domestic_cup")=="true"
    return False


def build_congestion(domestic_rows,nonleague_rows):
    index=build_played_index(nonleague_rows)
    out=[]
    invalid_domestic=0
    for row in domestic_rows:
        kickoff=parse_dt(row.get("kickoff_utc"))
        season=str(row.get("season") or "").strip()
        hid=str(row.get("home_team_id") or "").strip()
        aid=str(row.get("away_team_id") or "").strip()
        fid=str(row.get("fixture_id") or "").strip()
        if not (kickoff and season and hid and aid and fid):
            invalid_domestic+=1
            continue
        home=side_context(hid,season,kickoff,index)
        away=side_context(aid,season,kickoff,index)
        record={
            "domestic_fixture_id":fid,
            "provider_league_id":str(row.get("provider_league_id") or ""),
            "league_name":str(row.get("league_name") or ""),
            "country":str(row.get("country") or ""),
            "season":season,"round":str(row.get("round") or ""),
            "kickoff_utc":str(row.get("kickoff_utc") or ""),
            "status":str(row.get("status") or ""),
            "home_team_id":hid,"home_team":str(row.get("home_team") or ""),
            "away_team_id":aid,"away_team":str(row.get("away_team") or ""),
        }
        record.update({"home_"+k:v for k,v in home.items()})
        record.update({"away_"+k:v for k,v in away.items()})
        record.update({
            "either_team_prev_nonleague_within_72h":bool_text(within_hours(home,"ANY",72) or within_hours(away,"ANY",72)),
            "either_team_prev_nonleague_within_96h":bool_text(within_hours(home,"ANY",96) or within_hours(away,"ANY",96)),
            "either_team_prev_uefa_within_72h":bool_text(within_hours(home,"UEFA",72) or within_hours(away,"UEFA",72)),
            "either_team_prev_uefa_within_96h":bool_text(within_hours(home,"UEFA",96) or within_hours(away,"UEFA",96)),
            "either_team_prev_domestic_cup_within_72h":bool_text(within_hours(home,"DOMESTIC_CUP",72) or within_hours(away,"DOMESTIC_CUP",72)),
            "either_team_prev_domestic_cup_within_96h":bool_text(within_hours(home,"DOMESTIC_CUP",96) or within_hours(away,"DOMESTIC_CUP",96)),
            "either_team_previous_nonleague_was_thursday":bool_text(
                home.get("prev_nonleague_was_thursday")=="true" or away.get("prev_nonleague_was_thursday")=="true"
            ),
            "strictly_prior_fixture_evidence_only":"true",
            "future_schedule_used":"false","no_lookahead":"true",
            "historical_backfill_only":"true","research_only":"true",
            "operational_betting_authority":"false","creates_signal":"false",
            "probability_mutation":"false","eligibility_mutation":"false",
            "stake_changes":"false","forward_journal_mutation":"false",
        })
        out.append(record)
    out.sort(key=lambda r:(r["kickoff_utc"],r["domestic_fixture_id"]))
    return out,invalid_domestic


def run(config_path=CONFIG,get=api_get,now=None):
    now=now or datetime.now(timezone.utc)
    cfg,matrix=load_config(config_path)
    domestic=read_csv(DOMESTIC)
    if not domestic:
        raise RuntimeError("top5_referee_fixture_history.csv is required before nonleague backfill")
    membership=domestic_team_membership(domestic)
    archive=read_csv(ARCHIVE)
    state=state_rows_for_matrix(matrix,read_csv(QUERY_STATE))
    shared=audit.read(SHARED_STATE)
    budget=audit.Budget(
        get,shared,now,
        limit=int(os.getenv("STAGE80_TOP5_NONLEAGUE_MAX_API_CALLS","77")),
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
                {"league":spec["provider_competition_id"],"season":spec["season"]},
                ttl_seconds=365*24*3600,
                force_refresh=False,
            )
            provider_rows,relevant=normalize_payload(
                payload,spec,attempted,membership.get(str(spec["season"]),set())
            )
            # Empty relevant rows are acceptable when provider returned a valid competition-season
            # but no Top-5 domestic club participated. Provider-zero is treated as an error because
            # the configured competition-season itself should exist.
            if provider_rows<=0:
                raise RuntimeError("provider returned no competition fixtures")
            archive=merge_archive(archive,relevant)
            row["status"]="CAPTURED"
            row["provider_fixture_rows"]=str(provider_rows)
            row["relevant_fixture_rows"]=str(len(relevant))
            row["error"]=""
        except audit.ProtectedBudgetError as exc:
            warnings.append(str(exc)); break
        except (ApiFootballBrokerError,RuntimeError,ValueError,TypeError,KeyError) as exc:
            row["status"]="ERROR"; row["error"]=str(exc)
            warnings.append(f"{spec['provider_competition_id']}:{spec['season']}: {exc}")
        finally:
            if row.get("last_attempt_at_utc")!=attempted:
                try: row["attempt_count"]=str(int(row.get("attempt_count") or 0)+1)
                except ValueError: row["attempt_count"]="1"
                row["last_attempt_at_utc"]=attempted
            write_csv(ARCHIVE,ARCHIVE_FIELDS,archive)
            write_csv(QUERY_STATE,STATE_FIELDS,state)

    congestion,invalid_domestic=build_congestion(domestic,archive)
    write_csv(CONGESTION,CONGESTION_FIELDS,congestion)
    audit.save(SHARED_STATE,shared)

    captured=sum(r.get("status")=="CAPTURED" for r in state)
    pending=len(state)-captured
    relevant_played=sum(str(r.get("status") or "") in FINAL for r in archive)
    relevant_uefa=sum(str(r.get("competition_type") or "")=="UEFA" for r in archive)
    relevant_cup=sum(str(r.get("competition_type") or "")=="DOMESTIC_CUP" for r in archive)
    broker_stats=get_broker().stats() if get is api_get else {}
    meta={
        "version":VERSION,"run_at_utc":iso_now(),
        "status":"OK" if pending==0 else "COLLECTING",
        "expected_queries":len(matrix),"captured_queries":captured,
        "pending_or_error_queries":pending,
        "archive_rows":len(archive),"played_archive_rows":relevant_played,
        "uefa_archive_rows":relevant_uefa,"domestic_cup_archive_rows":relevant_cup,
        "domestic_anchor_rows":len(domestic),
        "congestion_rows":len(congestion),"invalid_domestic_anchor_rows":invalid_domestic,
        "provider_budget_calls":budget.calls,"real_api_calls":broker_stats.get("real_api_calls"),
        "daily_api_calls_before":calls_before,
        "daily_api_calls_after":int(shared.get("api_day_calls") or 0),
        "protected_calls":protected_calls(),"warnings":warnings,
        "historical_backfill_only":True,"research_only":True,
        "operational_betting_authority":False,"creates_signal":False,
        "probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,
    }
    write_json(META,meta)

    rows_with_prior_home=sum(bool(r.get("home_prev_nonleague_fixture_id")) for r in congestion)
    rows_with_prior_away=sum(bool(r.get("away_prev_nonleague_fixture_id")) for r in congestion)
    congestion_meta={
        "version":CONGESTION_VERSION,"run_at_utc":iso_now(),
        "status":"OK" if pending==0 and invalid_domestic==0 and len(congestion)==len(domestic) else "ATTENTION",
        "source_domestic_rows":len(domestic),"source_nonleague_rows":len(archive),
        "output_rows":len(congestion),"unique_domestic_fixture_ids":len({r["domestic_fixture_id"] for r in congestion}),
        "invalid_domestic_anchor_rows":invalid_domestic,
        "rows_with_home_prior_nonleague":rows_with_prior_home,
        "rows_with_away_prior_nonleague":rows_with_prior_away,
        "rows_either_prev_nonleague_72h":sum(r["either_team_prev_nonleague_within_72h"]=="true" for r in congestion),
        "rows_either_prev_nonleague_96h":sum(r["either_team_prev_nonleague_within_96h"]=="true" for r in congestion),
        "rows_either_prev_uefa_72h":sum(r["either_team_prev_uefa_within_72h"]=="true" for r in congestion),
        "rows_either_prev_uefa_96h":sum(r["either_team_prev_uefa_within_96h"]=="true" for r in congestion),
        "rows_either_prev_cup_72h":sum(r["either_team_prev_domestic_cup_within_72h"]=="true" for r in congestion),
        "rows_either_prev_cup_96h":sum(r["either_team_prev_domestic_cup_within_96h"]=="true" for r in congestion),
        "rows_either_previous_nonleague_was_thursday":sum(r["either_team_previous_nonleague_was_thursday"]=="true" for r in congestion),
        "strictly_prior_fixture_evidence_only":True,"future_schedule_used":False,
        "no_lookahead":True,"provider_calls":0,
        "historical_backfill_only":True,"research_only":True,
        "operational_betting_authority":False,"creates_signal":False,
        "probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,
    }
    write_json(CONGESTION_META,congestion_meta)
    return meta,congestion_meta


def main():
    meta,context=run()
    print(json.dumps({"backfill":meta,"congestion":context},ensure_ascii=False))


if __name__=="__main__":
    main()
