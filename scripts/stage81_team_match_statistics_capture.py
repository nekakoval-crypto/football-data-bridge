#!/usr/bin/env python3
"""Stage81 — low-priority finished-fixture team statistics capture.

Collects API-Football /fixtures/statistics through the shared PBK broker/budget.

Research/archive layer only:
- durable backlog survives current-round rotation
- protected API reserve is respected
- incomplete provider payload stays retryable
- team-stat rows are deduplicated by fixture + team
- no betting/model/forward-journal authority is changed
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
from api_football_broker import ApiFootballBrokerError

OPS = Path(os.getenv("OPS_DIR", "ops"))

FIXTURES = OPS / "current_round_fixtures.csv"
LEDGER = OPS / "team_match_statistics.csv"
BACKLOG = OPS / "stage81_team_stats_backlog.csv"
META = OPS / "stage81_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

TERMINAL = {"FINISHED", "FT", "AET", "PEN"}

LEDGER_FIELDS = [
    "fixture_id",
    "provider_league_id",
    "league_name",
    "season",
    "round",
    "kickoff_utc",
    "observed_at_utc",
    "team_id",
    "team_name",
    "side",
    "opponent_name",
    "shots_total",
    "shots_on_goal",
    "shots_off_goal",
    "shots_insidebox",
    "shots_outsidebox",
    "blocked_shots",
    "possession_pct",
    "corners",
    "offsides",
    "fouls",
    "yellow_cards",
    "red_cards",
    "goalkeeper_saves",
    "passes_total",
    "passes_accurate",
    "passes_accuracy_pct",
    "expected_goals",
    "source",
    "research_only",
    "creates_signal",
    "probability_mutation",
    "eligibility_mutation",
    "stake_changes",
    "forward_journal_mutation",
]

BACKLOG_FIELDS = [
    "fixture_id",
    "provider_league_id",
    "league_name",
    "season",
    "round",
    "kickoff_utc",
    "home_team",
    "away_team",
    "source_status",
    "first_queued_at_utc",
    "last_seen_at_utc",
    "backlog_status",
    "captured_at_utc",
    "queue_source",
    "attempt_count",
    "last_attempt_at_utc",
    "last_attempt_result",
]


def iso(value=None):
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


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
        writer = csv.DictWriter(
            stream, fieldnames=fields, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def terminal_fixture(row, now):
    fixture_id = str(row.get("fixture_id") or "").strip()
    kickoff = parse_utc(row.get("kickoff_utc"))
    raw = str(
        row.get("source_status") or row.get("status") or ""
    ).strip().upper()
    normalized = str(row.get("status") or "").strip().upper()

    return bool(
        fixture_id
        and kickoff
        and kickoff <= now
        and (raw in TERMINAL or normalized == "FINISHED")
    )


def row_key(row):
    return (
        str(row.get("fixture_id") or "").strip(),
        str(row.get("team_id") or "").strip(),
    )


def merge_rows(existing, incoming):
    merged = {
        row_key(row): dict(row)
        for row in existing
        if all(row_key(row))
    }
    for row in incoming:
        key = row_key(row)
        if all(key) and key not in merged:
            merged[key] = dict(row)

    return [
        merged[key]
        for key in sorted(merged)
    ]


def completed_fixture_ids(rows):
    sides = {}
    for row in rows:
        fixture_id = str(row.get("fixture_id") or "").strip()
        side = str(row.get("side") or "").strip().upper()
        team_id = str(row.get("team_id") or "").strip()
        if not fixture_id or not team_id:
            continue
        sides.setdefault(fixture_id, set()).add(side)

    return {
        fixture_id
        for fixture_id, observed_sides in sides.items()
        if {"HOME", "AWAY"}.issubset(observed_sides)
    }


def captured_at_by_fixture(rows):
    completed = completed_fixture_ids(rows)
    result = {}
    for row in rows:
        fixture_id = str(row.get("fixture_id") or "").strip()
        observed = str(row.get("observed_at_utc") or "").strip()
        if fixture_id not in completed or not observed:
            continue
        if fixture_id not in result or observed < result[fixture_id]:
            result[fixture_id] = observed
    return result


def sync_backlog(existing, fixtures, ledger_rows, now):
    merged = {
        str(row.get("fixture_id") or "").strip(): {
            field: row.get(field, "")
            for field in BACKLOG_FIELDS
        }
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
            "provider_league_id",
            "league_name",
            "season",
            "round",
            "kickoff_utc",
            "home_team",
            "away_team",
            "source_status",
        ):
            value = str(fixture.get(field) or "").strip()
            if value:
                old[field] = value

        old["last_seen_at_utc"] = now_iso
        merged[fixture_id] = old

    captured = captured_at_by_fixture(ledger_rows)

    for fixture_id, row in merged.items():
        if fixture_id in captured:
            row["backlog_status"] = "CAPTURED"
            row["captured_at_utc"] = (
                row.get("captured_at_utc") or captured[fixture_id]
            )
        else:
            row["backlog_status"] = "PENDING"
            row["captured_at_utc"] = ""

    rows = [
        merged[key]
        for key in sorted(
            merged,
            key=lambda fid: (
                parse_utc(merged[fid].get("kickoff_utc")) or now,
                fid,
            ),
        )
    ]

    return {
        "rows": rows,
        "new_rows": new_rows,
        "terminal_seen": terminal_seen,
        "pending": sum(
            row.get("backlog_status") == "PENDING" for row in rows
        ),
        "captured": sum(
            row.get("backlog_status") == "CAPTURED" for row in rows
        ),
    }


def attempt_count(row):
    try:
        return max(
            0, int(str(row.get("attempt_count") or "0").strip())
        )
    except ValueError:
        return 0


def record_attempts(rows, attempts):
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
        row["last_attempt_at_utc"] = str(
            attempt.get("attempted_at_utc") or ""
        )
        row["last_attempt_result"] = str(
            attempt.get("result") or ""
        )

    return [
        by_fixture[str(row.get("fixture_id") or "").strip()]
        for row in rows
    ]


def retry_cooldown_hours(row):
    """Return bounded cooldown after an unsuccessful provider attempt."""
    result = str(row.get("last_attempt_result") or "").strip().upper()
    attempts = attempt_count(row)
    if attempts <= 0:
        return 0.0
    if result == "NO_DATA":
        base = float(os.getenv("STAGE81_NO_DATA_RETRY_BASE_HOURS", "6"))
        cap = float(os.getenv("STAGE81_NO_DATA_RETRY_MAX_HOURS", "72"))
    elif result == "ERROR":
        base = float(os.getenv("STAGE81_ERROR_RETRY_BASE_HOURS", "1"))
        cap = float(os.getenv("STAGE81_ERROR_RETRY_MAX_HOURS", "12"))
    else:
        return 0.0
    return max(0.0, min(cap, base * (2 ** max(0, attempts - 1))))


def retry_ready(row, now):
    last_attempt = parse_utc(row.get("last_attempt_at_utc"))
    if last_attempt is None:
        return True
    cooldown = retry_cooldown_hours(row)
    return cooldown <= 0 or now >= last_attempt + timedelta(hours=cooldown)


def candidate_fixtures(rows, captured, now, limit):
    candidates = []

    for row in rows:
        fixture_id = str(row.get("fixture_id") or "").strip()
        kickoff = parse_utc(row.get("kickoff_utc"))

        if (
            not fixture_id
            or fixture_id in captured
            or not kickoff
            or kickoff > now
        ):
            continue

        if str(row.get("backlog_status") or "").upper() != "PENDING":
            continue

        if not retry_ready(row, now):
            continue

        candidates.append(row)

    def fair_key(row):
        last_attempt = parse_utc(row.get("last_attempt_at_utc"))
        return (
            0 if last_attempt is None else 1,
            last_attempt
            or datetime.min.replace(tzinfo=timezone.utc),
            parse_utc(row.get("kickoff_utc")) or now,
            str(row.get("fixture_id") or ""),
        )

    candidates.sort(key=fair_key)
    return candidates[: max(0, int(limit))]


def protected_calls(ops, now):
    live = audit.live_forecast(
        Path(ops) / "current_round_fixtures.csv", now
    )
    live_calls = int(live.get("reserved_live_calls") or 0)

    round_calls = audit.current_round_forecast(
        now,
        calls_per_run=int(
            os.getenv(
                "STAGE81_CURRENT_ROUND_CALLS_PER_RUN", "32"
            )
        ),
    )

    standings = int(
        os.getenv("STAGE81_STANDINGS_RESERVE_CALLS", "16")
    )
    stage77 = int(
        os.getenv("STAGE81_PLAYER_STATS_RESERVE_CALLS", "4")
    )
    safety = int(
        os.getenv("STAGE81_SAFETY_RESERVE_CALLS", "8")
    )

    total = (
        live_calls
        + round_calls
        + max(0, standings)
        + max(0, stage77)
        + max(0, safety)
    )

    return {
        "live": live_calls,
        "current_round": round_calls,
        "standings": max(0, standings),
        "player_stats_stage77": max(0, stage77),
        "safety": max(0, safety),
        "total": max(0, total),
        "live_forecast_status": live.get("status"),
    }


STAT_MAP = {
    "Shots on Goal": "shots_on_goal",
    "Shots off Goal": "shots_off_goal",
    "Total Shots": "shots_total",
    "Blocked Shots": "blocked_shots",
    "Shots insidebox": "shots_insidebox",
    "Shots outsidebox": "shots_outsidebox",
    "Fouls": "fouls",
    "Corner Kicks": "corners",
    "Offsides": "offsides",
    "Ball Possession": "possession_pct",
    "Yellow Cards": "yellow_cards",
    "Red Cards": "red_cards",
    "Goalkeeper Saves": "goalkeeper_saves",
    "Total passes": "passes_total",
    "Passes accurate": "passes_accurate",
    "Passes %": "passes_accuracy_pct",
    "expected_goals": "expected_goals",
}


def clean_number(value):
    if value is None or value == "":
        return None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if value.endswith("%"):
            value = value[:-1].strip()

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return int(number) if number.is_integer() else number


def normalized_name(value):
    return " ".join(
        str(value or "").casefold().split()
    )


def normalize_team_statistics(payload, fixture, observed_at):
    response = (
        payload.get("response", [])
        if isinstance(payload, dict)
        else []
    )

    home_name = str(fixture.get("home_team") or "").strip()
    away_name = str(fixture.get("away_team") or "").strip()

    home_key = normalized_name(home_name)
    away_key = normalized_name(away_name)

    rows = []

    for block in response:
        if not isinstance(block, dict):
            continue

        team = block.get("team") or {}
        team_id = str(team.get("id") or "").strip()
        team_name = str(team.get("name") or "").strip()

        if not team_id or not team_name:
            continue

        key = normalized_name(team_name)

        if key == home_key and home_key:
            side = "HOME"
            opponent = away_name
        elif key == away_key and away_key:
            side = "AWAY"
            opponent = home_name
        else:
            # Venue must come from explicit fixture evidence.
            continue

        row = {
            field: ""
            for field in LEDGER_FIELDS
        }

        row.update(
            {
                "fixture_id": str(
                    fixture.get("fixture_id") or ""
                ).strip(),
                "provider_league_id": str(
                    fixture.get("provider_league_id") or ""
                ).strip(),
                "league_name": str(
                    fixture.get("league_name") or ""
                ).strip(),
                "season": str(
                    fixture.get("season") or ""
                ).strip(),
                "round": str(
                    fixture.get("round") or ""
                ).strip(),
                "kickoff_utc": str(
                    fixture.get("kickoff_utc") or ""
                ).strip(),
                "observed_at_utc": observed_at,
                "team_id": team_id,
                "team_name": team_name,
                "side": side,
                "opponent_name": opponent,
                "source": "API-Football /fixtures/statistics",
                "research_only": "true",
                "creates_signal": "false",
                "probability_mutation": "false",
                "eligibility_mutation": "false",
                "stake_changes": "false",
                "forward_journal_mutation": "false",
            }
        )

        usable = 0

        statistics = block.get("statistics") or []
        if not isinstance(statistics, list):
            statistics = []

        for stat in statistics:
            if not isinstance(stat, dict):
                continue

            provider_type = str(
                stat.get("type") or ""
            ).strip()

            target = STAT_MAP.get(provider_type)
            if not target:
                continue

            value = clean_number(stat.get("value"))
            if value is None:
                continue

            row[target] = value
            usable += 1

        if usable:
            rows.append(row)

    sides = {
        str(row.get("side") or "").upper()
        for row in rows
    }

    if not {"HOME", "AWAY"}.issubset(sides):
        return []

    if len(rows) != 2:
        return []

    return rows


def capture(
    fixtures,
    existing_rows,
    get,
    now,
    max_fixtures,
):
    captured = completed_fixture_ids(existing_rows)
    candidates = candidate_fixtures(
        fixtures, captured, now, max_fixtures
    )

    new_rows = []
    captured_fixture_ids = []
    warnings = []
    attempts = []
    deferred = 0

    for index, fixture in enumerate(candidates):
        fixture_id = str(
            fixture.get("fixture_id") or ""
        ).strip()

        attempted_at = iso(now)

        try:
            payload = get(
                "/fixtures/statistics",
                {"fixture": fixture_id},
                ttl_seconds=30 * 24 * 3600,
                force_refresh=False,
            )

        except audit.ProtectedBudgetError as exc:
            deferred = len(candidates) - index
            warnings.append(str(exc))
            break

        except (
            ApiFootballBrokerError,
            RuntimeError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            attempts.append(
                {
                    "fixture_id": fixture_id,
                    "attempted_at_utc": attempted_at,
                    "result": "ERROR",
                }
            )
            warnings.append(
                f"{fixture_id}: {exc}"
            )
            continue

        rows = normalize_team_statistics(
            payload, fixture, attempted_at
        )

        if not rows:
            attempts.append(
                {
                    "fixture_id": fixture_id,
                    "attempted_at_utc": attempted_at,
                    "result": "NO_DATA",
                }
            )
            continue

        new_rows.extend(rows)
        captured_fixture_ids.append(fixture_id)

        attempts.append(
            {
                "fixture_id": fixture_id,
                "attempted_at_utc": attempted_at,
                "result": "CAPTURED",
            }
        )

    merged = merge_rows(
        existing_rows, new_rows
    )

    return {
        "rows": merged,
        "new_rows": len(new_rows),
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
    existing_rows = read_csv(LEDGER)
    existing_backlog = read_csv(BACKLOG)

    backlog_before = sync_backlog(
        existing_backlog,
        fixtures,
        existing_rows,
        now,
    )

    state = audit.read(SHARED_STATE)
    reserve = protected_calls(OPS, now)

    max_calls = int(
        os.getenv("STAGE81_MAX_API_CALLS", "2")
    )

    daily_limit = int(
        os.getenv(
            "STAGE71_MAX_DAILY_API_CALLS", "180"
        )
    )

    budget = audit.Budget(
        s53.api_get,
        state,
        now,
        limit=max_calls,
        daily_limit=daily_limit,
        protected_calls=reserve["total"],
        checkpoint=lambda value: audit.save(
            SHARED_STATE, value
        ),
    )

    result = capture(
        backlog_before["rows"],
        existing_rows,
        budget,
        now,
        int(
            os.getenv(
                "STAGE81_MAX_FIXTURES_PER_RUN",
                str(max_calls),
            )
        ),
    )

    attempted_backlog = record_attempts(
        backlog_before["rows"],
        result["attempts"],
    )

    backlog_after = sync_backlog(
        attempted_backlog,
        [],
        result["rows"],
        now,
    )

    if result["rows"] or LEDGER.exists():
        write_csv_atomic(
            LEDGER,
            LEDGER_FIELDS,
            result["rows"],
        )

    if backlog_after["rows"] or BACKLOG.exists():
        write_csv_atomic(
            BACKLOG,
            BACKLOG_FIELDS,
            backlog_after["rows"],
        )

    audit.save(SHARED_STATE, state)

    no_data_attempts = sum(
        item.get("result") == "NO_DATA"
        for item in result["attempts"]
    )

    error_attempts = sum(
        item.get("result") == "ERROR"
        for item in result["attempts"]
    )

    meta = {
        "version": "PBK_STAGE81_TEAM_MATCH_STATISTICS_V1",
        "run_at_utc": iso(now),
        "status": (
            "ATTENTION"
            if result["warnings"]
            else (
                "WAITING"
                if result["deferred_fixtures"]
                else "OK"
            )
        ),
        "provider_endpoint": "/fixtures/statistics",
        "provider_calls": budget.calls,
        "daily_api_calls": state.get(
            "api_day_calls", 0
        ),
        "protected_calls": reserve,
        "candidate_fixtures": result[
            "candidate_fixtures"
        ],
        "captured_fixtures": result[
            "captured_fixtures"
        ],
        "captured_fixture_ids": result[
            "captured_fixture_ids"
        ],
        "deferred_fixtures": result[
            "deferred_fixtures"
        ],
        "attempted_fixtures": len(
            result["attempts"]
        ),
        "no_data_attempts": no_data_attempts,
        "error_attempts": error_attempts,
        "backlog_terminal_seen_this_run": (
            backlog_before["terminal_seen"]
        ),
        "backlog_new_this_run": (
            backlog_before["new_rows"]
        ),
        "backlog_rows": len(
            backlog_after["rows"]
        ),
        "backlog_pending": backlog_after[
            "pending"
        ],
        "backlog_captured": backlog_after[
            "captured"
        ],
        "backlog_persists_across_round_rotation": True,
        "fair_retry_order": True,
        "new_team_stat_rows": result[
            "new_rows"
        ],
        "total_team_stat_rows": len(
            result["rows"]
        ),
        "raw_archive_requested_via_shared_broker": True,
        "raw_archive_durable_only_when_configured": True,
        "research_only": True,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "warnings": result["warnings"],
    }

    META.parent.mkdir(
        parents=True, exist_ok=True
    )

    META.write_text(
        json.dumps(
            meta,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            meta,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
