"""Match-aware, broker-only API-Football standings snapshot capture."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import api_football_broker as broker
import stage71_observation_audit as audit

OPS = Path(os.getenv("OPS_DIR", "ops"))
LEAGUES = OPS / "current_round_leagues.csv"
FIXTURES = OPS / "current_round_fixtures.csv"
SNAPSHOTS = OPS / "standings_snapshots.csv"
STATE = OPS / "standings_capture_state.json"
LAST_RUN = OPS / "standings_snapshot_last_run.json"
SEASON = os.getenv("API_FOOTBALL_SEASON", "2026")
DAILY_LIMIT = 180
DEFAULT_RUN_CAP = 16
NO_DATA_BACKOFF = timedelta(hours=6)
FIELDS = [
    "snapshot_id", "provider_league_id", "league_name", "season",
    "observed_at_utc", "team_id", "team_name", "team_logo_url", "rank",
    "points", "played", "win", "draw", "lose", "goals_for", "goals_against",
    "goals_diff", "form", "group_name", "description", "source",
]


def dt(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def stamp(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path):
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                return None
            return list(reader)
    except (OSError, UnicodeError, csv.Error):
        return None


def load_state(path=STATE):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def tracked_scope(leagues, fixtures):
    """Return only league-seasons represented in both tracked current-round files."""
    if leagues is None or fixtures is None:
        return None
    known = {}
    for row in leagues:
        lid, season = str(row.get("provider_league_id") or "").strip(), str(row.get("season") or "").strip()
        if lid and season:
            known[(lid, season)] = row
    return {key: value for key, value in known.items()
            if any((str(row.get("provider_league_id") or "").strip(), str(row.get("season") or "").strip()) == key
                   for row in fixtures)}


def candidate_leagues(leagues, fixtures, now, window_minutes=75):
    scope = tracked_scope(leagues, fixtures)
    if scope is None:
        return None
    candidates = {}
    for row in fixtures:
        key = (str(row.get("provider_league_id") or "").strip(),
               str(row.get("season") or "").strip())
        kickoff = dt(row.get("kickoff_utc"))
        if key not in scope or kickoff is None:
            continue
        delta = kickoff - now
        if timedelta(0) < delta <= timedelta(minutes=window_minutes):
            current = candidates.get(key)
            if current is None or kickoff < current["kickoff"]:
                candidates[key] = {"league": scope[key], "kickoff": kickoff}
    return candidates


def read_snapshot_rows(path=SNAPSHOTS):
    rows = read_csv(path)
    return [] if rows is None else rows


def adequate_snapshot(rows, league_id, season, kickoff):
    """Find a valid single snapshot in the 90-minute pre-kickoff window."""
    groups = {}
    for row in rows:
        if (str(row.get("provider_league_id") or "") != str(league_id)
                or str(row.get("season") or "") != str(season)):
            continue
        observed = dt(row.get("observed_at_utc"))
        snapshot = str(row.get("snapshot_id") or "")
        team = str(row.get("team_id") or "")
        if not observed or not snapshot or not team:
            continue
        groups.setdefault(snapshot, []).append((observed, team, row))
    eligible = []
    for snapshot, items in groups.items():
        observations = {item[0] for item in items}
        teams = [item[1] for item in items]
        if len(observations) != 1 or len(teams) != len(set(teams)):
            continue
        observed = next(iter(observations))
        if kickoff - timedelta(minutes=90) <= observed <= kickoff:
            eligible.append((observed, snapshot))
    if not eligible:
        return None
    return max(eligible)


def _value(mapping, *keys):
    current = mapping
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _groups(payload, requested_league, requested_season):
    if not isinstance(payload, dict) or not isinstance(payload.get("response"), list):
        raise ValueError("malformed standings response")
    result = payload["response"]
    if not result:
        return []
    flattened = []
    for item in result:
        league = item.get("league") if isinstance(item, dict) else None
        if not isinstance(league, dict):
            raise ValueError("missing standings league")
        if str(league.get("id") or "") != str(requested_league):
            raise ValueError("standings league mismatch")
        if str(league.get("season") or "") != str(requested_season):
            raise ValueError("standings season mismatch")
        standings = league.get("standings")
        if not isinstance(standings, list):
            raise ValueError("malformed standings groups")
        for group in standings:
            if not isinstance(group, list):
                raise ValueError("malformed standings group")
            flattened.extend((league, row) for row in group)
    return flattened


def normalize_response(payload, league_id, season, observed_at):
    """Normalize all provider groups, rejecting the entire observation on corruption."""
    groups = _groups(payload, league_id, season)
    if not groups:
        return []
    rows, seen = [], set()
    for league, item in groups:
        if not isinstance(item, dict):
            raise ValueError("malformed standings row")
        team = item.get("team") if isinstance(item.get("team"), dict) else {}
        team_id = str(team.get("id") or "").strip()
        if not team_id or team_id in seen:
            raise ValueError("missing or duplicate team id")
        seen.add(team_id)
        row = {
            "snapshot_id": "",
            "provider_league_id": str(league_id),
            "league_name": league.get("name"),
            "season": str(season),
            "observed_at_utc": stamp(observed_at),
            "team_id": team_id,
            "team_name": team.get("name"),
            "team_logo_url": team.get("logo"),
            "rank": item.get("rank"),
            "points": item.get("points"),
            "played": _value(item, "all", "played"),
            "win": _value(item, "all", "win"),
            "draw": _value(item, "all", "draw"),
            "lose": _value(item, "all", "lose"),
            "goals_for": _value(item, "all", "goals", "for"),
            "goals_against": _value(item, "all", "goals", "against"),
            "goals_diff": item.get("goalsDiff"),
            "form": item.get("form"),
            "group_name": item.get("group"),
            "description": item.get("description"),
            "source": "api-football:/standings",
        }
        rows.append(row)
    if not rows:
        raise ValueError("standings contained no usable teams")
    snapshot_id = "standings-" + hashlib.sha256(
        f"{league_id}|{season}|{rows[0]['observed_at_utc']}".encode("utf-8")
    ).hexdigest()[:20]
    for row in rows:
        row["snapshot_id"] = snapshot_id
    return rows


def append_snapshot(path, rows):
    existing = read_snapshot_rows(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing + rows)
    temp.replace(path)


def capture_run(now=None, get=None, ops=OPS):
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    leagues_path, fixtures_path = ops / LEAGUES.name, ops / FIXTURES.name
    snapshots_path, state_path, last_run_path = ops / SNAPSHOTS.name, ops / STATE.name, ops / LAST_RUN.name
    leagues, fixtures = read_csv(leagues_path), read_csv(fixtures_path)
    state = load_state(state_path)
    candidates = candidate_leagues(leagues, fixtures, now)
    meta = {
        "run_at_utc": stamp(now), "status": "OK",
        "tracked_leagues": len(tracked_scope(leagues, fixtures) or {}) if candidates is not None else 0,
        "candidate_leagues": len(candidates or {}), "provider_calls": 0,
        "snapshots_appended": 0, "rows_appended": 0,
        "skipped_no_upcoming_fixture": 0, "skipped_adequate_snapshot": 0,
        "skipped_no_data_backoff": 0, "budget_deferred_leagues": [],
        "api_day_calls_before": 0, "api_day_calls_after": 0,
        "reserved_live_calls": 0, "reserved_current_round_calls": 0,
        "safety_margin_calls": int(os.getenv("STAGE71_API_SAFETY_MARGIN", "10")),
        "standings_available_calls": 0, "warnings": [], "provider_polling": True,
    }
    if candidates is None:
        meta.update(status="SCHEDULE_UNKNOWN", warnings=["tracked current-round schedule missing or malformed"])
        save_json(last_run_path, meta)
        return meta
    shared = load_state(ops / "stage71_observation_state.json")
    daily_before = int(shared.get("api_day_calls", 0)) if shared.get("api_day") == now.date().isoformat() else 0
    forecast = audit.live_forecast(fixtures_path, now)
    if forecast.get("status") != "OPEN":
        meta.update(status="SCHEDULE_UNKNOWN", warnings=["LIVE reserve schedule unknown; standings deferred"])
        save_json(last_run_path, meta)
        return meta
    reserved_live = int(forecast["reserved_live_calls"])
    reserved_round = audit.current_round_forecast(now)
    safety = meta["safety_margin_calls"]
    protected = reserved_live + reserved_round + safety
    meta.update(reserved_live_calls=reserved_live, reserved_current_round_calls=reserved_round,
                standings_available_calls=max(0, DAILY_LIMIT - daily_before - protected),
                api_day_calls_before=daily_before)
    if not candidates:
        meta.update(api_day_calls_after=daily_before, skipped_no_upcoming_fixture=1)
        save_json(last_run_path, meta)
        return meta
    get = get or broker.api_get
    budget = audit.Budget(get, shared, now, limit=int(os.getenv("STANDINGS_MAX_API_CALLS", DEFAULT_RUN_CAP)),
                          daily_limit=DAILY_LIMIT, protected_calls=protected,
                          checkpoint=lambda value: save_json(ops / "stage71_observation_state.json", value))
    existing = read_snapshot_rows(snapshots_path)
    for key, candidate in candidates.items():
        league_id, season = key
        record = state.setdefault(f"{league_id}:{season}", {})
        last_attempt = dt(record.get("last_attempt_at_utc"))
        if record.get("last_status") == "NO_DATA" and last_attempt and now - last_attempt < NO_DATA_BACKOFF:
            meta["skipped_no_data_backoff"] += 1
            continue
        if adequate_snapshot(existing, league_id, season, candidate["kickoff"]):
            meta["skipped_adequate_snapshot"] += 1
            continue
        record["last_attempt_at_utc"] = stamp(now)
        try:
            payload = budget("/standings", {"league": league_id, "season": season}, force_refresh=True)
            observed = datetime.now(timezone.utc)
            rows = normalize_response(payload, league_id, season, observed)
            if not rows:
                record.update(last_status="NO_DATA", last_error="provider returned no standings")
                continue
            append_snapshot(snapshots_path, rows)
            existing.extend(rows)
            record.update(last_success_at_utc=stamp(observed), latest_snapshot_id=rows[0]["snapshot_id"],
                          last_status="OK", last_error=None)
            meta["snapshots_appended"] += 1
            meta["rows_appended"] += len(rows)
        except audit.ProtectedBudgetError as exc:
            meta["budget_deferred_leagues"].append(league_id)
            meta["status"] = "BUDGET_DEFERRED"
            meta["warnings"].append(str(exc))
            record.update(last_status="BUDGET_DEFERRED", last_error=str(exc))
        except Exception as exc:
            record.update(last_status="MALFORMED" if "standings" in str(exc).lower() else "PROVIDER_ERROR",
                          last_error=str(exc))
            meta["warnings"].append(f"{league_id}: {exc}")
    save_json(state_path, state)
    save_json(ops / "stage71_observation_state.json", shared)
    meta["provider_calls"] = budget.calls
    meta["api_day_calls_after"] = int(shared.get("api_day_calls", daily_before))
    if meta["budget_deferred_leagues"]:
        meta["status"] = "BUDGET_DEFERRED"
    save_json(last_run_path, meta)
    return meta


if __name__ == "__main__":
    print(json.dumps(capture_run(), ensure_ascii=False, indent=2))
