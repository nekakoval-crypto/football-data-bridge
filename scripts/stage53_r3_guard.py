#!/usr/bin/env python3
"""Guard Stage 53 against an unverified live reproduction of Stage 48 R3.

The MASTER freezes the *idea* of R3 (Big-5, Monday, both teams <=10 league
matches remaining, Draw) but explicitly says the exact Stage 48 implementation
must be recovered before a new live implementation is treated as R3.

This guard runs after Stage 53 screening and before Git commit. It:
- removes same-run R3 rows from canonical forward_log.csv;
- preserves them append-only in r3_unverified_candidates.csv;
- marks screen/passport rows as CANDIDATE_UNVERIFIED rather than R3=YES;
- leaves R1/R2 signals untouched, including overlaps.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
FORWARD = OPS / "forward_log.csv"
SCREEN = OPS / "latest_screen.csv"
PASSPORTS = OPS / "context_passports.csv"
META = OPS / "last_run.json"
R3_CANDIDATES = OPS / "r3_unverified_candidates.csv"

CANDIDATE_FIELDS = [
    "candidate_id", "screened_at_utc", "div", "league", "api_fixture_id", "match_date", "kickoff_time",
    "weekday", "home_team", "away_team", "home_remaining", "away_remaining", "best_draw_odds",
    "best_draw_book", "odds_last_update_utc", "status", "reason"
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


def remove_rule(rule_string, rule):
    rules = [x for x in (rule_string or "").split("|") if x and x != rule]
    return "|".join(rules)


def main():
    if not META.exists():
        print("R3 guard: no last_run.json; nothing to do")
        return
    meta = json.loads(META.read_text(encoding="utf-8"))
    run_at = meta.get("screened_at_utc") or ""

    forward, forward_fields = read_csv(FORWARD)
    screen, screen_fields = read_csv(SCREEN)
    passports, passport_fields = read_csv(PASSPORTS)
    candidates, _ = read_csv(R3_CANDIDATES)
    candidate_ids = {r.get("candidate_id") for r in candidates}

    # Capture every same-run row that the current provisional implementation labelled R3.
    provisional = [r for r in screen if r.get("screened_at_utc") == run_at and r.get("r3") == "YES"]
    added_candidates = 0
    for r in provisional:
        cid = f"R3U|{r.get('div')}|{r.get('api_fixture_id')}|{run_at}"
        if cid not in candidate_ids:
            candidates.append({
                "candidate_id": cid,
                "screened_at_utc": run_at,
                "div": r.get("div"),
                "league": r.get("league"),
                "api_fixture_id": r.get("api_fixture_id"),
                "match_date": r.get("match_date"),
                "kickoff_time": r.get("kickoff_time"),
                "weekday": r.get("weekday"),
                "home_team": r.get("home_team"),
                "away_team": r.get("away_team"),
                "home_remaining": r.get("home_remaining"),
                "away_remaining": r.get("away_remaining"),
                "best_draw_odds": r.get("best_draw_odds"),
                "best_draw_book": r.get("best_draw_book"),
                "odds_last_update_utc": r.get("odds_last_update_utc"),
                "status": "CANDIDATE_UNVERIFIED",
                "reason": "Exact Stage 48 R3 implementation not recovered; blocked from canonical forward"
            })
            candidate_ids.add(cid)
            added_candidates += 1

    # Same-run R3 forward rows have not been committed yet; block them before canonical persistence.
    before = len(forward)
    forward = [r for r in forward if not (r.get("rule") == "R3" and r.get("screened_at_utc") == run_at)]
    blocked_forward = before - len(forward)

    # R3 remains visible diagnostically, but never masquerades as verified R3.
    for r in screen:
        if r.get("screened_at_utc") == run_at and r.get("r3") == "YES":
            r["r3"] = "CANDIDATE_UNVERIFIED"
            r["signal_rules"] = remove_rule(r.get("signal_rules"), "R3")
            if not r.get("signal_rules"):
                r["passport_status"] = "WATCH_R3_UNVERIFIED"
            append_note(r, "R3 blocked: exact Stage 48 implementation not recovered")

    kept_passports = []
    for r in passports:
        if r.get("screened_at_utc") == run_at and r.get("r3") == "YES":
            r["r3"] = "CANDIDATE_UNVERIFIED"
            r["signal_rules"] = remove_rule(r.get("signal_rules"), "R3")
            append_note(r, "R3 blocked: exact Stage 48 implementation not recovered")
            # Keep the passport only if it is independently R1/R2.
            if r.get("signal_rules"):
                kept_passports.append(r)
        else:
            kept_passports.append(r)
    passports = kept_passports

    write_csv(FORWARD, forward_fields, forward)
    write_csv(SCREEN, screen_fields, screen)
    write_csv(PASSPORTS, passport_fields, passports)
    write_csv(R3_CANDIDATES, CANDIDATE_FIELDS, candidates)

    meta["r3_exact_reproduction_verified"] = False
    meta["r3_candidates_blocked_this_run"] = len(provisional)
    meta["r3_forward_rows_removed_before_commit"] = blocked_forward
    meta["r3_unverified_candidates_total"] = len(candidates)
    meta["signal_matches_after_r3_guard"] = len(passports)
    meta["forward_rows_after_r3_guard"] = len(forward)
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "run_at": run_at,
        "provisional_r3": len(provisional),
        "blocked_forward": blocked_forward,
        "new_unverified_candidates": added_candidates,
        "canonical_passports": len(passports),
        "canonical_forward_rows": len(forward)
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
