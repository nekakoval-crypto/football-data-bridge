#!/usr/bin/env python3
"""Stage 78 — provider-free Player Grade coverage, XI quality and importance research.

Consumes only already-captured operational files. It never calls API-Football and
never changes canonical probability, EV, R1/R2/R3 eligibility, stake, settlement
or the immutable Forward journal.
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
try:
    from player_snapshot_store import read_snapshot_rows
except ImportError:
    from scripts.player_snapshot_store import read_snapshot_rows

OPS = Path(os.getenv("OPS_DIR", "ops"))
GRADES = OPS / "player_grade_snapshots.csv"
STATS = OPS / "player_stats_snapshots.csv"
ROTATION = OPS / "rotation_snapshots.csv"
FIXTURES = OPS / "current_round_fixtures.csv"
COVERAGE = OPS / "player_grade_coverage.json"
XI_HISTORY = OPS / "xi_quality_history.csv"
IMPORTANCE = OPS / "player_importance_research.csv"
META = OPS / "stage78_last_run.json"
VERSION = "PBK_STAGE78_PLAYER_RESEARCH_V1"

XI_FIELDS = [
    "fixture_id", "captured_at_utc", "kickoff_utc", "side", "team_id", "team_name",
    "formation", "lineup_status", "xi_quality", "previous_xi_quality",
    "delta_vs_previous_xi", "covered_players", "xi_players", "coverage_pct",
    "grade_confidence", "grade_version", "grade_basis", "low_minute_rows_excluded",
    "source", "no_lookahead", "research_only", "creates_signal",
    "probability_mutation", "eligibility_mutation", "stake_changes",
]

IMPORTANCE_FIELDS = [
    "team_id", "team_name", "player_id", "player_name", "position_group",
    "eligible", "status", "starts", "without_starts", "points_with",
    "points_without", "goal_diff_with", "goal_diff_without", "points_delta",
    "goal_diff_delta", "shrinkage_weight", "importance_score", "sample_reason",
    "research_only", "creates_signal", "probability_mutation",
    "eligibility_mutation", "stake_changes",
]


def now_iso(value=None):
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv_atomic(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def write_json_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def _num(value, default=None):
    try:
        return float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _json_list(value):
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _player_id(player):
    return str((player or {}).get("id") or (player or {}).get("player_id") or "").strip()


def _confidence(covered, total=11):
    ratio = covered / max(total, 1)
    if ratio >= .82:
        return "HIGH"
    if ratio >= .55:
        return "MEDIUM"
    if covered:
        return "LOW"
    return "UNKNOWN"


def coverage_report(grade_rows, stat_rows):
    """Deterministic data-quality report for Stage77 output."""
    grade_keys = [(r.get("fixture_id"), r.get("team_id"), r.get("player_id")) for r in grade_rows]
    stat_keys = [(r.get("fixture_id"), r.get("team_id"), r.get("player_id")) for r in stat_rows]
    duplicates_grade = sum(n - 1 for n in Counter(grade_keys).values() if n > 1)
    duplicates_stats = sum(n - 1 for n in Counter(stat_keys).values() if n > 1)
    grade_key_set = {k for k in grade_keys if all(k)}
    stat_key_set = {k for k in stat_keys if all(k)}
    positions = Counter(str(r.get("position_group") or "UNKNOWN") for r in grade_rows)
    confidences = Counter(str(r.get("confidence") or "UNKNOWN") for r in grade_rows)
    low_minute = sum((_num(r.get("minutes"), 0) or 0) < 30 for r in grade_rows)
    missing_grade = sum(_num(r.get("overall_grade")) is None for r in grade_rows)
    fixtures = {str(r.get("fixture_id") or "") for r in grade_rows if r.get("fixture_id")}
    teams = {(str(r.get("fixture_id") or ""), str(r.get("team_id") or "")) for r in grade_rows if r.get("fixture_id") and r.get("team_id")}
    team_counts = Counter((str(r.get("fixture_id") or ""), str(r.get("team_id") or "")) for r in grade_rows)
    complete_team_xi = sum(count >= 11 for count in team_counts.values())
    status = "WAITING" if not grade_rows else ("ATTENTION" if duplicates_grade or duplicates_stats or missing_grade else "OK")
    return {
        "version": VERSION,
        "status": status,
        "grade_rows": len(grade_rows),
        "stat_rows": len(stat_rows),
        "fixtures_with_grades": len(fixtures),
        "fixture_team_pairs": len(teams),
        "fixture_team_pairs_with_11plus_rows": complete_team_xi,
        "grade_stat_key_overlap": len(grade_key_set & stat_key_set),
        "grade_only_keys": len(grade_key_set - stat_key_set),
        "stats_only_keys": len(stat_key_set - grade_key_set),
        "duplicate_grade_rows": duplicates_grade,
        "duplicate_stat_rows": duplicates_stats,
        "missing_overall_grade_rows": missing_grade,
        "low_minute_rows_lt30": low_minute,
        "low_minute_share_pct": round(100 * low_minute / max(len(grade_rows), 1), 1),
        "position_groups": dict(sorted(positions.items())),
        "confidence": dict(sorted(confidences.items())),
        "limitations": [] if grade_rows else ["PLAYER_GRADE_SNAPSHOTS_NOT_CAPTURED_YET"],
        "research_only": True,
        "provider_polling": False,
    }


def _grade_asof(player_id, grade_rows, kickoff_utc, captured_at_utc, min_minutes=30, form_size=5):
    """Return a pre-match player grade using only evidence actually known by capture time."""
    eligible = []
    low_excluded = 0
    for row in grade_rows:
        if str(row.get("player_id") or "") != str(player_id):
            continue
        match_kickoff = str(row.get("kickoff_utc") or "")
        observed = str(row.get("observed_at_utc") or "")
        if not match_kickoff or match_kickoff >= str(kickoff_utc):
            continue
        if observed and observed > str(captured_at_utc):
            continue
        value = _num(row.get("overall_grade"))
        if value is None:
            continue
        minutes = _num(row.get("minutes"), 0) or 0
        if minutes < min_minutes:
            low_excluded += 1
            continue
        eligible.append((match_kickoff, value, row))
    eligible.sort(key=lambda item: item[0], reverse=True)
    sample = eligible[:form_size]
    if not sample:
        return None, 0, low_excluded, None, None
    value = round(mean(item[1] for item in sample), 2)
    version = next((item[2].get("grade_version") for item in sample if item[2].get("grade_version")), None)
    source = next((item[2].get("source") for item in sample if item[2].get("source")), None)
    return value, len(sample), low_excluded, version, source


def _xi_quality(xi, grade_rows, kickoff, captured):
    values = []
    missing = []
    low_excluded = 0
    versions = Counter()
    sources = Counter()
    samples = []
    for player in xi:
        pid = _player_id(player)
        if not pid:
            continue
        value, sample, low, version, source = _grade_asof(pid, grade_rows, kickoff, captured)
        low_excluded += low
        if value is None:
            missing.append(pid)
            continue
        values.append(value)
        samples.append(sample)
        if version:
            versions[version] += 1
        if source:
            sources[source] += 1
    return {
        "quality": round(mean(values), 2) if values else None,
        "covered": len(values),
        "missing": missing,
        "coverage_pct": round(100 * len(values) / max(len(xi), 1), 1),
        "confidence": _confidence(len(values), len(xi)),
        "grade_version": versions.most_common(1)[0][0] if versions else None,
        "source": sources.most_common(1)[0][0] if sources else None,
        "basis": "FORM_5_MIN30" if values else None,
        "low_excluded": low_excluded,
        "mean_history_sample": round(mean(samples), 2) if samples else 0,
    }


def build_xi_quality_history(rotation_rows, grade_rows):
    output = []
    seen = set()
    for row in rotation_rows:
        fixture_id = str(row.get("api_fixture_id") or "").strip()
        captured = str(row.get("captured_at_utc") or "").strip()
        kickoff = str(row.get("kickoff_utc") or "").strip()
        if not fixture_id or not captured or not kickoff:
            continue
        for side in ("home", "away"):
            current = _json_list(row.get(f"{side}_current_xi_json"))
            previous = _json_list(row.get(f"{side}_prev_xi_json"))
            if len(current) != 11:
                continue
            key = (fixture_id, side, captured)
            if key in seen:
                continue
            seen.add(key)
            current_q = _xi_quality(current, grade_rows, kickoff, captured)
            previous_q = _xi_quality(previous, grade_rows, kickoff, captured) if len(previous) == 11 else None
            delta = None
            if current_q["quality"] is not None and previous_q and previous_q["quality"] is not None:
                delta = round(current_q["quality"] - previous_q["quality"], 2)
            output.append({
                "fixture_id": fixture_id,
                "captured_at_utc": captured,
                "kickoff_utc": kickoff,
                "side": side,
                "team_id": str(row.get(f"{side}_team_id") or ""),
                "team_name": row.get(f"{side}_team"),
                "formation": row.get(f"{side}_current_formation"),
                "lineup_status": "OFFICIAL_OR_PROVIDER_CURRENT" if str(row.get("current_lineups_available") or "").upper() == "YES" else "UNKNOWN",
                "xi_quality": current_q["quality"],
                "previous_xi_quality": previous_q["quality"] if previous_q else None,
                "delta_vs_previous_xi": delta,
                "covered_players": current_q["covered"],
                "xi_players": len(current),
                "coverage_pct": current_q["coverage_pct"],
                "grade_confidence": current_q["confidence"],
                "grade_version": current_q["grade_version"],
                "grade_basis": current_q["basis"],
                "low_minute_rows_excluded": current_q["low_excluded"],
                "source": current_q["source"],
                "no_lookahead": "true",
                "research_only": "true",
                "creates_signal": "false",
                "probability_mutation": "false",
                "eligibility_mutation": "false",
                "stake_changes": "false",
            })
    return sorted(output, key=lambda r: (r["kickoff_utc"], r["fixture_id"], r["side"], r["captured_at_utc"]))


def _result_index(fixture_rows):
    out = {}
    for row in fixture_rows:
        fixture_id = str(row.get("fixture_id") or "").strip()
        home = str(row.get("home_team") or "")
        away = str(row.get("away_team") or "")
        hg = _num(row.get("score_home"))
        ag = _num(row.get("score_away"))
        status = str(row.get("status") or "").lower()
        if not fixture_id or hg is None or ag is None or status not in {"finished", "ft", "settled"}:
            continue
        hp = 3 if hg > ag else (1 if hg == ag else 0)
        ap = 3 if ag > hg else (1 if hg == ag else 0)
        out[fixture_id] = {
            "home_team": home, "away_team": away,
            "home_points": hp, "away_points": ap,
            "home_gd": hg - ag, "away_gd": ag - hg,
        }
    return out


def build_player_importance(rotation_rows, fixture_rows, min_with=5, min_without=5):
    """Descriptive starts-vs-no-starts foundation with hard small-sample guard."""
    results = _result_index(fixture_rows)
    team_matches = defaultdict(dict)
    player_names = {}
    player_positions = {}
    for row in rotation_rows:
        fixture_id = str(row.get("api_fixture_id") or "")
        result = results.get(fixture_id)
        if not result:
            continue
        for side in ("home", "away"):
            team_id = str(row.get(f"{side}_team_id") or "")
            team_name = str(row.get(f"{side}_team") or "")
            xi = _json_list(row.get(f"{side}_current_xi_json"))
            if not team_id or len(xi) != 11:
                continue
            points = result.get(f"{side}_points")
            gd = result.get(f"{side}_gd")
            team_matches[team_id][fixture_id] = {"team_name": team_name, "points": points, "gd": gd, "starters": {_player_id(p) for p in xi if _player_id(p)}}
            for p in xi:
                pid = _player_id(p)
                if pid:
                    player_names[(team_id, pid)] = p.get("name")
                    player_positions[(team_id, pid)] = p.get("pos") or p.get("position")
    output = []
    for team_id, matches in sorted(team_matches.items()):
        all_players = sorted({pid for match in matches.values() for pid in match["starters"]})
        for pid in all_players:
            with_rows = [m for m in matches.values() if pid in m["starters"]]
            without_rows = [m for m in matches.values() if pid not in m["starters"]]
            eligible = len(with_rows) >= min_with and len(without_rows) >= min_without
            p_with = mean(m["points"] for m in with_rows) if with_rows else None
            p_without = mean(m["points"] for m in without_rows) if without_rows else None
            gd_with = mean(m["gd"] for m in with_rows) if with_rows else None
            gd_without = mean(m["gd"] for m in without_rows) if without_rows else None
            points_delta = round(p_with - p_without, 3) if eligible else None
            gd_delta = round(gd_with - gd_without, 3) if eligible else None
            # Conservative shrinkage: full weight only after ~20 observations in each group.
            shrinkage = min(1.0, min(len(with_rows), len(without_rows)) / 20.0) if eligible else 0.0
            score = round((points_delta * .7 + gd_delta * .3) * shrinkage, 3) if eligible else None
            reason = "OK" if eligible else f"INSUFFICIENT_SAMPLE_WITH_{len(with_rows)}_WITHOUT_{len(without_rows)}"
            output.append({
                "team_id": team_id,
                "team_name": next(iter(matches.values()))["team_name"],
                "player_id": pid,
                "player_name": player_names.get((team_id, pid)),
                "position_group": player_positions.get((team_id, pid)),
                "eligible": "true" if eligible else "false",
                "status": "RESEARCH_ESTIMATE" if eligible else "UNKNOWN",
                "starts": len(with_rows),
                "without_starts": len(without_rows),
                "points_with": round(p_with, 3) if p_with is not None else None,
                "points_without": round(p_without, 3) if p_without is not None else None,
                "goal_diff_with": round(gd_with, 3) if gd_with is not None else None,
                "goal_diff_without": round(gd_without, 3) if gd_without is not None else None,
                "points_delta": points_delta,
                "goal_diff_delta": gd_delta,
                "shrinkage_weight": round(shrinkage, 3),
                "importance_score": score,
                "sample_reason": reason,
                "research_only": "true",
                "creates_signal": "false",
                "probability_mutation": "false",
                "eligibility_mutation": "false",
                "stake_changes": "false",
            })
    return output


def main():
    grades = read_snapshot_rows(GRADES)
    stats = read_snapshot_rows(STATS)
    rotations = read_csv(ROTATION)
    fixtures = read_csv(FIXTURES)
    coverage = coverage_report(grades, stats)
    xi_rows = build_xi_quality_history(rotations, grades)
    importance_rows = build_player_importance(
        rotations, fixtures,
        min_with=int(os.getenv("STAGE78_IMPORTANCE_MIN_WITH", "5")),
        min_without=int(os.getenv("STAGE78_IMPORTANCE_MIN_WITHOUT", "5")),
    )
    write_json_atomic(COVERAGE, {**coverage, "generated_at_utc": now_iso()})
    write_csv_atomic(XI_HISTORY, XI_FIELDS, xi_rows)
    write_csv_atomic(IMPORTANCE, IMPORTANCE_FIELDS, importance_rows)
    meta = {
        "version": VERSION,
        "run_at_utc": now_iso(),
        "status": "WAITING" if not grades else ("ATTENTION" if coverage["status"] == "ATTENTION" else "OK"),
        "provider_calls": 0,
        "grade_rows": len(grades),
        "xi_quality_rows": len(xi_rows),
        "importance_rows": len(importance_rows),
        "importance_eligible_rows": sum(r.get("eligible") == "true" for r in importance_rows),
        "coverage_status": coverage["status"],
        "research_only": True,
        "no_lookahead": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "limitations": ["PLAYER_IMPORTANCE_IS_DESCRIPTIVE_STARTS_VS_NO_STARTS_WITH_SHRINKAGE", "NO_CAUSAL_CLAIM"],
    }
    write_json_atomic(META, meta)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
