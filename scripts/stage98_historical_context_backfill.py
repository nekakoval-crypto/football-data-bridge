#!/usr/bin/env python3
"""Stage98 — historical official-lineup and injury-evidence backfill.

Provider-facing research/archive capture for terminal fixtures already present in
Stage80 historical_fixtures.csv.

Goals:
- expand context evidence beyond canonical Stage55 forward-signal scope;
- preserve official lineups as historical evidence only when both starting XIs
  are complete;
- preserve injury rows only when the provider returns explicit injury evidence;
- never convert an empty injuries response into a false "zero injuries" fact;
- keep endpoint-specific retry state and exponential cooldown;
- use only the shared API-Football broker/budget/raw-R2 path.

This stage has no model, signal, probability, eligibility, stake, settlement or
Forward Journal authority.
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
HISTORICAL = OPS / "historical_fixtures.csv"
LINEUPS = OPS / "historical_lineup_evidence.csv"
INJURIES = OPS / "historical_injury_evidence.csv"
BACKLOG = OPS / "stage98_historical_context_backlog.csv"
META = OPS / "stage98_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

LINEUP_SOURCE = "api-football:/fixtures/lineups"
INJURY_SOURCE = "api-football:/injuries?fixture"
VERSION = "PBK_STAGE98_HISTORICAL_CONTEXT_BACKFILL_V1"

LINEUP_FIELDS = [
    "fixture_id", "provider_league_id", "league_name", "season", "round",
    "kickoff_utc", "captured_at_utc", "team_id", "team_name", "side",
    "formation", "coach", "starting_xi_json", "starting_xi_count", "source",
    "research_only", "creates_signal", "probability_mutation",
    "eligibility_mutation", "stake_changes", "forward_journal_mutation",
]

INJURY_FIELDS = [
    "fixture_id", "provider_league_id", "league_name", "season", "round",
    "kickoff_utc", "captured_at_utc", "team_id", "team_name", "player_id",
    "player_name", "availability_type", "reason", "source", "research_only",
    "creates_signal", "probability_mutation", "eligibility_mutation",
    "stake_changes", "forward_journal_mutation",
]

BACKLOG_FIELDS = [
    "fixture_id", "provider_league_id", "league_name", "season", "round",
    "kickoff_utc", "home_team", "away_team", "first_queued_at_utc",
    "last_seen_at_utc", "queue_source",
    "lineup_status", "lineup_attempt_count", "lineup_last_attempt_at_utc",
    "lineup_last_attempt_result", "lineup_captured_at_utc",
    "injury_status", "injury_attempt_count", "injury_last_attempt_at_utc",
    "injury_last_attempt_result", "injury_captured_at_utc",
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


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def truthy(value):
    return str(value or "").strip().upper() in {"1", "YES", "TRUE", "Y"}


def normalized_name(value):
    return " ".join(str(value or "").casefold().split())


def read_csv(path):
    if not Path(path).exists():
        return []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv_atomic(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def terminal_fixture(row):
    return bool(sval(row, "fixture_id") and truthy(row.get("terminal_observed")))


def kickoff_of(row):
    return sval(row, "latest_kickoff_utc") or sval(row, "first_kickoff_utc")


def lineup_key(row):
    return (sval(row, "fixture_id"), sval(row, "team_id"))


def injury_key(row):
    return (
        sval(row, "fixture_id"),
        sval(row, "team_id"),
        sval(row, "player_id") or sval(row, "player_name"),
        sval(row, "availability_type"),
        sval(row, "reason"),
    )


def merge_first(existing, incoming, key_fn):
    merged = {}
    for row in existing:
        key = key_fn(row)
        if all(key) and key not in merged:
            merged[key] = dict(row)
    added = 0
    for row in incoming:
        key = key_fn(row)
        if all(key) and key not in merged:
            merged[key] = dict(row)
            added += 1
    return [merged[key] for key in sorted(merged)], added


def completed_lineup_fixture_ids(rows):
    by_fixture = {}
    for row in rows:
        fixture_id = sval(row, "fixture_id")
        side = sval(row, "side").upper()
        try:
            count = int(float(sval(row, "starting_xi_count") or 0))
        except ValueError:
            count = 0
        if fixture_id and sval(row, "team_id") and side in {"HOME", "AWAY"} and count == 11:
            by_fixture.setdefault(fixture_id, set()).add(side)
    return {fid for fid, sides in by_fixture.items() if {"HOME", "AWAY"}.issubset(sides)}


def injury_fixture_ids(rows):
    return {sval(row, "fixture_id") for row in rows if sval(row, "fixture_id") and (sval(row, "player_id") or sval(row, "player_name"))}


def captured_at_by_fixture(rows):
    result = {}
    for row in rows:
        fid = sval(row, "fixture_id")
        stamp = sval(row, "captured_at_utc")
        if fid and stamp and (fid not in result or stamp < result[fid]):
            result[fid] = stamp
    return result


def sync_backlog(existing, historical, lineup_rows, injury_rows, now):
    merged = {
        sval(row, "fixture_id"): {field: row.get(field, "") for field in BACKLOG_FIELDS}
        for row in existing if sval(row, "fixture_id")
    }
    now_iso = iso(now)
    new_rows = 0
    terminal_seen = 0

    for fixture in historical:
        if not terminal_fixture(fixture):
            continue
        terminal_seen += 1
        fid = sval(fixture, "fixture_id")
        row = merged.get(fid)
        if row is None:
            row = {field: "" for field in BACKLOG_FIELDS}
            row["fixture_id"] = fid
            row["first_queued_at_utc"] = now_iso
            row["queue_source"] = "stage80_historical_terminal_fixture"
            row["lineup_attempt_count"] = "0"
            row["injury_attempt_count"] = "0"
            new_rows += 1
        for src, dst in (
            ("provider_league_id", "provider_league_id"),
            ("league_name", "league_name"),
            ("season", "season"),
            ("round", "round"),
            ("home_team", "home_team"),
            ("away_team", "away_team"),
        ):
            value = sval(fixture, src)
            if value:
                row[dst] = value
        kickoff = kickoff_of(fixture)
        if kickoff:
            row["kickoff_utc"] = kickoff
        row["last_seen_at_utc"] = now_iso
        merged[fid] = row

    lineups_done = completed_lineup_fixture_ids(lineup_rows)
    injuries_done = injury_fixture_ids(injury_rows)
    lineup_captured = captured_at_by_fixture(lineup_rows)
    injury_captured = captured_at_by_fixture(injury_rows)

    for fid, row in merged.items():
        if fid in lineups_done:
            row["lineup_status"] = "CAPTURED"
            row["lineup_captured_at_utc"] = row.get("lineup_captured_at_utc") or lineup_captured.get(fid, "")
        else:
            row["lineup_status"] = "PENDING"
            row["lineup_captured_at_utc"] = ""
        if fid in injuries_done:
            row["injury_status"] = "CAPTURED"
            row["injury_captured_at_utc"] = row.get("injury_captured_at_utc") or injury_captured.get(fid, "")
        else:
            row["injury_status"] = "PENDING"
            row["injury_captured_at_utc"] = ""

    rows = [merged[key] for key in sorted(
        merged,
        key=lambda fid: (parse_utc(merged[fid].get("kickoff_utc")) or now, fid),
    )]
    return {
        "rows": rows,
        "new_rows": new_rows,
        "terminal_seen": terminal_seen,
        "lineup_captured": sum(r.get("lineup_status") == "CAPTURED" for r in rows),
        "lineup_pending": sum(r.get("lineup_status") == "PENDING" for r in rows),
        "injury_captured": sum(r.get("injury_status") == "CAPTURED" for r in rows),
        "injury_pending": sum(r.get("injury_status") == "PENDING" for r in rows),
    }


def attempt_count(row, prefix):
    try:
        return max(0, int(sval(row, f"{prefix}_attempt_count") or "0"))
    except ValueError:
        return 0


def retry_cooldown_hours(row, prefix):
    result = sval(row, f"{prefix}_last_attempt_result").upper()
    attempts = attempt_count(row, prefix)
    if attempts <= 0:
        return 0.0
    if result == "NO_DATA":
        base = float(os.getenv("STAGE98_NO_DATA_RETRY_BASE_HOURS", "6"))
        cap = float(os.getenv("STAGE98_NO_DATA_RETRY_MAX_HOURS", "72"))
    elif result == "ERROR":
        base = float(os.getenv("STAGE98_ERROR_RETRY_BASE_HOURS", "1"))
        cap = float(os.getenv("STAGE98_ERROR_RETRY_MAX_HOURS", "12"))
    else:
        return 0.0
    return max(0.0, min(cap, base * (2 ** max(0, attempts - 1))))


def retry_ready(row, prefix, now):
    if sval(row, f"{prefix}_status").upper() == "CAPTURED":
        return False
    last = parse_utc(row.get(f"{prefix}_last_attempt_at_utc"))
    if last is None:
        return True
    cooldown = retry_cooldown_hours(row, prefix)
    return cooldown <= 0 or now >= last + timedelta(hours=cooldown)


def candidate_fixtures(rows, now, limit):
    candidates = [
        row for row in rows
        if retry_ready(row, "lineup", now) or retry_ready(row, "injury", now)
    ]

    def key(row):
        lineup_last = parse_utc(row.get("lineup_last_attempt_at_utc"))
        injury_last = parse_utc(row.get("injury_last_attempt_at_utc"))
        attempts = [x for x in (lineup_last, injury_last) if x is not None]
        last = min(attempts) if attempts else None
        never = not attempts
        return (
            0 if never else 1,
            last or datetime.min.replace(tzinfo=timezone.utc),
            parse_utc(row.get("kickoff_utc")) or now,
            sval(row, "fixture_id"),
        )

    candidates.sort(key=key)
    return candidates[:max(0, int(limit))]


def record_attempt(rows, fixture_id, prefix, attempted_at, result):
    output = []
    for row in rows:
        row = dict(row)
        if sval(row, "fixture_id") == str(fixture_id):
            row[f"{prefix}_attempt_count"] = str(attempt_count(row, prefix) + 1)
            row[f"{prefix}_last_attempt_at_utc"] = attempted_at
            row[f"{prefix}_last_attempt_result"] = result
        output.append(row)
    return output


def canonical_xi(block):
    output = []
    seen = set()
    for item in block.get("startXI") or []:
        if not isinstance(item, dict):
            continue
        player = item.get("player") or {}
        pid = str(player.get("id") or "").strip()
        name = str(player.get("name") or "").strip()
        ident = pid or name
        if not ident or ident in seen:
            continue
        seen.add(ident)
        output.append({
            "id": pid or None,
            "name": name or None,
            "number": player.get("number"),
            "pos": player.get("pos"),
            "grid": player.get("grid"),
        })
    return output


def normalize_lineups(payload, fixture, captured_at):
    response = payload.get("response", []) if isinstance(payload, dict) else []
    home_key = normalized_name(fixture.get("home_team"))
    away_key = normalized_name(fixture.get("away_team"))
    rows = []
    sides = set()

    for block in response or []:
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
        elif key == away_key and away_key:
            side = "AWAY"
        else:
            continue
        xi = canonical_xi(block)
        if len(xi) != 11:
            continue
        sides.add(side)
        rows.append({
            "fixture_id": sval(fixture, "fixture_id"),
            "provider_league_id": sval(fixture, "provider_league_id"),
            "league_name": sval(fixture, "league_name"),
            "season": sval(fixture, "season"),
            "round": sval(fixture, "round"),
            "kickoff_utc": sval(fixture, "kickoff_utc"),
            "captured_at_utc": captured_at,
            "team_id": team_id,
            "team_name": team_name,
            "side": side,
            "formation": block.get("formation") or "",
            "coach": (block.get("coach") or {}).get("name") or "",
            "starting_xi_json": json.dumps(xi, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            "starting_xi_count": "11",
            "source": LINEUP_SOURCE,
            "research_only": "true",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        })

    if len(rows) != 2 or not {"HOME", "AWAY"}.issubset(sides):
        return []
    return rows


def normalize_injuries(payload, fixture, captured_at):
    response = payload.get("response", []) if isinstance(payload, dict) else []
    rows = []
    seen = set()
    for item in response or []:
        if not isinstance(item, dict):
            continue
        player = item.get("player") or {}
        team = item.get("team") or {}
        team_id = str(team.get("id") or "").strip()
        team_name = str(team.get("name") or "").strip()
        player_id = str(player.get("id") or "").strip()
        player_name = str(player.get("name") or "").strip()
        availability_type = str(player.get("type") or "").strip()
        reason = str(player.get("reason") or "").strip()
        ident = player_id or player_name
        if not team_id or not ident:
            continue
        key = (team_id, ident, availability_type, reason)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "fixture_id": sval(fixture, "fixture_id"),
            "provider_league_id": sval(fixture, "provider_league_id"),
            "league_name": sval(fixture, "league_name"),
            "season": sval(fixture, "season"),
            "round": sval(fixture, "round"),
            "kickoff_utc": sval(fixture, "kickoff_utc"),
            "captured_at_utc": captured_at,
            "team_id": team_id,
            "team_name": team_name,
            "player_id": player_id,
            "player_name": player_name,
            "availability_type": availability_type,
            "reason": reason,
            "source": INJURY_SOURCE,
            "research_only": "true",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        })
    return rows


def protected_calls(now):
    live = audit.live_forecast(OPS / "current_round_fixtures.csv", now)
    current_round = audit.current_round_forecast(
        now,
        calls_per_run=int(os.getenv("STAGE98_CURRENT_ROUND_CALLS_PER_RUN", "32")),
    )
    standings = max(0, int(os.getenv("STAGE98_STANDINGS_RESERVE_CALLS", "16")))
    stage77 = max(0, int(os.getenv("STAGE98_STAGE77_RESERVE_CALLS", "48")))
    stage81 = max(0, int(os.getenv("STAGE98_STAGE81_RESERVE_CALLS", "12")))
    safety = max(0, int(os.getenv("STAGE98_SAFETY_RESERVE_CALLS", "16")))
    return {
        "live": int(live.get("reserved_live_calls") or 0),
        "current_round": int(current_round),
        "standings": standings,
        "stage77": stage77,
        "stage81": stage81,
        "safety": safety,
        "total": int(live.get("reserved_live_calls") or 0) + int(current_round) + standings + stage77 + stage81 + safety,
    }


def capture(backlog_rows, lineup_rows, injury_rows, get, now, max_fixtures):
    candidates = candidate_fixtures(backlog_rows, now, max_fixtures)
    new_lineups = []
    new_injuries = []
    warnings = []
    lineup_calls = injury_calls = 0
    lineup_no_data = injury_no_data = 0
    errors = 0
    deferred_tasks = 0
    tasks_attempted = 0

    rows = list(backlog_rows)
    stop = False
    for index, fixture in enumerate(candidates):
        fid = sval(fixture, "fixture_id")
        for prefix, path, normalizer in (
            ("lineup", "/fixtures/lineups", normalize_lineups),
            ("injury", "/injuries", normalize_injuries),
        ):
            current = next((r for r in rows if sval(r, "fixture_id") == fid), fixture)
            if not retry_ready(current, prefix, now):
                continue
            attempted_at = iso(now)
            try:
                payload = get(
                    path,
                    {"fixture": fid},
                    ttl_seconds=6 * 3600,
                    force_refresh=False,
                )
            except audit.ProtectedBudgetError as exc:
                remaining = 0
                for rest in candidates[index:]:
                    for pfx in ("lineup", "injury"):
                        cur = next((r for r in rows if sval(r, "fixture_id") == sval(rest, "fixture_id")), rest)
                        if retry_ready(cur, pfx, now):
                            remaining += 1
                deferred_tasks = remaining
                warnings.append(str(exc))
                stop = True
                break
            except (ApiFootballBrokerError, RuntimeError, ValueError, TypeError, KeyError) as exc:
                tasks_attempted += 1
                errors += 1
                rows = record_attempt(rows, fid, prefix, attempted_at, "ERROR")
                warnings.append(f"{prefix} {fid}: {exc}")
                continue

            tasks_attempted += 1
            if prefix == "lineup":
                lineup_calls += 1
            else:
                injury_calls += 1

            evidence = normalizer(payload, fixture, attempted_at)
            if not evidence:
                rows = record_attempt(rows, fid, prefix, attempted_at, "NO_DATA")
                if prefix == "lineup":
                    lineup_no_data += 1
                else:
                    injury_no_data += 1
                continue

            rows = record_attempt(rows, fid, prefix, attempted_at, "CAPTURED")
            if prefix == "lineup":
                new_lineups.extend(evidence)
            else:
                new_injuries.extend(evidence)
        if stop:
            break

    merged_lineups, lineup_added = merge_first(lineup_rows, new_lineups, lineup_key)
    merged_injuries, injury_added = merge_first(injury_rows, new_injuries, injury_key)
    final_backlog = sync_backlog(rows, [], merged_lineups, merged_injuries, now)

    return {
        "lineups": merged_lineups,
        "injuries": merged_injuries,
        "backlog": final_backlog,
        "candidate_fixtures": len(candidates),
        "tasks_attempted": tasks_attempted,
        "lineup_calls": lineup_calls,
        "injury_calls": injury_calls,
        "lineup_no_data": lineup_no_data,
        "injury_no_data": injury_no_data,
        "errors": errors,
        "deferred_tasks": deferred_tasks,
        "lineup_rows_added": lineup_added,
        "injury_rows_added": injury_added,
        "warnings": warnings,
    }


def main():
    now = datetime.now(timezone.utc)
    historical = read_csv(HISTORICAL)
    existing_lineups = read_csv(LINEUPS)
    existing_injuries = read_csv(INJURIES)
    existing_backlog = read_csv(BACKLOG)

    backlog_before = sync_backlog(
        existing_backlog,
        historical,
        existing_lineups,
        existing_injuries,
        now,
    )

    state = audit.read(SHARED_STATE)
    reserve = protected_calls(now)
    max_calls = int(os.getenv("STAGE98_MAX_API_CALLS", "96"))
    daily_limit = int(os.getenv("STAGE71_MAX_DAILY_API_CALLS", "7000"))
    budget = audit.Budget(
        s53.api_get,
        state,
        now,
        limit=max_calls,
        daily_limit=daily_limit,
        protected_calls=reserve["total"],
        checkpoint=lambda value: audit.save(SHARED_STATE, value),
    )

    result = capture(
        backlog_before["rows"],
        existing_lineups,
        existing_injuries,
        budget,
        now,
        int(os.getenv("STAGE98_MAX_FIXTURES_PER_RUN", "48")),
    )

    if result["lineups"] or LINEUPS.exists():
        write_csv_atomic(LINEUPS, LINEUP_FIELDS, result["lineups"])
    if result["injuries"] or INJURIES.exists():
        write_csv_atomic(INJURIES, INJURY_FIELDS, result["injuries"])
    if result["backlog"]["rows"] or BACKLOG.exists():
        write_csv_atomic(BACKLOG, BACKLOG_FIELDS, result["backlog"]["rows"])
    audit.save(SHARED_STATE, state)

    meta = {
        "version": VERSION,
        "run_at_utc": iso(now),
        "status": "ATTENTION" if result["warnings"] else ("WAITING" if result["deferred_tasks"] else "OK"),
        "provider_endpoints": ["/fixtures/lineups", "/injuries?fixture"],
        "provider_calls": budget.calls,
        "daily_api_calls": int(state.get("api_day_calls") or 0),
        "protected_calls": reserve,
        "historical_fixture_rows": len(historical),
        "terminal_fixtures": backlog_before["terminal_seen"],
        "backlog_rows": len(result["backlog"]["rows"]),
        "candidate_fixtures": result["candidate_fixtures"],
        "tasks_attempted": result["tasks_attempted"],
        "lineup_calls": result["lineup_calls"],
        "injury_calls": result["injury_calls"],
        "lineup_no_data": result["lineup_no_data"],
        "injury_no_data": result["injury_no_data"],
        "error_attempts": result["errors"],
        "deferred_tasks": result["deferred_tasks"],
        "lineup_evidence_rows": len(result["lineups"]),
        "injury_evidence_rows": len(result["injuries"]),
        "lineup_rows_added": result["lineup_rows_added"],
        "injury_rows_added": result["injury_rows_added"],
        "lineup_captured_fixtures": result["backlog"]["lineup_captured"],
        "lineup_pending_fixtures": result["backlog"]["lineup_pending"],
        "injury_evidence_fixtures": result["backlog"]["injury_captured"],
        "injury_pending_or_zero_unknown_fixtures": result["backlog"]["injury_pending"],
        "empty_injury_response_semantics": "UNKNOWN_NOT_ZERO",
        "warnings": result["warnings"],
        "raw_archive_requested_via_shared_broker": True,
        "research_only": True,
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
