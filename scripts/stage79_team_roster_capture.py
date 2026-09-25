#!/usr/bin/env python3
"""Stage 79 — low-priority current team roster capture.

Uses API-Football ``/players/squads`` only through the shared broker/backend.
Roster data is slow-changing reference data, so successful team snapshots are
cached using a transfer-aware freshness contract and only stale/missing teams
from current-round fixtures are candidates. During broad transfer-sensitive
periods the TTL is short; outside them a confirmed roster is treated as
slow-changing reference data and reused for longer. Big-5/upcoming teams are filled first so Match Card's manual
lineup picker is useful before expected/official XI exists.

This stage is context/reference only and never mutates canonical probability,
EV, R1/R2/R3 eligibility, stake, settlement or Forward evidence.
"""
from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import stage53_daily_screener as s53
import stage71_observation_audit as audit
from api_football_broker import ApiFootballBrokerError

OPS = Path(os.getenv("OPS_DIR", "ops"))
FIXTURES = OPS / "current_round_fixtures.csv"
ROSTERS = OPS / "team_rosters.csv"
META = OPS / "stage79_last_run.json"
SHARED_STATE = OPS / "stage71_observation_state.json"

BIG5 = {"39", "61", "78", "135", "140"}
TEAM_ID_RE = re.compile(r"/teams/(\d+)(?:\.[A-Za-z0-9]+)?(?:\?|$)")
ROSTER_FIELDS = [
    "team_id", "team_name", "captured_at_utc", "player_id", "player_name",
    "age", "number", "position", "photo_url", "source",
]


def iso(value=None):
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
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


def team_id_from_fixture(row, side):
    explicit = str(row.get(f"{side}_team_id") or "").strip()
    if explicit:
        return explicit
    logo = str(row.get(f"{side}_team_logo_url") or "")
    match = TEAM_ID_RE.search(logo)
    return match.group(1) if match else ""


DEFAULT_TRANSFER_SENSITIVE_PERIODS = "01-01:02-15,06-01:09-10"


def _month_day(value):
    return value.month * 100 + value.day


def transfer_sensitive(now, periods=None):
    """Conservative broad transfer-sensitive calendar, not a legal registration claim."""
    raw = str(periods or os.getenv(
        "STAGE79_ROSTER_TRANSFER_SENSITIVE_PERIODS",
        DEFAULT_TRANSFER_SENSITIVE_PERIODS,
    )).strip()
    point = _month_day(now)
    for part in raw.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        start, end = [x.strip() for x in part.split(":", 1)]
        try:
            sm, sd = [int(x) for x in start.split("-", 1)]
            em, ed = [int(x) for x in end.split("-", 1)]
            lo = sm * 100 + sd
            hi = em * 100 + ed
        except (TypeError, ValueError):
            continue
        if lo <= hi:
            if lo <= point <= hi:
                return True
        else:
            if point >= lo or point <= hi:
                return True
    return False


def effective_roster_ttl_days(
    now,
    *,
    stable_days=None,
    sensitive_days=None,
    periods=None,
):
    stable = max(1, int(
        stable_days
        if stable_days is not None
        else os.getenv("STAGE79_ROSTER_STABLE_TTL_DAYS", "28")
    ))
    sensitive = max(1, int(
        sensitive_days
        if sensitive_days is not None
        else os.getenv("STAGE79_ROSTER_SENSITIVE_TTL_DAYS", "3")
    ))
    return sensitive if transfer_sensitive(now, periods=periods) else stable


def latest_capture_by_team(rows):
    latest = {}
    for row in rows:
        tid = str(row.get("team_id") or "").strip()
        captured = parse_utc(row.get("captured_at_utc"))
        if tid and captured and (tid not in latest or captured > latest[tid]):
            latest[tid] = captured
    return latest


def candidate_teams(fixtures, roster_rows, now, limit, ttl_days=7, priority_team_ids=None):
    """Return stale/missing current teams, prioritising explicit ids then Big-5 and kickoff proximity."""
    latest = latest_capture_by_team(roster_rows)
    fresh_after = now - timedelta(days=max(1, int(ttl_days)))
    priority = {str(x).strip(): i for i, x in enumerate(priority_team_ids or []) if str(x).strip()}
    candidates = {}
    for row in fixtures:
        kickoff = parse_utc(row.get("kickoff_utc"))
        # Old completed fixtures should not drive current roster traffic.
        if kickoff and kickoff < now - timedelta(hours=6):
            continue
        league = str(row.get("provider_league_id") or "").strip()
        for side in ("home", "away"):
            tid = team_id_from_fixture(row, side)
            if not tid or latest.get(tid, datetime.min.replace(tzinfo=timezone.utc)) >= fresh_after:
                continue
            team_name = str(row.get(f"{side}_team") or "").strip()
            seconds = abs((kickoff - now).total_seconds()) if kickoff else 10**12
            key = (
                0 if tid in priority else 1,
                priority.get(tid, 10**6),
                0 if league in BIG5 else 1,
                0 if kickoff and kickoff >= now else 1,
                seconds,
                tid,
            )
            current = candidates.get(tid)
            if current is None or key < current[0]:
                candidates[tid] = (key, {"team_id": tid, "team_name": team_name, "league_id": league, "kickoff_utc": row.get("kickoff_utc")})
    return [item[1] for item in sorted(candidates.values(), key=lambda x: x[0])[: max(0, int(limit))]]


def normalize_squad(payload, requested_team_id, requested_team_name, captured_at):
    rows = []
    response = payload.get("response", []) if isinstance(payload, dict) else []
    blocks = [block for block in response if isinstance(block, dict)]
    preferred = next((block for block in blocks if str((block.get("team") or {}).get("id") or "") == str(requested_team_id)), None)
    block = preferred or (blocks[0] if blocks else None)
    if not block:
        return []
    team = block.get("team") or {}
    team_id = str(team.get("id") or requested_team_id or "").strip()
    team_name = team.get("name") or requested_team_name
    for player in block.get("players") or []:
        if not isinstance(player, dict):
            continue
        player_id = str(player.get("id") or "").strip()
        if not player_id:
            continue
        rows.append({
            "team_id": team_id,
            "team_name": team_name,
            "captured_at_utc": captured_at,
            "player_id": player_id,
            "player_name": player.get("name"),
            "age": player.get("age"),
            "number": player.get("number"),
            "position": player.get("position"),
            "photo_url": player.get("photo"),
            "source": "api-football:/players/squads",
        })
    return rows


def replace_team_rosters(existing, incoming):
    replaced = {str(row.get("team_id") or "").strip() for row in incoming if row.get("team_id")}
    kept = [dict(row) for row in existing if str(row.get("team_id") or "").strip() not in replaced]
    merged = kept + [dict(row) for row in incoming]
    return sorted(merged, key=lambda row: (str(row.get("team_name") or ""), str(row.get("position") or ""), str(row.get("player_name") or ""), str(row.get("player_id") or "")))


def protected_calls(ops, now):
    live = audit.live_forecast(ops / "current_round_fixtures.csv", now)
    live_calls = int(live.get("reserved_live_calls") or 0)
    round_calls = audit.current_round_forecast(now, calls_per_run=int(os.getenv("STAGE79_CURRENT_ROUND_CALLS_PER_RUN", "32")))
    standings_calls = max(0, int(os.getenv("STAGE79_STANDINGS_RESERVE_CALLS", "16")))
    safety = max(0, int(os.getenv("STAGE79_SAFETY_RESERVE_CALLS", "8")))
    return {
        "live": live_calls,
        "current_round": round_calls,
        "standings": standings_calls,
        "safety": safety,
        "total": live_calls + round_calls + standings_calls + safety,
    }


def capture(fixtures, existing, get, now, max_teams, ttl_days=7, priority_team_ids=None):
    candidates = candidate_teams(fixtures, existing, now, max_teams, ttl_days=ttl_days, priority_team_ids=priority_team_ids)
    incoming, captured_teams, warnings = [], [], []
    deferred = 0
    for index, team in enumerate(candidates):
        try:
            payload = get(
                "/players/squads", {"team": team["team_id"]},
                ttl_seconds=int(ttl_days) * 24 * 3600,
                force_refresh=False,
            )
        except audit.ProtectedBudgetError as exc:
            deferred = len(candidates) - index
            warnings.append(str(exc))
            break
        except (ApiFootballBrokerError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            warnings.append(f"{team['team_id']} {team.get('team_name')}: {exc}")
            continue
        rows = normalize_squad(payload, team["team_id"], team.get("team_name"), iso(now))
        if not rows:
            warnings.append(f"{team['team_id']} {team.get('team_name')}: provider returned no usable roster rows")
            continue
        incoming.extend(rows)
        captured_teams.append({"team_id": team["team_id"], "team_name": team.get("team_name"), "players": len(rows)})
    return {
        "rows": replace_team_rosters(existing, incoming),
        "candidate_teams": len(candidates),
        "captured_teams": captured_teams,
        "deferred_teams": deferred,
        "warnings": warnings,
    }


def main():
    now = datetime.now(timezone.utc)
    fixtures = read_csv(FIXTURES)
    existing = read_csv(ROSTERS)
    state = audit.read(SHARED_STATE)
    reserve = protected_calls(OPS, now)
    max_calls = int(os.getenv("STAGE79_MAX_API_CALLS", "8"))
    daily_limit = int(os.getenv("STAGE71_MAX_DAILY_API_CALLS", "180"))
    budget = audit.Budget(
        s53.api_get, state, now,
        limit=max_calls,
        daily_limit=daily_limit,
        protected_calls=reserve["total"],
        checkpoint=lambda value: audit.save(SHARED_STATE, value),
    )
    priorities = [x.strip() for x in os.getenv("STAGE79_PRIORITY_TEAM_IDS", "").split(",") if x.strip()]
    ttl_days = effective_roster_ttl_days(now)
    result = capture(
        fixtures,
        existing,
        budget,
        now,
        max_calls,
        ttl_days=ttl_days,
        priority_team_ids=priorities,
    )
    if result["rows"] or ROSTERS.exists():
        write_csv_atomic(ROSTERS, ROSTER_FIELDS, result["rows"])
    audit.save(SHARED_STATE, state)
    meta = {
        "version": "PBK_STAGE79_TEAM_ROSTERS_V1",
        "run_at_utc": iso(now),
        "status": "ATTENTION" if result["warnings"] else ("WAITING" if result["deferred_teams"] else "OK"),
        "provider_endpoint": "/players/squads",
        "provider_calls": budget.calls,
        "daily_api_calls": state.get("api_day_calls", 0),
        "protected_calls": reserve,
        "roster_ttl_days": ttl_days,
        "roster_freshness_policy": "TRANSFER_AWARE_V1",
        "transfer_sensitive": transfer_sensitive(now),
        "stable_ttl_days": max(1, int(os.getenv("STAGE79_ROSTER_STABLE_TTL_DAYS", "28"))),
        "sensitive_ttl_days": max(1, int(os.getenv("STAGE79_ROSTER_SENSITIVE_TTL_DAYS", "3"))),
        "transfer_sensitive_periods": os.getenv(
            "STAGE79_ROSTER_TRANSFER_SENSITIVE_PERIODS",
            DEFAULT_TRANSFER_SENSITIVE_PERIODS,
        ),
        "candidate_teams": result["candidate_teams"],
        "captured_teams": result["captured_teams"],
        "deferred_teams": result["deferred_teams"],
        "total_roster_rows": len(result["rows"]),
        "warnings": result["warnings"],
        "reference_only": True,
        "provider_polling_frontend": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
