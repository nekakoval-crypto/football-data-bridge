#!/usr/bin/env python3
"""Stage 58: unified human-readable PBK daily brief.

Merges canonical forward signals with the latest operational context from
Stages 54-57. This is a presentation layer only; it never changes strategy
eligibility, trigger prices, stakes, settlement, or context snapshots.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
FORWARD = OPS / "forward_log.csv"
ODDS = OPS / "odds_snapshots.csv"
CONTEXT = OPS / "context_latest.csv"
STAGE56 = OPS / "stage56_latest.csv"
INTERNATIONAL = OPS / "international_context.csv"
OUT_JSON = OPS / "daily_brief.json"
OUT_MD = OPS / "daily_brief.md"
META = OPS / "stage58_last_run.json"


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def latest_by(rows, time_field="captured_at_utc"):
    out = {}
    for r in rows:
        fid = r.get("forward_id") or ""
        if not fid:
            continue
        cur = out.get(fid)
        if cur is None or (r.get(time_field) or "") > (cur.get(time_field) or ""):
            out[fid] = r
    return out


def safe(row, key):
    v = row.get(key)
    return "" if v is None else v


def float_or_none(v):
    try:
        return float(str(v))
    except Exception:
        return None


def kickoff_of(bet, ctx):
    if ctx.get("current_kickoff_utc"):
        return ctx["current_kickoff_utc"]
    d, t = bet.get("match_date") or "", bet.get("kickoff_time") or ""
    return f"{d}T{t}:00Z" if d and t else ""


def context_flags(ctx, intl, rotation, odds):
    flags = []
    for side in ("home", "away"):
        if ctx.get(f"{side}_prev_is_uefa_or_cup") == "YES":
            flags.append(f"{side.upper()}_PREV_UEFA_OR_CUP")
        if ctx.get(f"{side}_next_is_uefa_or_cup") == "YES":
            flags.append(f"{side.upper()}_NEXT_UEFA_OR_CUP")
    if intl.get("within_7d_before_fifa_window") == "YES":
        flags.append("WITHIN_7D_BEFORE_FIFA_WINDOW")
    if intl.get("within_7d_after_fifa_window") == "YES":
        flags.append("WITHIN_7D_AFTER_FIFA_WINDOW")
    if rotation.get("rotation_verified") != "YES":
        flags.append("OFFICIAL_ROTATION_PENDING")
    if odds.get("user_allowlist_configured") != "YES":
        flags.append("USER_BOOKMAKERS_NOT_CONFIGURED")
    elif not odds.get("user_best_odds"):
        flags.append("USER_EXECUTABLE_PRICE_NOT_OBSERVED")
    return flags


def user_execution_text(user_execution):
    status = user_execution.get("status") or ""
    if status == "AVAILABLE":
        return f"{user_execution.get('odds') or 'N/A'} @ {user_execution.get('bookmaker') or 'N/A'}"
    return status or "UNKNOWN"


def main():
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    active = [r for r in read_csv(FORWARD) if r.get("status") in {"PAPER", "OPEN", "REVIEW"}]
    odds = latest_by(read_csv(ODDS))
    ctx = latest_by(read_csv(CONTEXT))
    s56 = latest_by(read_csv(STAGE56), "weather_captured_at_utc")
    intl = {r.get("forward_id"): r for r in read_csv(INTERNATIONAL) if r.get("forward_id")}

    matches = []
    for bet in active:
        fid = bet.get("forward_id") or ""
        o, c, w, i = odds.get(fid, {}), ctx.get(fid, {}), s56.get(fid, {}), intl.get(fid, {})
        kickoff = kickoff_of(bet, c)
        snapshot_type = c.get("snapshot_type") or ""

        if snapshot_type in {"T24", "T3", "T60"}:
            injury_status = "QUERIED"
            injuries = {
                "total": safe(c, "injuries_count"),
                "home": safe(c, "home_injuries_count"),
                "away": safe(c, "away_injuries_count"),
            }
        else:
            injury_status = "NOT_QUERIED_YET"
            injuries = {"total": "", "home": "", "away": ""}

        user_allowlist = o.get("user_allowlist_configured") == "YES"
        if user_allowlist:
            user_execution = {
                "status": "AVAILABLE" if o.get("user_best_odds") else "NO_PRICE_OBSERVED",
                "odds": safe(o, "user_best_odds"),
                "bookmaker": safe(o, "user_best_book"),
            }
        else:
            user_execution = {"status": "NOT_CONFIGURED", "odds": "", "bookmaker": ""}

        match = {
            "forward_id": fid,
            "rule": safe(bet, "rule"),
            "league": safe(bet, "league"),
            "fixture_id": safe(bet, "api_fixture_id"),
            "kickoff_utc": kickoff,
            "home_team": safe(bet, "home_team"),
            "away_team": safe(bet, "away_team"),
            "selection": safe(bet, "bet_selection"),
            "stake_u": safe(bet, "stake_u"),
            "status": safe(bet, "status"),
            "trigger": {
                "source": safe(bet, "trigger_source"),
                "b365_home": safe(bet, "trigger_b365_home"),
                "b365_draw": safe(bet, "trigger_b365_draw"),
                "b365_away": safe(bet, "trigger_b365_away"),
                "selected_odds": safe(bet, "trigger_b365_away") if bet.get("bet_selection") == "Away" else safe(bet, "trigger_b365_draw"),
                "immutable": True,
            },
            "market_observed": {
                "captured_at_utc": safe(o, "captured_at_utc"),
                "best_odds": safe(o, "best_odds"),
                "best_bookmaker": safe(o, "best_book"),
                "bet365_odds": safe(o, "bet365_odds"),
                "api_odds_update_utc": safe(o, "api_odds_update_utc"),
                "note": "Observed market-best is not automatically a user-executable price",
            },
            "user_execution": user_execution,
            "league_state": {
                "home_rank": safe(bet, "home_rank"),
                "away_rank": safe(bet, "away_rank"),
                "home_points": safe(bet, "home_points"),
                "away_points": safe(bet, "away_points"),
                "home_played": safe(bet, "home_played"),
                "away_played": safe(bet, "away_played"),
                "home_last5_ppg": safe(bet, "home_last5_ppg"),
                "away_last5_ppg": safe(bet, "away_last5_ppg"),
            },
            "calendar": {
                "snapshot_type": snapshot_type,
                "captured_at_utc": safe(c, "captured_at_utc"),
                "referee": safe(c, "referee"),
                "venue": safe(c, "venue_name"),
                "city": safe(c, "venue_city"),
                "home_prev": {
                    "competition": safe(c, "home_prev_competition"), "opponent": safe(c, "home_prev_opponent"),
                    "date_utc": safe(c, "home_prev_date_utc"), "rest_hours": safe(c, "home_rest_hours"),
                },
                "away_prev": {
                    "competition": safe(c, "away_prev_competition"), "opponent": safe(c, "away_prev_opponent"),
                    "date_utc": safe(c, "away_prev_date_utc"), "rest_hours": safe(c, "away_rest_hours"),
                },
                "home_next": {
                    "competition": safe(c, "home_next_competition"), "opponent": safe(c, "home_next_opponent"),
                    "date_utc": safe(c, "home_next_date_utc"), "hours_after": safe(c, "home_hours_to_next"),
                },
                "away_next": {
                    "competition": safe(c, "away_next_competition"), "opponent": safe(c, "away_next_opponent"),
                    "date_utc": safe(c, "away_next_date_utc"), "hours_after": safe(c, "away_hours_to_next"),
                },
            },
            "injuries": {"status": injury_status, **injuries},
            "weather": {
                "snapshot_type": safe(w, "weather_snapshot_type"),
                "captured_at_utc": safe(w, "weather_captured_at_utc"),
                "temperature_c": safe(w, "temperature_c"),
                "precipitation_probability_pct": safe(w, "precipitation_probability_pct"),
                "precipitation_mm": safe(w, "precipitation_mm"),
                "wind_speed_kmh": safe(w, "wind_speed_10m_kmh"),
                "wind_gusts_kmh": safe(w, "wind_gusts_10m_kmh"),
                "visibility_m": safe(w, "visibility_m"),
                "weather_code": safe(w, "weather_code"),
                "role": "context-only",
            },
            "rotation": {
                "status": "VERIFIED" if w.get("rotation_verified") == "YES" else "WAITING_OFFICIAL_XI",
                "captured_at_utc": safe(w, "rotation_captured_at_utc"),
                "home_retained_starters": safe(w, "home_retained_starters"),
                "away_retained_starters": safe(w, "away_retained_starters"),
                "home_changed_starters": safe(w, "home_changed_starters"),
                "away_changed_starters": safe(w, "away_changed_starters"),
                "home_retained_pct": safe(w, "home_retained_pct"),
                "away_retained_pct": safe(w, "away_retained_pct"),
            },
            "international": {
                "fifa_relation": safe(i, "fifa_relation"),
                "window": safe(i, "fifa_window_name"),
                "hours_to_start": safe(i, "hours_to_fifa_window_start"),
                "hours_since_end": safe(i, "hours_since_fifa_window_end"),
                "within_7d_before": safe(i, "within_7d_before_fifa_window"),
                "within_7d_after": safe(i, "within_7d_after_fifa_window"),
                "player_level": safe(i, "player_level_international_status") or "UNVERIFIED",
                "player_level_reason": safe(i, "player_level_reason") or "No direct call-up/appearance evidence",
            },
            "flags": context_flags(c, i, w, o),
        }
        matches.append(match)

    matches.sort(key=lambda m: m.get("kickoff_utc") or "")
    payload = {
        "generated_at_utc": now,
        "status": "OK",
        "active_signals": len(matches),
        "policy": {
            "trigger": "immutable Bet365 first capture",
            "market_best": "observed API market price; not necessarily user executable",
            "user_execution": "only prices from configured executable bookmakers are treated as user-executable",
            "context": "explanatory only; does not change locked rules",
        },
        "matches": matches,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# PBK Daily Brief",
        "",
        f"Generated UTC: {now}",
        f"Active canonical signals: {len(matches)}",
        "",
        "> Context layers are explanatory only. Market-best and user-executable prices are shown separately.",
        "",
    ]
    for m in matches:
        trig = m["trigger"]
        market = m["market_observed"]
        cal = m["calendar"]
        weather = m["weather"]
        intl_m = m["international"]
        md += [
            f"## {m['rule']} | {m['home_team']} — {m['away_team']}",
            f"- Kickoff UTC: {m['kickoff_utc']} | Selection: {m['selection']} | Stake: {m['stake_u']}u",
            f"- Trigger Bet365: H {trig['b365_home']} / D {trig['b365_draw']} / A {trig['b365_away']} (immutable)",
            f"- Market-best observed: {market['best_odds']} @ {market['best_bookmaker']} | Bet365 now: {market['bet365_odds']}",
            f"- User-executable: {user_execution_text(m['user_execution'])}",
            f"- Referee / venue: {cal['referee'] or 'TBD'} | {cal['venue'] or 'TBD'}, {cal['city'] or 'TBD'}",
            f"- Previous: home {cal['home_prev']['competition']} vs {cal['home_prev']['opponent']} ({cal['home_prev']['rest_hours']}h rest); away {cal['away_prev']['competition']} vs {cal['away_prev']['opponent']} ({cal['away_prev']['rest_hours']}h rest)",
            f"- Next: home {cal['home_next']['competition']} vs {cal['home_next']['opponent']} ({cal['home_next']['hours_after']}h after); away {cal['away_next']['competition']} vs {cal['away_next']['opponent']} ({cal['away_next']['hours_after']}h after)",
            f"- Injuries: {m['injuries']['status']}",
            f"- Weather [{weather['snapshot_type'] or 'pending'}]: {weather['temperature_c']}°C, precip {weather['precipitation_probability_pct']}%, wind {weather['wind_speed_kmh']} km/h, gusts {weather['wind_gusts_kmh']} km/h",
            f"- Rotation: {m['rotation']['status']}",
            f"- International: {intl_m['fifa_relation']} FIFA window; to start {intl_m['hours_to_start']}h; player-level {intl_m['player_level']}",
            f"- Flags: {', '.join(m['flags']) if m['flags'] else 'none'}",
            "",
        ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    meta = {"run_at_utc": now, "status": "OK", "active_signals": len(matches), "json": str(OUT_JSON), "markdown": str(OUT_MD)}
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
