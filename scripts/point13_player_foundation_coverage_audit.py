#!/usr/bin/env python3
"""PBK Point 13 — provider-free player foundation coverage audit.

Measures historical player-stat, Player Grade, walk-forward form, and xG/xA
identity coverage using only persisted PBK artifacts. No provider/network calls.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
HISTORY = OPS / "pbk16_all_competition_fixture_history.csv"
STATS = OPS / "player_stats_snapshots.csv"
GRADES = OPS / "player_grade_snapshots.csv"
FORM = OPS / "player_form_walk_forward.csv"
PLAYERS = OPS / "historical_players.csv"
XGXA = OPS / "pbk_player_xg_xa_research.csv"
MAPPING = OPS / "statsbomb_pbk_player_mapping_candidates.csv"
STAGE77_META = OPS / "stage77_historical_player_backfill_last_run.json"
STAGE78_META = OPS / "stage78_player_form_walk_forward_last_run.json"
STAGE92_META = OPS / "stage92_statsbomb_pbk_player_mapping_last_run.json"
OUT = OPS / "point13_player_foundation_coverage_audit.json"
VERSION = "PBK_POINT13_PLAYER_FOUNDATION_COVERAGE_AUDIT_V1"
TERMINAL = {"FT", "AET", "PEN", "FINISHED"}


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_json(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def pct(num, den):
    return round(100.0 * num / den, 4) if den else 0.0


def fixture_ids_with_players(rows):
    return {
        sval(row, "fixture_id")
        for row in rows
        if sval(row, "fixture_id") and sval(row, "player_id")
    }


def terminal_history(rows):
    out = {}
    for row in rows:
        fixture_id = sval(row, "fixture_id")
        status = sval(row, "status").upper()
        if fixture_id and status in TERMINAL:
            out.setdefault(fixture_id, row)
    return out


def mapping_status(row):
    return sval(row, "match_status").upper() or "UNKNOWN"


def summarize(history_rows, stats_rows, grade_rows, form_rows, player_rows, xgxa_rows, mapping_rows):
    history = terminal_history(history_rows)
    stats_fixtures = fixture_ids_with_players(stats_rows)
    grade_fixtures = fixture_ids_with_players(grade_rows)
    normalized_fixtures = stats_fixtures & grade_fixtures

    catalog_players = {sval(r, "player_id") for r in player_rows if sval(r, "player_id")}
    match_stat_players = {
        sval(r, "player_id")
        for r in player_rows
        if sval(r, "player_id") and sval(r, "has_match_stats_evidence").upper() == "YES"
    }

    form3 = sum(int(float(sval(r, "sample_3") or 0)) >= 3 for r in form_rows)
    form5 = sum(int(float(sval(r, "sample_5") or 0)) >= 5 for r in form_rows)
    form10 = sum(int(float(sval(r, "sample_10") or 0)) >= 10 for r in form_rows)

    mapped_xg_players = {sval(r, "pbk_player_id") for r in xgxa_rows if sval(r, "pbk_player_id")}
    mapping_counts = defaultdict(int)
    for row in mapping_rows:
        mapping_counts[mapping_status(row)] += 1

    by_country_season = defaultdict(lambda: {"terminal_fixtures": set(), "normalized_player_fixtures": set()})
    by_competition_season = defaultdict(lambda: {"terminal_fixtures": set(), "normalized_player_fixtures": set()})

    for fixture_id, row in history.items():
        country = sval(row, "country") or "UNKNOWN"
        season = sval(row, "season") or "UNKNOWN"
        competition = sval(row, "competition_name") or "UNKNOWN"
        by_country_season[(country, season)]["terminal_fixtures"].add(fixture_id)
        by_competition_season[(country, competition, season)]["terminal_fixtures"].add(fixture_id)
        if fixture_id in normalized_fixtures:
            by_country_season[(country, season)]["normalized_player_fixtures"].add(fixture_id)
            by_competition_season[(country, competition, season)]["normalized_player_fixtures"].add(fixture_id)

    def rollup(mapping):
        out = {}
        for key, bucket in sorted(mapping.items()):
            total = len(bucket["terminal_fixtures"])
            covered = len(bucket["normalized_player_fixtures"])
            out["|".join(key)] = {
                "terminal_fixtures": total,
                "normalized_player_fixtures": covered,
                "fixture_coverage_pct": pct(covered, total),
            }
        return out

    total_terminal = len(history)
    total_normalized = len(normalized_fixtures)
    total_form = len(form_rows)

    return {
        "historical_fixture_coverage": {
            "terminal_historical_fixtures": total_terminal,
            "stats_fixtures": len(stats_fixtures),
            "grade_fixtures": len(grade_fixtures),
            "normalized_player_fixtures": total_normalized,
            "fixture_coverage_pct": pct(total_normalized, total_terminal),
        },
        "player_catalog_coverage": {
            "catalog_players": len(catalog_players),
            "players_with_match_stats_evidence": len(match_stat_players),
            "match_stats_player_coverage_pct": pct(len(match_stat_players), len(catalog_players)),
        },
        "form_coverage": {
            "form_rows": total_form,
            "form3_full_window_rows": form3,
            "form5_full_window_rows": form5,
            "form10_full_window_rows": form10,
            "form3_full_window_pct": pct(form3, total_form),
            "form5_full_window_pct": pct(form5, total_form),
            "form10_full_window_pct": pct(form10, total_form),
        },
        "xg_xa_coverage": {
            "mapped_research_rows": len(xgxa_rows),
            "mapped_pbk_players": len(mapped_xg_players),
            "mapping_rows": len(mapping_rows),
            "auto_match_high": mapping_counts.get("AUTO_MATCH", 0),
            "review": mapping_counts.get("REVIEW", 0),
            "unmatched": mapping_counts.get("UNMATCHED", 0),
            "mapped_vs_catalog_player_pct": pct(len(mapped_xg_players), len(catalog_players)),
        },
        "by_country_season": rollup(by_country_season),
        "by_competition_season": rollup(by_competition_season),
    }


def main():
    coverage = summarize(
        read_csv(HISTORY),
        read_csv(STATS),
        read_csv(GRADES),
        read_csv(FORM),
        read_csv(PLAYERS),
        read_csv(XGXA),
        read_csv(MAPPING),
    )
    stage77 = read_json(STAGE77_META)
    stage78 = read_json(STAGE78_META)
    stage92 = read_json(STAGE92_META)

    report = {
        "version": VERSION,
        "run_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "OK",
        "provider_calls": 0,
        "research_only": True,
        "operational_betting_authority": False,
        "no_lookahead_form_contract": stage78.get("no_lookahead"),
        "stage77_remaining_unattempted_or_retryable": stage77.get("remaining_unattempted_or_retryable"),
        "stage77_archive_first_enabled": stage77.get("archive_first_enabled"),
        "stage92_auto_match_high": stage92.get("auto_match_high"),
        **coverage,
    }

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
