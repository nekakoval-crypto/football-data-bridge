#!/usr/bin/env python3
"""Stage 77 — low-priority player stats and PBK Player Grade capture.

The capture consumes API-Football ``/fixtures/players`` only through the shared
broker path used by Stage53/Stage71. It is deliberately lower priority than
LIVE/current-round/standings work and stops before protected daily reserve.

Finished fixtures are persisted into a durable backfill queue before any provider
call is attempted. Therefore a fixture deferred by quota protection cannot be
lost merely because the current-round inventory later advances to another round.

The queue is fair across retries: fixtures that have never been attempted are
served first, then previously attempted fixtures are retried oldest-attempt-first.
A provider response with no usable player rows remains PENDING evidence; it is
never mislabeled CAPTURED and cannot permanently starve later fixtures.

Outputs are research/context only. They never mutate canonical probability, EV,
R1/R2/R3 eligibility, stake, settlement or the immutable Forward journal.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
from api_football_broker import ApiFootballBrokerError, make_archive_before_budget_get, get_broker
from player_grade import GRADE_VERSION, grade_aggregate, normalize_api_football_player
from player_snapshot_store import read_snapshot_rows, snapshot_parts_dir, migrate_legacy_monolith

OPS = Path(os.getenv("OPS_DIR", "ops"))
FIXTURES = OPS / "current_round_fixtures.csv"
STATS = OPS / "player_stats_snapshots.csv"
GRADES = OPS / "player_grade_snapshots.csv"
STATS_PARTS = snapshot_parts_dir(STATS)
GRADES_PARTS = snapshot_parts_dir(GRADES)
BACKLOG = OPS / "stage77_player_stats_backlog.csv"
META = OPS / "stage77_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

TERMINAL = {"FINISHED", "FT", "AET", "PEN"}

STAT_FIELDS = [
    "fixture_id", "team_id", "team_name", "kickoff_utc", "observed_at_utc",
    "player_id", "player_name", "position", "minutes", "provider_rating",
    "shots_total", "shots_on", "goals", "assists", "passes_total", "passes_key",
    "passes_accuracy", "tackles_total", "tackles_blocks", "interceptions",
    "duels_total", "duels_won", "dribbles_attempts", "dribbles_success",
    "fouls_drawn", "fouls_committed", "yellow", "red", "penalty_won",
    "penalty_committed", "penalty_scored", "penalty_missed", "source",
]

GRADE_FIELDS = [
    "fixture_id", "team_id", "team_name", "kickoff_utc", "observed_at_utc",
    "player_id", "player_name", "position_group", "minutes", "overall_grade",
    "confidence", "coverage_pct", "provider_rating_reference", "grade_version",
    "components_json", "limitations_json", "source", "research_only",
    "creates_signal", "probability_mutation", "eligibility_mutation", "stake_changes",
]

BACKLOG_FIELDS = [
    "fixture_id", "provider_league_id", "league_name", "season", "round",
    "kickoff_utc", "home_team", "away_team", "source_status",
    "first_queued_at_utc", "last_seen_at_utc", "backlog_status",
    "captured_at_utc", "queue_source", "attempt_count", "last_attempt_at_utc",
    "last_attempt_result",
]


def iso(value=None):
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


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


def row_key(row):
    return (
        str(row.get("fixture_id") or "").strip(),
        str(row.get("team_id") or "").strip(),
        str(row.get("player_id") or "").strip(),
    )


def merge_rows(existing, incoming):
    merged = {row_key(row): dict(row) for row in existing if all(row_key(row))}
    for row in incoming:
        key = row_key(row)
        if all(key):
            merged[key] = dict(row)
    return [merged[key] for key in sorted(merged)]


def completed_fixture_ids(stats_rows, grade_rows):
    """Treat a fixture as captured only when both ledgers contain player rows."""
    stats = {str(row.get("fixture_id") or "") for row in stats_rows if row.get("player_id")}
    grades = {str(row.get("fixture_id") or "") for row in grade_rows if row.get("player_id")}
    return stats & grades


def captured_at_by_fixture(stats_rows, grade_rows):
    completed = completed_fixture_ids(stats_rows, grade_rows)
    observed = {}
    for row in list(stats_rows) + list(grade_rows):
        fixture_id = str(row.get("fixture_id") or "").strip()
        stamp = str(row.get("observed_at_utc") or "").strip()
        if fixture_id not in completed or not stamp:
            continue
        if fixture_id not in observed or stamp < observed[fixture_id]:
            observed[fixture_id] = stamp
    return observed


def terminal_fixture(row, now):
    fixture_id = str(row.get("fixture_id") or "").strip()
    kickoff = parse_utc(row.get("kickoff_utc"))
    raw_status = str(row.get("source_status") or row.get("status") or "").strip().upper()
    normalized = str(row.get("status") or "").strip().upper()
    return bool(
        fixture_id and kickoff and kickoff <= now and
        (raw_status in TERMINAL or normalized == "FINISHED")
    )


def sync_backlog(existing, fixtures, stats_rows, grade_rows, now):
    """Persist every observed terminal fixture until player data is captured.

    The queue is operational state, not a claim that player stats were available at
    FT. A queued fixture remains eligible even after it disappears from the rolling
    current-round inventory. Existing first-queue and attempt provenance are never
    rewritten by ordinary inventory refreshes.
    """
    merged = {
        str(row.get("fixture_id") or "").strip(): {field: row.get(field, "") for field in BACKLOG_FIELDS}
        for row in existing
        if str(row.get("fixture_id") or "").strip()
    }
    now_iso = iso(now)
    new_rows = 0
    terminal_seen = 0
    for fixture in fixtures:
        if not terminal_fixture(fixture, now):
            continue
        terminal_seen += 1
        fixture_id = str(fixture.get("fixture_id") or "").strip()
        old = merged.get(fixture_id)
        if old is None:
            old = {field: "" for field in BACKLOG_FIELDS}
            old["fixture_id"] = fixture_id
            old["first_queued_at_utc"] = now_iso
            old["queue_source"] = "current_round_terminal_fixture"
            old["attempt_count"] = "0"
            new_rows += 1
        for field in (
            "provider_league_id", "league_name", "season", "round",
            "kickoff_utc", "home_team", "away_team", "source_status",
        ):
            value = str(fixture.get(field) or "").strip()
            if value:
                old[field] = value
        old["last_seen_at_utc"] = now_iso
        merged[fixture_id] = old

    captured_at = captured_at_by_fixture(stats_rows, grade_rows)
    for fixture_id, row in merged.items():
        if fixture_id in captured_at:
            row["backlog_status"] = "CAPTURED"
            row["captured_at_utc"] = row.get("captured_at_utc") or captured_at[fixture_id]
        else:
            row["backlog_status"] = "PENDING"
            row["captured_at_utc"] = ""

    rows = [merged[key] for key in sorted(merged, key=lambda fid: (
        parse_utc(merged[fid].get("kickoff_utc")) or now, fid
    ))]
    return {
        "rows": rows,
        "new_rows": new_rows,
        "terminal_seen": terminal_seen,
        "pending": sum(row.get("backlog_status") == "PENDING" for row in rows),
        "captured": sum(row.get("backlog_status") == "CAPTURED" for row in rows),
    }


def attempt_count(row):
    try:
        return max(0, int(str(row.get("attempt_count") or "0").strip()))
    except ValueError:
        return 0


def record_attempts(rows, attempts):
    """Persist provider-attempt evidence without changing capture truth."""
    by_fixture = {
        str(row.get("fixture_id") or "").strip(): dict(row)
        for row in rows
        if str(row.get("fixture_id") or "").strip()
    }
    for attempt in attempts:
        fixture_id = str(attempt.get("fixture_id") or "").strip()
        row = by_fixture.get(fixture_id)
        if row is None:
            continue
        row["attempt_count"] = str(attempt_count(row) + 1)
        row["last_attempt_at_utc"] = str(attempt.get("attempted_at_utc") or "")
        row["last_attempt_result"] = str(attempt.get("result") or "")
    return [by_fixture[str(row.get("fixture_id") or "").strip()] for row in rows]


def retry_cooldown_hours(row):
    """Return bounded cooldown after an unsuccessful provider attempt."""
    result = str(row.get("last_attempt_result") or "").strip().upper()
    attempts = attempt_count(row)
    if attempts <= 0:
        return 0.0
    if result == "NO_DATA":
        base = float(os.getenv("STAGE77_NO_DATA_RETRY_BASE_HOURS", "6"))
        cap = float(os.getenv("STAGE77_NO_DATA_RETRY_MAX_HOURS", "72"))
    elif result == "ERROR":
        base = float(os.getenv("STAGE77_ERROR_RETRY_BASE_HOURS", "1"))
        cap = float(os.getenv("STAGE77_ERROR_RETRY_MAX_HOURS", "12"))
    else:
        return 0.0
    return max(0.0, min(cap, base * (2 ** max(0, attempts - 1))))


def retry_ready(row, now):
    last_attempt = parse_utc(row.get("last_attempt_at_utc"))
    if last_attempt is None:
        return True
    cooldown = retry_cooldown_hours(row)
    return cooldown <= 0 or now >= last_attempt + timedelta(hours=cooldown)


def candidate_fixtures(fixtures, captured, now, limit):
    candidates = []
    for row in fixtures:
        fixture_id = str(row.get("fixture_id") or "").strip()
        kickoff = parse_utc(row.get("kickoff_utc"))
        raw_status = str(row.get("source_status") or row.get("status") or "").strip().upper()
        normalized = str(row.get("status") or "").strip().upper()
        if not fixture_id or fixture_id in captured or not kickoff or kickoff > now:
            continue
        if raw_status not in TERMINAL and normalized != "FINISHED":
            continue
        if not retry_ready(row, now):
            continue
        candidates.append(row)

    def fair_key(row):
        last_attempt = parse_utc(row.get("last_attempt_at_utc"))
        # Never-attempted fixtures always go first. Once every pending fixture has
        # had a chance, retry the least-recently attempted fixture first.
        return (
            0 if last_attempt is None else 1,
            last_attempt or datetime.min.replace(tzinfo=timezone.utc),
            parse_utc(row.get("kickoff_utc")) or now,
            str(row.get("fixture_id") or ""),
        )

    candidates.sort(key=fair_key)
    return candidates[: max(0, int(limit))]


def protected_calls(ops, now):
    live = audit.live_forecast(ops / "current_round_fixtures.csv", now)
    live_calls = int(live.get("reserved_live_calls") or 0)
    round_calls = audit.current_round_forecast(
        now, calls_per_run=int(os.getenv("STAGE77_CURRENT_ROUND_CALLS_PER_RUN", "32"))
    )
    standings_calls = int(os.getenv("STAGE77_STANDINGS_RESERVE_CALLS", "16"))
    safety = int(os.getenv("STAGE77_SAFETY_RESERVE_CALLS", "8"))
    return {
        "live": live_calls,
        "current_round": round_calls,
        "standings": max(0, standings_calls),
        "safety": max(0, safety),
        "total": max(0, live_calls + round_calls + standings_calls + safety),
        "live_forecast_status": live.get("status"),
    }


def normalize_fixture_players(payload, fixture, observed_at):
    fixture_id = str(fixture.get("fixture_id") or "").strip()
    kickoff = str(fixture.get("kickoff_utc") or "").strip()
    stats_rows, grade_rows = [], []
    for team_block in payload.get("response", []) if isinstance(payload, dict) else []:
        if not isinstance(team_block, dict):
            continue
        team = team_block.get("team") or {}
        team_id = str(team.get("id") or "").strip()
        team_name = team.get("name")
        for item in team_block.get("players") or []:
            if not isinstance(item, dict):
                continue
            player = item.get("player") or {}
            statistics = item.get("statistics") or []
            if not isinstance(statistics, list) or not statistics:
                continue
            normalized = normalize_api_football_player(player, statistics[0] or {})
            if not normalized.get("player_id"):
                continue
            normalized.update({
                "fixture_id": fixture_id,
                "team_id": team_id,
                "team_name": team_name,
                "kickoff_utc": kickoff,
                "observed_at_utc": observed_at,
            })
            stats_rows.append(normalized)
            grade = grade_aggregate(normalized)
            grade_rows.append({
                "fixture_id": fixture_id,
                "team_id": team_id,
                "team_name": team_name,
                "kickoff_utc": kickoff,
                "observed_at_utc": observed_at,
                "player_id": normalized.get("player_id"),
                "player_name": normalized.get("player_name"),
                "position_group": grade.get("position_group"),
                "minutes": grade.get("minutes") if grade.get("minutes") is not None else normalized.get("minutes"),
                "overall_grade": grade.get("overall_grade"),
                "confidence": grade.get("confidence"),
                "coverage_pct": grade.get("coverage_pct"),
                "provider_rating_reference": grade.get("provider_rating_reference"),
                "grade_version": grade.get("version") or GRADE_VERSION,
                "components_json": json.dumps(grade.get("components") or {}, ensure_ascii=False, sort_keys=True),
                "limitations_json": json.dumps(grade.get("limitations") or [], ensure_ascii=False),
                "source": grade.get("source") or normalized.get("source"),
                "research_only": "true",
                "creates_signal": "false",
                "probability_mutation": "false",
                "eligibility_mutation": "false",
                "stake_changes": "false",
            })
    return stats_rows, grade_rows


def capture(fixtures, existing_stats, existing_grades, get, now, max_fixtures):
    captured = completed_fixture_ids(existing_stats, existing_grades)
    candidates = candidate_fixtures(fixtures, captured, now, max_fixtures)
    new_stats, new_grades = [], []
    captured_fixture_ids, warnings, attempts = [], [], []
    deferred = 0
    for index, fixture in enumerate(candidates):
        fixture_id = str(fixture.get("fixture_id") or "")
        attempted_at = iso(now)
        try:
            payload = get(
                "/fixtures/players", {"fixture": fixture_id},
                ttl_seconds=7 * 24 * 3600, force_refresh=False,
            )
        except audit.ProtectedBudgetError as exc:
            deferred = len(candidates) - index
            warnings.append(str(exc))
            break
        except (ApiFootballBrokerError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            attempts.append({"fixture_id": fixture_id, "attempted_at_utc": attempted_at, "result": "ERROR"})
            warnings.append(f"{fixture_id}: {exc}")
            continue
        observed = iso(now)
        stats_rows, grade_rows = normalize_fixture_players(payload, fixture, observed)
        if not stats_rows:
            attempts.append({"fixture_id": fixture_id, "attempted_at_utc": attempted_at, "result": "NO_DATA"})
            warnings.append(f"{fixture_id}: provider returned no usable player rows")
            continue
        attempts.append({"fixture_id": fixture_id, "attempted_at_utc": attempted_at, "result": "CAPTURED"})
        new_stats.extend(stats_rows)
        new_grades.extend(grade_rows)
        captured_fixture_ids.append(fixture_id)
    return {
        "stats": merge_rows(existing_stats, new_stats),
        "grades": merge_rows(existing_grades, new_grades),
        "new_stats_rows": len(new_stats),
        "new_grade_rows": len(new_grades),
        "candidate_fixtures": len(candidates),
        "captured_fixture_ids": captured_fixture_ids,
        "captured_fixtures": len(captured_fixture_ids),
        "deferred_fixtures": deferred,
        "attempts": attempts,
        "warnings": warnings,
    }


def main():
    now = datetime.now(timezone.utc)
    fixtures = read_csv(FIXTURES)
    existing_stats = merge_rows([], read_snapshot_rows(STATS, STATS_PARTS))
    existing_grades = merge_rows([], read_snapshot_rows(GRADES, GRADES_PARTS))
    existing_backlog = read_csv(BACKLOG)

    backlog_before = sync_backlog(
        existing_backlog, fixtures, existing_stats, existing_grades, now
    )

    state = audit.read(SHARED_STATE)
    reserve = protected_calls(OPS, now)
    max_calls = int(os.getenv("STAGE77_MAX_API_CALLS", "4"))
    daily_limit = int(os.getenv("STAGE71_MAX_DAILY_API_CALLS", "180"))
    budget = audit.Budget(
        s53.api_get, state, now,
        limit=max_calls,
        daily_limit=daily_limit,
        protected_calls=reserve["total"],
        checkpoint=lambda value: audit.save(SHARED_STATE, value),
    )
    archive_stats = {"archive_read_hits": 0, "archive_read_misses": 0, "archive_read_errors": 0}
    historical_get = make_archive_before_budget_get(budget, archive_stats)
    result = capture(
        backlog_before["rows"], existing_stats, existing_grades, historical_get, now,
        int(os.getenv("STAGE77_MAX_FIXTURES_PER_RUN", str(max_calls))),
    )

    attempted_backlog = record_attempts(backlog_before["rows"], result["attempts"])
    backlog_after = sync_backlog(
        attempted_backlog, [], result["stats"], result["grades"], now
    )

    stats_store = migrate_legacy_monolith(
        STATS, STATS_PARTS, STAT_FIELDS, result["stats"]
    )
    grades_store = migrate_legacy_monolith(
        GRADES, GRADES_PARTS, GRADE_FIELDS, result["grades"]
    )
    if backlog_after["rows"] or BACKLOG.exists():
        write_csv_atomic(BACKLOG, BACKLOG_FIELDS, backlog_after["rows"])
    audit.save(SHARED_STATE, state)
    broker_stats = get_broker().stats()
    if int(broker_stats.get("archive_errors") or 0) > 0:
        result["warnings"].append(f"raw archive write failures: {broker_stats.get('archive_errors')}")
    no_data_attempts = sum(item.get("result") == "NO_DATA" for item in result["attempts"])
    error_attempts = sum(item.get("result") == "ERROR" for item in result["attempts"])
    meta = {
        "version": "PBK_STAGE77_PLAYER_STATS_CAPTURE_V3_FAIR_BACKLOG",
        "run_at_utc": iso(now),
        "status": "ATTENTION" if result["warnings"] else ("WAITING" if result["deferred_fixtures"] else "OK"),
        "provider_endpoint": "/fixtures/players",
        "provider_calls": budget.calls,
        "provider_successes": broker_stats.get("provider_successes"),
        "archive_write_successes": broker_stats.get("archive_write_successes"),
        "archive_write_failures": broker_stats.get("archive_errors"),
        "provider_archive_write_through_ok": broker_stats.get("provider_successes") == (broker_stats.get("archive_write_successes") or 0) + (broker_stats.get("archive_errors") or 0),
        "archive_first_enabled": True,
        "archive_read_hits": archive_stats["archive_read_hits"],
        "archive_read_misses": archive_stats["archive_read_misses"],
        "archive_read_errors": archive_stats["archive_read_errors"],
        "daily_api_calls": state.get("api_day_calls", 0),
        "protected_calls": reserve,
        "candidate_fixtures": result["candidate_fixtures"],
        "captured_fixtures": result["captured_fixtures"],
        "captured_fixture_ids": result["captured_fixture_ids"],
        "deferred_fixtures": result["deferred_fixtures"],
        "attempted_fixtures": len(result["attempts"]),
        "no_data_attempts": no_data_attempts,
        "error_attempts": error_attempts,
        "backlog_terminal_seen_this_run": backlog_before["terminal_seen"],
        "backlog_new_this_run": backlog_before["new_rows"],
        "backlog_rows": len(backlog_after["rows"]),
        "backlog_pending": backlog_after["pending"],
        "backlog_captured": backlog_after["captured"],
        "backlog_persists_across_round_rotation": True,
        "fair_retry_order": True,
        "new_stats_rows": result["new_stats_rows"],
        "new_grade_rows": result["new_grade_rows"],
        "total_stats_rows": len(result["stats"]),
        "total_grade_rows": len(result["grades"]),
        "snapshot_store": "YEAR_PARTITIONED_V1",
        "stats_partitions": stats_store["partitions"],
        "grade_partitions": grades_store["partitions"],
        "warnings": result["warnings"],
        "research_only": True,
        "no_lookahead_consumption": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
