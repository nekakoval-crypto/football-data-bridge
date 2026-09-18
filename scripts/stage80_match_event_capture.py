#!/usr/bin/env python3
"""Stage80 — durable finished-fixture match-event archive.

Captures API-Football /fixtures/events through the shared PBK broker/budget.
This is archive/research evidence only and never mutates betting/model state.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
from api_football_broker import ApiFootballBrokerError

OPS = Path(os.getenv("OPS_DIR", "ops"))
FIXTURES = OPS / "current_round_fixtures.csv"
EVENTS = OPS / "match_event_snapshots.csv"
BACKLOG = OPS / "stage80_match_event_backlog.csv"
META = OPS / "stage80_match_event_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

TERMINAL = {"FINISHED", "FT", "AET", "PEN"}
VERSION = "PBK_STAGE80_MATCH_EVENT_ARCHIVE_V1"

EVENT_FIELDS = [
    "event_id","fixture_id","provider_league_id","league_name","season","round",
    "kickoff_utc","observed_at_utc","elapsed","extra","team_id","team_name",
    "player_id","player_name","assist_id","assist_name","event_type","detail",
    "comments","source","archive_version","research_only","creates_signal",
    "probability_mutation","eligibility_mutation","stake_changes",
    "forward_journal_mutation",
]
BACKLOG_FIELDS = [
    "fixture_id","provider_league_id","league_name","season","round","kickoff_utc",
    "home_team","away_team","source_status","first_queued_at_utc","last_seen_at_utc",
    "backlog_status","captured_at_utc","queue_source","attempt_count",
    "last_attempt_at_utc","last_attempt_result",
]


def iso(value=None):
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def parse_utc(value):
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z","+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv_atomic(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def terminal_fixture(row, now):
    kickoff = parse_utc(row.get("kickoff_utc"))
    status = (sval(row,"source_status") or sval(row,"status")).upper()
    return bool(sval(row,"fixture_id") and kickoff and kickoff <= now and (status in TERMINAL or sval(row,"status").upper()=="FINISHED"))


def completed_fixture_ids(rows):
    return {sval(row,"fixture_id") for row in rows if sval(row,"fixture_id") and sval(row,"event_id")}


def first_observed_by_fixture(rows):
    out = {}
    for row in rows:
        fid, observed = sval(row,"fixture_id"), sval(row,"observed_at_utc")
        if fid and observed and (fid not in out or observed < out[fid]):
            out[fid] = observed
    return out


def sync_backlog(existing, fixtures, event_rows, now):
    merged = {
        sval(row,"fixture_id"):{field:row.get(field,"") for field in BACKLOG_FIELDS}
        for row in existing if sval(row,"fixture_id")
    }
    now_iso = iso(now)
    new_rows = terminal_seen = 0
    for fixture in fixtures:
        if not terminal_fixture(fixture, now):
            continue
        terminal_seen += 1
        fid = sval(fixture,"fixture_id")
        row = merged.get(fid)
        if row is None:
            row = {field:"" for field in BACKLOG_FIELDS}
            row.update({"fixture_id":fid,"first_queued_at_utc":now_iso,"queue_source":"current_round_terminal_fixture","attempt_count":"0"})
            new_rows += 1
        for field in ("provider_league_id","league_name","season","round","kickoff_utc","home_team","away_team","source_status"):
            value = sval(fixture,field)
            if value:
                row[field] = value
        row["last_seen_at_utc"] = now_iso
        merged[fid] = row

    captured = first_observed_by_fixture(event_rows)
    for fid,row in merged.items():
        if fid in captured:
            row["backlog_status"] = "CAPTURED"
            row["captured_at_utc"] = row.get("captured_at_utc") or captured[fid]
        else:
            row["backlog_status"] = "PENDING"
            row["captured_at_utc"] = ""

    rows = [merged[k] for k in sorted(merged, key=lambda fid:(parse_utc(merged[fid].get("kickoff_utc")) or now, fid))]
    return {
        "rows":rows,"new_rows":new_rows,"terminal_seen":terminal_seen,
        "pending":sum(r.get("backlog_status")=="PENDING" for r in rows),
        "captured":sum(r.get("backlog_status")=="CAPTURED" for r in rows),
    }


def attempt_count(row):
    try: return max(0,int(sval(row,"attempt_count") or "0"))
    except ValueError: return 0


def record_attempts(rows, attempts):
    by = {sval(r,"fixture_id"):dict(r) for r in rows if sval(r,"fixture_id")}
    for a in attempts:
        fid = str(a.get("fixture_id") or "")
        if fid not in by: continue
        by[fid]["attempt_count"] = str(attempt_count(by[fid])+1)
        by[fid]["last_attempt_at_utc"] = str(a.get("attempted_at_utc") or "")
        by[fid]["last_attempt_result"] = str(a.get("result") or "")
    return [by[sval(r,"fixture_id")] for r in rows]


def candidate_fixtures(rows, captured, now, limit):
    out=[]
    for row in rows:
        fid=sval(row,"fixture_id")
        kickoff=parse_utc(row.get("kickoff_utc"))
        if not fid or fid in captured or not kickoff or kickoff>now: continue
        if sval(row,"backlog_status").upper()!="PENDING": continue
        out.append(row)
    out.sort(key=lambda r:(0 if not parse_utc(r.get("last_attempt_at_utc")) else 1,
                           parse_utc(r.get("last_attempt_at_utc")) or datetime.min.replace(tzinfo=timezone.utc),
                           parse_utc(r.get("kickoff_utc")) or now,
                           sval(r,"fixture_id")))
    return out[:max(0,int(limit))]


def protected_calls(ops, now):
    live=audit.live_forecast(Path(ops)/"current_round_fixtures.csv",now)
    live_calls=int(live.get("reserved_live_calls") or 0)
    round_calls=audit.current_round_forecast(now,calls_per_run=int(os.getenv("STAGE80_EVENT_CURRENT_ROUND_CALLS_PER_RUN","32")))
    standings=max(0,int(os.getenv("STAGE80_EVENT_STANDINGS_RESERVE_CALLS","16")))
    stage77=max(0,int(os.getenv("STAGE80_EVENT_PLAYER_STATS_RESERVE_CALLS","4")))
    stage81=max(0,int(os.getenv("STAGE80_EVENT_TEAM_STATS_RESERVE_CALLS","12")))
    safety=max(0,int(os.getenv("STAGE80_EVENT_SAFETY_RESERVE_CALLS","8")))
    total=live_calls+round_calls+standings+stage77+stage81+safety
    return {"live":live_calls,"current_round":round_calls,"standings":standings,"player_stats_stage77":stage77,"team_stats_stage81":stage81,"safety":safety,"total":total}


def event_signature(fixture_id, item):
    time=item.get("time") or {}
    team=item.get("team") or {}
    player=item.get("player") or {}
    assist=item.get("assist") or {}
    fields=[
        fixture_id,time.get("elapsed"),time.get("extra"),team.get("id"),team.get("name"),
        player.get("id"),player.get("name"),assist.get("id"),assist.get("name"),
        item.get("type"),item.get("detail"),item.get("comments"),
    ]
    return json.dumps(fields,ensure_ascii=False,separators=(",",":"))


def normalize_events(payload, fixture, observed_at):
    response=payload.get("response",[]) if isinstance(payload,dict) else []
    if not isinstance(response,list): return []
    occurrences={}
    rows=[]
    fid=sval(fixture,"fixture_id")
    for item in response:
        if not isinstance(item,dict): continue
        sig=event_signature(fid,item)
        occurrences[sig]=occurrences.get(sig,0)+1
        event_id=hashlib.sha256(f"{sig}|{occurrences[sig]}".encode("utf-8")).hexdigest()
        time=item.get("time") or {}; team=item.get("team") or {}; player=item.get("player") or {}; assist=item.get("assist") or {}
        if not item.get("type") and not item.get("detail"): continue
        rows.append({
            "event_id":event_id,"fixture_id":fid,
            "provider_league_id":sval(fixture,"provider_league_id"),"league_name":sval(fixture,"league_name"),
            "season":sval(fixture,"season"),"round":sval(fixture,"round"),"kickoff_utc":sval(fixture,"kickoff_utc"),
            "observed_at_utc":observed_at,"elapsed":time.get("elapsed") if time.get("elapsed") is not None else "",
            "extra":time.get("extra") if time.get("extra") is not None else "",
            "team_id":team.get("id") or "","team_name":team.get("name") or "",
            "player_id":player.get("id") or "","player_name":player.get("name") or "",
            "assist_id":assist.get("id") or "","assist_name":assist.get("name") or "",
            "event_type":item.get("type") or "","detail":item.get("detail") or "","comments":item.get("comments") or "",
            "source":"API-Football /fixtures/events","archive_version":VERSION,
            "research_only":"true","creates_signal":"false","probability_mutation":"false",
            "eligibility_mutation":"false","stake_changes":"false","forward_journal_mutation":"false",
        })
    return rows


def merge_rows(existing,incoming):
    merged={sval(r,"event_id"):dict(r) for r in existing if sval(r,"event_id")}
    for row in incoming:
        eid=sval(row,"event_id")
        if eid and eid not in merged: merged[eid]=dict(row)
    return [merged[k] for k in sorted(merged)]


def capture(backlog_rows, existing_rows, get, now, max_fixtures):
    captured=completed_fixture_ids(existing_rows)
    candidates=candidate_fixtures(backlog_rows,captured,now,max_fixtures)
    new=[]; attempts=[]; warnings=[]; captured_ids=[]; deferred=0
    for idx,fixture in enumerate(candidates):
        fid=sval(fixture,"fixture_id"); attempted_at=iso(now)
        try:
            payload=get("/fixtures/events",{"fixture":fid},ttl_seconds=30*24*3600,force_refresh=False)
        except audit.ProtectedBudgetError as exc:
            deferred=len(candidates)-idx; warnings.append(str(exc)); break
        except (ApiFootballBrokerError,RuntimeError,ValueError,TypeError,KeyError) as exc:
            attempts.append({"fixture_id":fid,"attempted_at_utc":attempted_at,"result":"ERROR"})
            warnings.append(f"{fid}: {exc}"); continue
        rows=normalize_events(payload,fixture,attempted_at)
        if not rows:
            attempts.append({"fixture_id":fid,"attempted_at_utc":attempted_at,"result":"NO_DATA"})
            continue
        new.extend(rows); captured_ids.append(fid)
        attempts.append({"fixture_id":fid,"attempted_at_utc":attempted_at,"result":"CAPTURED"})
    return {
        "rows":merge_rows(existing_rows,new),"new_rows":len(new),"candidate_fixtures":len(candidates),
        "captured_fixture_ids":captured_ids,"captured_fixtures":len(captured_ids),
        "deferred_fixtures":deferred,"attempts":attempts,"warnings":warnings,
    }


def main():
    now=datetime.now(timezone.utc)
    fixtures=read_csv(FIXTURES); existing=read_csv(EVENTS); old_backlog=read_csv(BACKLOG)
    before=sync_backlog(old_backlog,fixtures,existing,now)
    state=audit.read(SHARED_STATE); reserve=protected_calls(OPS,now)
    max_calls=int(os.getenv("STAGE80_EVENT_MAX_API_CALLS","8"))
    daily_limit=int(os.getenv("STAGE71_MAX_DAILY_API_CALLS","7000"))
    budget=audit.Budget(s53.api_get,state,now,limit=max_calls,daily_limit=daily_limit,protected_calls=reserve["total"],checkpoint=lambda value:audit.save(SHARED_STATE,value))
    result=capture(before["rows"],existing,budget,now,int(os.getenv("STAGE80_EVENT_MAX_FIXTURES_PER_RUN",str(max_calls))))
    attempted=record_attempts(before["rows"],result["attempts"])
    after=sync_backlog(attempted,[],result["rows"],now)
    write_csv_atomic(EVENTS,EVENT_FIELDS,result["rows"])
    write_csv_atomic(BACKLOG,BACKLOG_FIELDS,after["rows"])
    audit.save(SHARED_STATE,state)
    meta={
        "version":VERSION,"run_at_utc":iso(now),"status":"ATTENTION" if result["warnings"] else ("WAITING" if result["deferred_fixtures"] else "OK"),
        "provider_endpoint":"/fixtures/events","provider_calls":budget.calls,"daily_api_calls":state.get("api_day_calls",0),
        "protected_calls":reserve,"candidate_fixtures":result["candidate_fixtures"],"captured_fixtures":result["captured_fixtures"],
        "captured_fixture_ids":result["captured_fixture_ids"],"deferred_fixtures":result["deferred_fixtures"],
        "attempted_fixtures":len(result["attempts"]),"no_data_attempts":sum(a.get("result")=="NO_DATA" for a in result["attempts"]),
        "error_attempts":sum(a.get("result")=="ERROR" for a in result["attempts"]),
        "backlog_rows":len(after["rows"]),"backlog_pending":after["pending"],"backlog_captured":after["captured"],
        "new_event_rows":result["new_rows"],"total_event_rows":len(result["rows"]),"warnings":result["warnings"],
        "research_only":True,"creates_signal":False,"probability_mutation":False,"eligibility_mutation":False,
        "stake_changes":False,"forward_journal_mutation":False,
    }
    META.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(meta,ensure_ascii=False))


if __name__=="__main__":
    main()
