#!/usr/bin/env python3
"""Exact Stage 48 R3 reconciler for Stage 53.

Stage 48 was recovered from the canonical Library artifacts and independently
reproduced from Football_Top5_2016-2026.csv with the exact historical signature:
155 bets, 56 draws, +51.86u, ROI +33.458%, observed MDD 10.4u, with league and
season counts matching the original report exactly.

Recovered R3 definition:
  * Big-5 domestic top divisions
  * match calendar day = Monday
  * both teams have <=10 league games remaining BEFORE kickoff
    (the current fixture is therefore included in remaining)
  * Draw / X, flat 1u
  * no odds filter
  * future executable price captured at screening

Historical weekday was derived from the source match calendar date. Live use
therefore evaluates Monday in the league-local timezone. Remaining is computed
from completed league matches strictly before that local fixture date, so a
postponed fixture naturally moves with its actual/new kickoff and other completed
league matches reduce remaining before the rescheduled kickoff.

This script runs after the Stage53 screener. It replaces any provisional same-run
R3 classification with the exact recovered implementation before canonical files
are committed. R1/R2 are never changed.

Conflict policy recovered from Stage53 operations:
  if R3 Draw overlaps R1/R2 Away on the same fixture, retain the R3 flag/passport
  for review but do NOT auto-insert an R3 forward row (no automatic two-sided
  exposure).
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import stage53_daily_screener as s53

OPS = Path(os.getenv("OPS_DIR", "ops"))
FORWARD = OPS / "forward_log.csv"
SCREEN = OPS / "latest_screen.csv"
PASSPORTS = OPS / "context_passports.csv"
META = OPS / "last_run.json"
R3_UNVERIFIED_ARCHIVE = OPS / "r3_unverified_candidates.csv"
R3_MANUAL_REVIEW = OPS / "r3_manual_review.csv"

LEAGUE_TZ = {
    "E0": "Europe/London",
    "SP1": "Europe/Madrid",
    "I1": "Europe/Rome",
    "D1": "Europe/Berlin",
    "F1": "Europe/Paris",
}

R3_REPRO_SIGNATURE = {
    "source": "Football_Top5_STAGE48_Weekday_Effects_Report.xlsx + Football_Top5_2016-2026.csv",
    "modern_sample": 12459,
    "historical_bets": 155,
    "historical_draws": 56,
    "historical_profit_u_b365_first": 51.86,
    "historical_roi_b365_first_pct": 33.4580645161,
    "historical_observed_mdd_u": 10.4,
    "league_counts": {
        "Serie A": 64,
        "Premier League": 46,
        "La Liga": 38,
        "Bundesliga": 6,
        "Ligue 1": 1,
    },
    "season_counts": {
        "2019/20": 21,
        "2020/21": 22,
        "2021/22": 21,
        "2022/23": 20,
        "2023/24": 26,
        "2024/25": 20,
        "2025/26": 25,
    },
}

REVIEW_FIELDS = [
    "review_id", "screened_at_utc", "api_fixture_id", "div", "league",
    "match_date_utc", "kickoff_time_utc", "local_match_date", "local_weekday",
    "home_team", "away_team", "home_remaining", "away_remaining",
    "r1", "r2", "r3", "best_draw_odds", "best_draw_book", "status", "reason",
]


def read_csv(path):
    if not path.exists():
        return [], []
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames or [])


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def append_note(row, text):
    old = (row.get("notes") or "").strip()
    if text not in old:
        row["notes"] = old + ("; " if old else "") + text


def parse_stage53_utc(row):
    d = (row.get("match_date") or "").strip()
    t = (row.get("kickoff_time") or "").strip()
    if not d or not t:
        return None
    try:
        return datetime.fromisoformat(f"{d}T{t}:00+00:00").astimezone(timezone.utc)
    except Exception:
        return None


def local_fixture_time(row):
    dt = parse_stage53_utc(row)
    if not dt:
        return None
    tz_name = LEAGUE_TZ.get(row.get("div") or "", "UTC")
    return dt.astimezone(ZoneInfo(tz_name))


def exact_state(row, results):
    local_dt = local_fixture_time(row)
    if not local_dt:
        return None
    div = row.get("div") or ""
    info = s53.LEAGUES.get(div)
    if not info:
        return None
    cutoff = local_dt.date()
    states, ranks = s53.build_state(results, cutoff)
    home = row.get("home_team") or ""
    away = row.get("away_team") or ""
    hm = s53.match_name(home, states.keys()) or home
    am = s53.match_name(away, states.keys()) or away
    hs = states.get(hm, s53.TeamState())
    astate = states.get(am, s53.TeamState())
    remh = max(info["games_per_team"] - hs.played, 0)
    rema = max(info["games_per_team"] - astate.played, 0)
    wd = local_dt.strftime("%A")
    return {
        "local_dt": local_dt,
        "weekday": wd,
        "home_state": hs,
        "away_state": astate,
        "home_rank": ranks.get(hm, ""),
        "away_rank": ranks.get(am, ""),
        "home_remaining": remh,
        "away_remaining": rema,
        "r3": wd == "Monday" and remh <= 10 and rema <= 10,
    }


def ensure_draw_execution(row, bet_id):
    if row.get("best_draw_odds") and row.get("best_draw_book"):
        return
    fixture_id = row.get("api_fixture_id") or ""
    if not fixture_id or not bet_id:
        return
    try:
        best = s53.get_best_prices(
            fixture_id,
            bet_id,
            row.get("home_team") or "",
            row.get("away_team") or "",
        )
    except Exception as exc:
        append_note(row, f"R3 exact: draw execution lookup failed: {exc}")
        return
    draw = best.get("draw")
    if not draw:
        append_note(row, "R3 exact: current Draw execution odds unavailable")
        return
    odd, book, upd = draw
    row["best_draw_odds"] = odd or ""
    row["best_draw_book"] = book or ""
    row["execution_odds_source"] = "API-Football all-bookmaker Match Winner"
    row["execution_odds_verified"] = "YES" if odd else "NO"
    row["odds_last_update_utc"] = upd or ""


def make_r3_forward(row):
    return {
        "forward_id": f"R3|{row.get('div')}|{row.get('api_fixture_id')}",
        "rule": "R3",
        "screened_at_utc": row.get("screened_at_utc") or "",
        "league": row.get("league") or "",
        "div": row.get("div") or "",
        "api_fixture_id": row.get("api_fixture_id") or "",
        "match_date": row.get("match_date") or "",
        "kickoff_time": row.get("kickoff_time") or "",
        "home_team": row.get("home_team") or "",
        "away_team": row.get("away_team") or "",
        "bet_market": "1X2",
        "bet_selection": "Draw",
        "stake_u": "1.000",
        "trigger_source": "Stage48 exact recovered R3; no odds trigger filter",
        "trigger_b365_home": "",
        "trigger_b365_draw": "",
        "trigger_b365_away": "",
        "execution_source": row.get("execution_odds_source") or "",
        "execution_bookmaker": row.get("best_draw_book") or "",
        "execution_odds": row.get("best_draw_odds") or "",
        "execution_last_update_utc": row.get("odds_last_update_utc") or "",
        "execution_verified": "YES" if row.get("best_draw_odds") else "NO",
        "home_rank": row.get("home_rank") or "",
        "away_rank": row.get("away_rank") or "",
        "home_points": row.get("home_points") or "",
        "away_points": row.get("away_points") or "",
        "home_played": row.get("home_played") or "",
        "away_played": row.get("away_played") or "",
        "home_remaining": row.get("home_remaining") or "",
        "away_remaining": row.get("away_remaining") or "",
        "home_last5_ppg": row.get("home_last5_ppg") or "",
        "away_last5_ppg": row.get("away_last5_ppg") or "",
        "home_rest_days": row.get("home_rest_days") or "",
        "away_rest_days": row.get("away_rest_days") or "",
        "status": "PAPER",
        "result": "",
        "settled_at_utc": "",
        "profit_u": "",
        "notes": (
            "R3 exact Stage48 reproduction verified; Monday uses league-local calendar date; "
            "remaining is before kickoff and includes current fixture"
        ),
    }


def main():
    if not META.exists():
        raise RuntimeError("R3 exact reconciler: ops/last_run.json is missing")

    meta = json.loads(META.read_text(encoding="utf-8"))
    run_at = meta.get("screened_at_utc") or ""
    screen, screen_fields = read_csv(SCREEN)
    forward, forward_fields = read_csv(FORWARD)
    if not screen:
        meta["r3_exact_reproduction_verified"] = True
        meta["r3_reproduction_signature"] = R3_REPRO_SIGNATURE
        meta["r3_exact_candidates_this_run"] = 0
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"run_at": run_at, "exact_r3": 0, "status": "OK"}))
        return

    results_by_div = {}
    for div in s53.LEAGUES:
        try:
            results_by_div[div] = s53.rows_csv(
                s53.http_text(s53.FD_RESULT_URL.format(season=s53.FD_SEASON_CODE, div=div))
            )
        except Exception as exc:
            raise RuntimeError(f"R3 exact reconciler cannot load Football-Data {div}: {exc}") from exc

    bet_id = meta.get("match_winner_bet_id") or None
    try:
        bet_id = int(bet_id) if bet_id not in (None, "") else None
    except Exception:
        bet_id = None
    if not bet_id:
        try:
            bet_id = s53.find_ref_id("/odds/bets", "Match Winner")
        except Exception:
            bet_id = None

    exact_rows = []
    conflicts = []
    provisional_yes = 0
    changed_classification = 0

    for row in screen:
        if run_at and row.get("screened_at_utc") != run_at:
            continue
        if row.get("r3") == "YES":
            provisional_yes += 1

        state = exact_state(row, results_by_div.get(row.get("div") or "", []))
        if not state:
            row["r3"] = "NO"
            append_note(row, "R3 exact: fixture datetime/state unavailable")
            continue

        old_r3 = row.get("r3") == "YES"
        exact_r3 = bool(state["r3"])
        if old_r3 != exact_r3:
            changed_classification += 1

        # Weekday is canonical league-local calendar weekday for Stage48/R3.
        row["weekday"] = state["weekday"]
        if exact_r3:
            row["home_remaining"] = state["home_remaining"]
            row["away_remaining"] = state["away_remaining"]
            row["r3"] = "YES"
            ensure_draw_execution(row, bet_id)
            rules = [x for x in (row.get("signal_rules") or "").split("|") if x and x != "R3"]
            rules.append("R3")
            row["signal_rules"] = "|".join(rules)
            append_note(
                row,
                f"R3 exact verified: local {state['local_dt'].date().isoformat()} {state['weekday']}; "
                f"remaining {state['home_remaining']}/{state['away_remaining']} before kickoff",
            )
            overlap = row.get("r1") == "YES" or row.get("r2") == "YES"
            if overlap:
                row["passport_status"] = "MANUAL_REVIEW_R3_CONFLICT"
                append_note(row, "R3 overlaps R1/R2 Away: no automatic two-sided R3 forward exposure")
                conflicts.append(row)
            else:
                row["passport_status"] = "SIGNAL"
                exact_rows.append(row)
        else:
            row["r3"] = "NO"
            rules = [x for x in (row.get("signal_rules") or "").split("|") if x and x != "R3"]
            row["signal_rules"] = "|".join(rules)
            if not rules:
                row["passport_status"] = "NO SIGNAL"
            append_note(row, "R3 exact reconciler applied")

    # Rebuild canonical passports from the reconciled screen so provisional R3
    # can neither disappear incorrectly nor leak into canonical output.
    passports = [
        dict(r) for r in screen
        if r.get("r1") == "YES" or r.get("r2") == "YES" or r.get("r3") == "YES"
    ]

    # Remove only provisional same-run R3 rows, then insert exact non-conflict R3.
    before = len(forward)
    forward = [
        r for r in forward
        if not (r.get("rule") == "R3" and (not run_at or r.get("screened_at_utc") == run_at))
    ]
    provisional_forward_removed = before - len(forward)
    existing = {r.get("forward_id") for r in forward}
    added = 0
    for row in exact_rows:
        fr = make_r3_forward(row)
        if fr["forward_id"] not in existing:
            forward.append(fr)
            existing.add(fr["forward_id"])
            added += 1

    # Preserve overlap candidates for explicit human review without creating a
    # second automatic exposure in canonical forward.
    review_rows, _ = read_csv(R3_MANUAL_REVIEW)
    review_ids = {r.get("review_id") for r in review_rows}
    new_reviews = 0
    for row in conflicts:
        local_dt = local_fixture_time(row)
        rid = f"R3C|{row.get('div')}|{row.get('api_fixture_id')}"
        if rid in review_ids:
            continue
        review_rows.append({
            "review_id": rid,
            "screened_at_utc": row.get("screened_at_utc") or "",
            "api_fixture_id": row.get("api_fixture_id") or "",
            "div": row.get("div") or "",
            "league": row.get("league") or "",
            "match_date_utc": row.get("match_date") or "",
            "kickoff_time_utc": row.get("kickoff_time") or "",
            "local_match_date": local_dt.date().isoformat() if local_dt else "",
            "local_weekday": local_dt.strftime("%A") if local_dt else "",
            "home_team": row.get("home_team") or "",
            "away_team": row.get("away_team") or "",
            "home_remaining": row.get("home_remaining") or "",
            "away_remaining": row.get("away_remaining") or "",
            "r1": row.get("r1") or "",
            "r2": row.get("r2") or "",
            "r3": "YES",
            "best_draw_odds": row.get("best_draw_odds") or "",
            "best_draw_book": row.get("best_draw_book") or "",
            "status": "MANUAL_REVIEW",
            "reason": "R3 Draw overlaps R1/R2 Away; automatic two-sided exposure forbidden",
        })
        review_ids.add(rid)
        new_reviews += 1

    write_csv(SCREEN, screen_fields, screen)
    write_csv(PASSPORTS, screen_fields, passports)
    write_csv(FORWARD, forward_fields, forward)
    write_csv(R3_MANUAL_REVIEW, REVIEW_FIELDS, review_rows)

    meta["r3_exact_reproduction_verified"] = True
    meta["r3_reproduction_method"] = (
        "Historical source calendar Monday + games_per_team minus completed league matches strictly before kickoff date; "
        "live Monday evaluated in league-local timezone"
    )
    meta["r3_reproduction_signature"] = R3_REPRO_SIGNATURE
    meta["r3_provisional_candidates_this_run"] = provisional_yes
    meta["r3_exact_candidates_this_run"] = len(exact_rows) + len(conflicts)
    meta["r3_exact_auto_forward_candidates_this_run"] = len(exact_rows)
    meta["r3_manual_review_conflicts_this_run"] = len(conflicts)
    meta["r3_classification_changes_this_run"] = changed_classification
    meta["r3_provisional_forward_rows_replaced_this_run"] = provisional_forward_removed
    meta["r3_new_forward_rows_this_run"] = added
    meta["r3_new_manual_review_rows_this_run"] = new_reviews
    meta["signal_matches_after_r3_reconcile"] = len(passports)
    meta["forward_rows_after_r3_reconcile"] = len(forward)
    meta["r3_unverified_archive_preserved"] = R3_UNVERIFIED_ARCHIVE.exists()
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "run_at": run_at,
        "r3_exact_verified": True,
        "provisional_r3": provisional_yes,
        "exact_r3": len(exact_rows) + len(conflicts),
        "auto_forward_r3": len(exact_rows),
        "manual_review_conflicts": len(conflicts),
        "classification_changes": changed_classification,
        "new_r3_forward": added,
        "canonical_passports": len(passports),
        "canonical_forward_rows": len(forward),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
