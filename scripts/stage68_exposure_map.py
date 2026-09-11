#!/usr/bin/env python3
"""Stage 68 — logical exposure and conflict map for PBK.

Read-only portfolio governance. Canonical rule rows remain untouched.
Identical fixture+market+selection rows are treated as one conceptual exposure
(e.g. R1 and R2 overlapping on the same Away 1X2 selection). Distinct canonical
selections on the same fixture are surfaced for manual review, never silently
netted or doubled.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
FORWARD = OPS / "forward_log.csv"
USER = OPS / "user_forward_view.csv"
OUT_CSV = OPS / "exposure_map.csv"
OUT_JSON = OPS / "exposure_summary.json"
OUT_MD = OPS / "exposure_summary.md"
META = OPS / "stage68_last_run.json"

ACTIVE_STATUSES = {"PAPER", "OPEN", "REVIEW"}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fnum(v, default=0.0):
    try:
        return float(str(v).strip())
    except Exception:
        return default


def norm(v):
    return " ".join(str(v or "").strip().lower().split())


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def watch_crossings():
    out = []
    specs = [
        ("Stage61", "stage61_market_crossings.csv"),
        ("Stage62", "stage62_ou_crossings.csv"),
        ("Stage63", "stage63_btts_crossings.csv"),
    ]
    for stage, name in specs:
        for r in read_csv(OPS / name):
            out.append({
                "stage": stage,
                "watch_id": r.get("watch_id") or "",
                "api_fixture_id": str(r.get("api_fixture_id") or ""),
                "selection": r.get("display_selection") or ("ТБ(2.5)" if stage == "Stage62" else "П1/П2 steam"),
            })
    return out


def display_selection(sel):
    return {"home": "П1", "draw": "Х", "away": "П2"}.get(norm(sel), sel or "")


def main():
    now = now_iso()
    forward = read_csv(FORWARD)
    user = read_csv(USER)
    fwd_by_id = {r.get("forward_id") or "": r for r in forward}

    raw = []
    for u in user:
        if str(u.get("status") or "").upper() not in ACTIVE_STATUSES:
            continue
        fid = u.get("forward_id") or ""
        f = fwd_by_id.get(fid, {})
        fixture_id = str(u.get("api_fixture_id") or f.get("api_fixture_id") or "")
        market = f.get("bet_market") or "UNKNOWN"
        selection = u.get("selection") or f.get("bet_selection") or ""
        stake = fnum(u.get("stake_u") or f.get("stake_u") or 1.0, 1.0)
        raw.append({
            "forward_id": fid,
            "rule": u.get("rule") or f.get("rule") or "",
            "api_fixture_id": fixture_id,
            "kickoff_utc": u.get("kickoff_utc") or "",
            "league": f.get("league") or "",
            "home_team": u.get("home_team") or f.get("home_team") or "",
            "away_team": u.get("away_team") or f.get("away_team") or "",
            "market": market,
            "selection": selection,
            "stake_u": stake,
            "user_odds": u.get("paper_user_execution_odds") or "",
            "user_bookmaker": u.get("paper_user_execution_bookmaker") or "",
            "status": u.get("status") or "",
        })

    # One logical exposure for identical fixture+market+selection.
    groups = defaultdict(list)
    for r in raw:
        key = (r["api_fixture_id"], norm(r["market"]), norm(r["selection"]))
        groups[key].append(r)

    watch = watch_crossings()
    watches_by_fixture = defaultdict(list)
    for w in watch:
        watches_by_fixture[w["api_fixture_id"]].append(w)

    exposures = []
    by_fixture_keys = defaultdict(list)
    for key, rows in groups.items():
        first = rows[0]
        logical_stake = max(r["stake_u"] for r in rows) if rows else 0.0
        rules = sorted({r["rule"] for r in rows if r["rule"]})
        raw_stake = sum(r["stake_u"] for r in rows)
        x = {
            "exposure_id": f"EXP|{first['api_fixture_id']}|{first['market']}|{first['selection']}",
            "api_fixture_id": first["api_fixture_id"],
            "kickoff_utc": first["kickoff_utc"],
            "league": first["league"],
            "home_team": first["home_team"],
            "away_team": first["away_team"],
            "market": first["market"],
            "selection": first["selection"],
            "display_selection": display_selection(first["selection"]),
            "trigger_rules": "+".join(rules),
            "raw_rule_rows": len(rows),
            "raw_rule_stake_u": f"{raw_stake:.3f}",
            "logical_exposure_u": f"{logical_stake:.3f}",
            "deduplicated_u": f"{max(0.0, raw_stake-logical_stake):.3f}",
            "user_bookmaker": first["user_bookmaker"],
            "user_odds": first["user_odds"],
            "fixture_conflict": "NO",
            "watch_overlap_count": len(watches_by_fixture.get(first["api_fixture_id"], [])),
            "governance": "ONE_CONCEPTUAL_EXPOSURE" if len(rows) > 1 else "SINGLE_RULE_EXPOSURE",
        }
        exposures.append(x)
        by_fixture_keys[first["api_fixture_id"]].append(x)

    conflicts = []
    for fixture_id, rows in by_fixture_keys.items():
        if len(rows) <= 1:
            continue
        distinct = {(norm(r["market"]), norm(r["selection"])) for r in rows}
        if len(distinct) > 1:
            for r in rows:
                r["fixture_conflict"] = "YES"
                r["governance"] = "MANUAL_REVIEW_DISTINCT_CANONICAL_EXPOSURES"
            conflicts.append({
                "api_fixture_id": fixture_id,
                "match": f"{rows[0]['home_team']} — {rows[0]['away_team']}",
                "exposures": [f"{r['market']}:{r['display_selection']} ({r['trigger_rules']})" for r in rows],
            })

    exposures.sort(key=lambda r: (r["kickoff_utc"], r["api_fixture_id"], r["market"], r["selection"]))

    fields = [
        "exposure_id", "api_fixture_id", "kickoff_utc", "league", "home_team", "away_team",
        "market", "selection", "display_selection", "trigger_rules", "raw_rule_rows",
        "raw_rule_stake_u", "logical_exposure_u", "deduplicated_u", "user_bookmaker",
        "user_odds", "fixture_conflict", "watch_overlap_count", "governance",
    ]
    write_csv(OUT_CSV, fields, exposures)

    logical_total = sum(fnum(r["logical_exposure_u"]) for r in exposures)
    raw_total = sum(fnum(r["raw_rule_stake_u"]) for r in exposures)
    dedup_total = sum(fnum(r["deduplicated_u"]) for r in exposures)

    by_day = defaultdict(float)
    by_league = defaultdict(float)
    by_team = defaultdict(float)
    for r in exposures:
        stake = fnum(r["logical_exposure_u"])
        day = (r.get("kickoff_utc") or "")[:10]
        if day:
            by_day[day] += stake
        by_league[r.get("league") or "UNKNOWN"] += stake
        by_team[r.get("home_team") or "UNKNOWN"] += stake
        by_team[r.get("away_team") or "UNKNOWN"] += stake

    watch_overlap_fixtures = sorted({r["api_fixture_id"] for r in exposures if int(r["watch_overlap_count"] or 0) > 0})

    payload = {
        "generated_at_utc": now,
        "status": "OK",
        "active_rule_rows": len(raw),
        "logical_exposures": len(exposures),
        "raw_rule_stake_u": round(raw_total, 3),
        "logical_exposure_u": round(logical_total, 3),
        "deduplicated_overlap_u": round(dedup_total, 3),
        "canonical_conflict_fixtures": len(conflicts),
        "watch_overlap_fixtures": len(watch_overlap_fixtures),
        "by_day_u": {k: round(v, 3) for k, v in sorted(by_day.items())},
        "by_league_u": {k: round(v, 3) for k, v in sorted(by_league.items())},
        "by_team_u": {k: round(v, 3) for k, v in sorted(by_team.items())},
        "conflicts": conflicts,
        "policy": {
            "identical_fixture_market_selection": "count as one conceptual exposure; do not multiply stake because multiple rules fired",
            "distinct_canonical_exposures_same_fixture": "manual review; never auto-net and never auto-double",
            "research_watch_overlap": "informational only; WATCH never adds canonical exposure",
            "real_money": "none; this is paper governance",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# PBK Exposure & Conflict Map",
        "",
        f"Обновлено UTC: {now}",
        f"Активные rule-строки: {len(raw)} | логических экспозиций: {len(exposures)}",
        f"Raw stake: {raw_total:.3f}u | логическая экспозиция: {logical_total:.3f}u | убрано дублей: {dedup_total:.3f}u",
        f"Canonical conflicts: {len(conflicts)} | WATCH overlaps: {len(watch_overlap_fixtures)}",
        "",
        "## Активные логические экспозиции",
    ]
    if not exposures:
        md.append("- Нет активных canonical экспозиций.")
    else:
        for r in exposures:
            extra = []
            if int(r["raw_rule_rows"]) > 1:
                extra.append(f"совпали правила {r['trigger_rules']}; считаем как 1 позицию")
            if r["fixture_conflict"] == "YES":
                extra.append("КОНФЛИКТ — manual review")
            if int(r["watch_overlap_count"] or 0) > 0:
                extra.append(f"WATCH overlap x{r['watch_overlap_count']}")
            suffix = " | " + "; ".join(extra) if extra else ""
            md.append(
                f"- **{r['home_team']} — {r['away_team']}** | {r['trigger_rules']} | {r['display_selection']} | "
                f"{r['logical_exposure_u']}u | {r['user_odds'] or 'N/A'} @ {r['user_bookmaker'] or 'N/A'}{suffix}"
            )

    md += ["", "## Конфликты"]
    if not conflicts:
        md.append("- Нет разных canonical экспозиций на один и тот же матч.")
    else:
        for c in conflicts:
            md.append(f"- **{c['match']}**: " + "; ".join(c["exposures"]))

    md += [
        "",
        "> R1+R2 на одном матче и одной ставке не превращаются в 2u. WATCH не добавляет экспозицию вообще.",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    META.write_text(json.dumps({
        "run_at_utc": now,
        "status": "OK",
        "active_rule_rows": len(raw),
        "logical_exposures": len(exposures),
        "logical_exposure_u": round(logical_total, 3),
        "deduplicated_overlap_u": round(dedup_total, 3),
        "canonical_conflict_fixtures": len(conflicts),
        "watch_overlap_fixtures": len(watch_overlap_fixtures),
        "api_calls": 0,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"logical_exposures": len(exposures), "logical_u": round(logical_total,3), "conflicts": len(conflicts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
