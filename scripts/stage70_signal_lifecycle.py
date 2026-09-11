#!/usr/bin/env python3
"""Stage 70 — unified lifecycle cards for canonical and WATCH signals.

Read-only aggregation over existing ops files. It creates no signals, makes no
API calls, changes no stakes/rules, and never mutates canonical forward data.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
OUT_CSV = OPS / "signal_lifecycle_events.csv"
OUT_JSON = OPS / "signal_lifecycle_cards.json"
OUT_MD = OPS / "signal_lifecycle_cards.md"
META = OPS / "stage70_last_run.json"

EVENT_FIELDS = [
    "entity_id", "entity_type", "rule_or_stage", "api_fixture_id", "league",
    "home_team", "away_team", "kickoff_utc", "event_time_utc", "event_type",
    "status", "selection", "bookmaker", "odds", "details",
]


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(name):
    p = OPS / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def first(row, *keys):
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            return str(v)
    return ""


def selection_ru(v):
    return {
        "Home": "П1", "H": "П1", "Away": "П2", "A": "П2",
        "Draw": "Х", "D": "Х", "O25": "ТБ(2.5)",
        "BTTS_YES": "ОЗ — Да", "BTTS_NO": "ОЗ — Нет",
        "YES": "ОЗ — Да", "NO": "ОЗ — Нет",
    }.get(str(v or ""), str(v or ""))


def add(events, base, event_time, event_type, status="", selection="", bookmaker="", odds="", details=""):
    if not event_time:
        return
    events.append({
        "entity_id": base.get("entity_id", ""),
        "entity_type": base.get("entity_type", ""),
        "rule_or_stage": base.get("rule_or_stage", ""),
        "api_fixture_id": base.get("api_fixture_id", ""),
        "league": base.get("league", ""),
        "home_team": base.get("home_team", ""),
        "away_team": base.get("away_team", ""),
        "kickoff_utc": base.get("kickoff_utc", ""),
        "event_time_utc": event_time,
        "event_type": event_type,
        "status": status,
        "selection": selection,
        "bookmaker": bookmaker,
        "odds": odds,
        "details": details,
    })


def canonical_events(events):
    forward = read_csv("forward_log.csv")
    user = {r.get("forward_id", ""): r for r in read_csv("user_forward_view.csv")}
    contexts = defaultdict(list)
    for r in read_csv("match_context_snapshots.csv"):
        contexts[r.get("forward_id", "")].append(r)
    weather = defaultdict(list)
    for r in read_csv("weather_snapshots.csv"):
        weather[r.get("forward_id", "")].append(r)
    rotation = defaultdict(list)
    for r in read_csv("rotation_snapshots.csv"):
        rotation[r.get("forward_id", "")].append(r)
    odds = defaultdict(list)
    for r in read_csv("odds_snapshots.csv"):
        odds[first(r, "forward_id", "api_fixture_id")].append(r)
    closes = defaultdict(list)
    for r in read_csv("closing_log.csv"):
        closes[first(r, "forward_id", "api_fixture_id")].append(r)
    fixture_events = defaultdict(list)
    for r in read_csv("fixture_events.csv"):
        fixture_events[first(r, "forward_id", "api_fixture_id")].append(r)

    for r in forward:
        fid = r.get("forward_id") or ""
        if not fid:
            continue
        u = user.get(fid, {})
        base = {
            "entity_id": fid,
            "entity_type": "CANONICAL",
            "rule_or_stage": r.get("rule") or "",
            "api_fixture_id": r.get("api_fixture_id") or "",
            "league": r.get("league") or "",
            "home_team": r.get("home_team") or "",
            "away_team": r.get("away_team") or "",
            "kickoff_utc": first(r, "kickoff_utc") or ((r.get("match_date") or "") + ("T" + r.get("kickoff_time") + ":00Z" if r.get("kickoff_time") else "")),
        }
        sel = selection_ru(first(u, "selection") or first(r, "bet_selection"))
        add(events, base, r.get("screened_at_utc") or "", "SIGNAL_CREATED", r.get("status") or "", sel,
            "Bet365", first(r, "trigger_selected_odds", "trigger_b365_away", "trigger_b365_home", "trigger_b365_draw"),
            "Canonical rule matched; trigger immutable")
        add(events, base, first(u, "paper_user_execution_at_utc"), "USER_EXECUTION_FROZEN", first(u, "user_execution_status"), sel,
            first(u, "paper_user_execution_bookmaker"), first(u, "paper_user_execution_odds"), "Prospective paper execution; not proof of real bet")
        for c in sorted(contexts.get(fid, []), key=lambda x: x.get("captured_at_utc") or ""):
            detail = "; ".join(x for x in [
                first(c, "snapshot_type"),
                ("lineups=" + first(c, "lineups_available")) if first(c, "lineups_available") else "",
                ("injuries=" + first(c, "injuries_count")) if first(c, "injuries_count") else "",
            ] if x)
            add(events, base, first(c, "captured_at_utc"), "CONTEXT_SNAPSHOT", first(c, "fixture_status"), sel, details=detail)
        for c in sorted(weather.get(fid, []), key=lambda x: x.get("captured_at_utc") or x.get("weather_captured_at_utc") or ""):
            add(events, base, first(c, "captured_at_utc", "weather_captured_at_utc"), "WEATHER_SNAPSHOT", selection=sel,
                details=f"temp={first(c,'temperature_c')}C precip={first(c,'precipitation_probability_pct')}%")
        for c in sorted(rotation.get(fid, []), key=lambda x: x.get("captured_at_utc") or x.get("rotation_captured_at_utc") or ""):
            add(events, base, first(c, "captured_at_utc", "rotation_captured_at_utc"), "XI_ROTATION", first(c, "rotation_verified"), sel,
                details=f"home_changed={first(c,'home_changed_starters')} away_changed={first(c,'away_changed_starters')}")
        key_opts = [fid, r.get("api_fixture_id") or ""]
        seen = set()
        for key in key_opts:
            for o in odds.get(key, []):
                sig = tuple(sorted(o.items()))
                if sig in seen: continue
                seen.add(sig)
                add(events, base, first(o, "captured_at_utc"), "ODDS_SNAPSHOT", first(o, "fixture_status"), sel,
                    first(o, "user_bookmaker", "bookmaker"), first(o, "user_selected_odds", "selected_odds", "odds"),
                    "Pre-kickoff odds snapshot")
            for o in closes.get(key, []):
                sig = tuple(sorted(o.items()))
                if sig in seen: continue
                seen.add(sig)
                add(events, base, first(o, "locked_at_utc", "captured_at_utc", "close_observed_at_utc"), "CLOSE_LOCKED", first(o, "status"), sel,
                    first(o, "user_bookmaker", "bookmaker"), first(o, "user_close_odds", "closing_odds", "odds"), "Latest observed pre-kickoff close")
            for o in fixture_events.get(key, []):
                sig = tuple(sorted(o.items()))
                if sig in seen: continue
                seen.add(sig)
                add(events, base, first(o, "captured_at_utc", "event_at_utc"), "FIXTURE_EVENT", first(o, "event_type", "status"), sel,
                    details=first(o, "details", "note", "reason"))
        if first(u, "result") or first(u, "status") in {"SETTLED", "VOID", "REVIEW"}:
            add(events, base, first(u, "settled_at_utc") or base["kickoff_utc"], "SETTLEMENT", first(u, "status"), sel,
                first(u, "paper_user_execution_bookmaker"), first(u, "paper_user_execution_odds"),
                f"result={first(u,'result')} user_profit_u={first(u,'user_profit_u')}")


def watch_events(events):
    for r in read_csv("stage65_watch_ledger.csv"):
        wid = r.get("watch_id") or ""
        if not wid:
            continue
        base = {
            "entity_id": wid, "entity_type": "WATCH", "rule_or_stage": first(r, "source_stage", "watch_family"),
            "api_fixture_id": r.get("api_fixture_id") or "", "league": r.get("league") or "",
            "home_team": r.get("home_team") or "", "away_team": r.get("away_team") or "",
            "kickoff_utc": r.get("kickoff_utc") or "",
        }
        sel = first(r, "selection_display") or selection_ru(first(r, "selection_code"))
        add(events, base, first(r, "crossed_at_utc"), "WATCH_CROSSING", "WATCH_ONLY", sel,
            first(r, "user_bookmaker"), first(r, "user_cross_odds"), f"movement_pp={first(r,'movement_pp')}")
        if first(r, "close_observed") == "YES":
            add(events, base, first(r, "close_observed_at_utc"), "WATCH_CLOSE", first(r, "close_status"), sel,
                first(r, "user_bookmaker"), first(r, "user_close_odds"), f"close_qualified={first(r,'close_qualified')}")
        if first(r, "settlement_status") in {"SETTLED", "VOID", "REVIEW"}:
            add(events, base, first(r, "settled_at_utc") or base["kickoff_utc"], "WATCH_SETTLEMENT", first(r, "settlement_status"), sel,
                first(r, "user_bookmaker"), first(r, "user_cross_odds"), f"result={first(r,'result')} profit_u={first(r,'user_profit_u')}")


def build_cards(events):
    grouped = defaultdict(list)
    for e in events:
        grouped[e["entity_id"]].append(e)
    cards = []
    for entity_id, rows in grouped.items():
        rows.sort(key=lambda x: (x.get("event_time_utc") or "", x.get("event_type") or ""))
        x = rows[0]
        cards.append({
            "entity_id": entity_id,
            "entity_type": x["entity_type"],
            "rule_or_stage": x["rule_or_stage"],
            "api_fixture_id": x["api_fixture_id"],
            "league": x["league"],
            "home_team": x["home_team"],
            "away_team": x["away_team"],
            "kickoff_utc": x["kickoff_utc"],
            "selection": next((r["selection"] for r in rows if r.get("selection")), ""),
            "latest_event": rows[-1]["event_type"],
            "latest_status": rows[-1]["status"],
            "event_count": len(rows),
            "timeline": rows,
        })
    cards.sort(key=lambda x: (x.get("kickoff_utc") or "", x.get("entity_type") or "", x.get("entity_id") or ""))
    return cards


def main():
    now = now_utc()
    events = []
    canonical_events(events)
    watch_events(events)
    events.sort(key=lambda x: (x.get("entity_id") or "", x.get("event_time_utc") or "", x.get("event_type") or ""))
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=EVENT_FIELDS, extrasaction="ignore")
        w.writeheader(); w.writerows(events)
    cards = build_cards(events)
    payload = {
        "generated_at_utc": iso(now), "status": "OK",
        "cards": cards,
        "summary": {
            "cards": len(cards),
            "canonical_cards": sum(1 for x in cards if x["entity_type"] == "CANONICAL"),
            "watch_cards": sum(1 for x in cards if x["entity_type"] == "WATCH"),
            "events": len(events),
        },
        "policy": {
            "read_only": True, "api_calls": 0, "creates_signals": False,
            "mutates_canonical": False, "purpose": "single chronological lifecycle per signal for future client/card views"
        }
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# PBK Signal Lifecycle", "", f"Обновлено UTC: {iso(now)}", "",
          f"Cards: {len(cards)} | canonical {payload['summary']['canonical_cards']} | WATCH {payload['summary']['watch_cards']} | events {len(events)}", ""]
    for c in cards:
        md += [f"## {c['entity_type']} | {c['rule_or_stage']} | {c['home_team']} — {c['away_team']}",
               f"- Ставка/рынок: {c['selection'] or '—'} | kickoff: {c['kickoff_utc']}",
               f"- Последнее событие: {c['latest_event']} | статус: {c['latest_status'] or '—'} | событий: {c['event_count']}"]
        for e in c["timeline"][-8:]:
            tail = " | ".join(x for x in [e.get("bookmaker"), e.get("odds"), e.get("details")] if x)
            md.append(f"  - {e['event_time_utc']} — {e['event_type']}" + (f" — {tail}" if tail else ""))
        md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    META.write_text(json.dumps({
        "run_at_utc": iso(now), "status": "OK", "cards": len(cards),
        "canonical_cards": payload["summary"]["canonical_cards"], "watch_cards": payload["summary"]["watch_cards"],
        "events": len(events), "api_calls": 0,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False))

if __name__ == "__main__":
    main()
