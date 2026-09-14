#!/usr/bin/env python3
"""PBK formation / coach / expected-XI read model.

Roadmap item 7 is deliberately read-only and provider-free. It composes already
captured Stage55/Stage56 lineup evidence from the Stage72 SQLite projection.
Confirmed official XI always wins for display. Before an official XI exists, an
expected XI may be reconstructed only from prior complete official starting XIs
that were observed before the target kickoff. No probability, eligibility,
stake, Value Radar, Forward or settlement state is changed here.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone

MIN_EXPECTED_HISTORY = 2
MAX_EXPECTED_HISTORY = 5


def _table_exists(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(conn, table):
    return [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]


def _dict_rows(cursor):
    names = [item[0] for item in cursor.description] if cursor.description else []
    rows = []
    for raw in cursor.fetchall():
        rows.append(dict(raw) if hasattr(raw, "keys") else dict(zip(names, raw)))
    return rows


def _fixture_rows(conn, table, fixture_id):
    if not _table_exists(conn, table):
        return []
    cols = set(_columns(conn, table))
    id_col = "api_fixture_id" if "api_fixture_id" in cols else (
        "fixture_id" if "fixture_id" in cols else None
    )
    if not id_col:
        return []
    return _dict_rows(conn.execute(
        f'SELECT * FROM "{table}" WHERE CAST("{id_col}" AS TEXT)=?',
        (str(fixture_id),),
    ))


def _rotation_table(conn):
    """Use a stable alias when present, otherwise Stage72's automatic raw CSV table."""
    if _table_exists(conn, "rotation_snapshots"):
        return "rotation_snapshots"
    if _table_exists(conn, "raw_rotation_snapshots"):
        return "raw_rotation_snapshots"
    return None


def _parse_utc(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def _json(value, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _complete_xi(value):
    items = _json(value, []) if isinstance(value, str) else (value or [])
    if not isinstance(items, list) or len(items) != 11:
        return []
    output, ids = [], set()
    for item in items:
        if not isinstance(item, dict):
            return []
        player = item.get("player") if isinstance(item.get("player"), dict) else item
        pid = str(player.get("id") or "").strip()
        name = str(player.get("name") or player.get("player_name") or "").strip()
        if not pid or pid in ids:
            return []
        ids.add(pid)
        output.append({
            "id": pid,
            "name": name or None,
            "number": player.get("number"),
            "pos": player.get("pos") or None,
            "grid": player.get("grid") or None,
            "position": player.get("position"),
            "lastname": player.get("lastname") or player.get("last_name"),
        })
    return output


def _latest_before(rows, cutoff, timestamp_field="captured_at_utc"):
    eligible = []
    for row in rows:
        observed = _parse_utc(row.get(timestamp_field))
        if observed is not None and cutoff is not None and observed <= cutoff:
            eligible.append((observed, row))
    return max(eligible, key=lambda item: item[0])[1] if eligible else None


def _fixture_identity(conn, fixture_id):
    rows = _fixture_rows(conn, "current_round_matches", fixture_id)
    if not rows:
        return None
    row = rows[0]
    context_rows = _fixture_rows(conn, "context_latest", fixture_id)
    context = _latest_before(context_rows, _parse_utc(row.get("kickoff_utc")))
    rotation_table = _rotation_table(conn)
    rotation = _latest_before(_fixture_rows(conn, rotation_table, fixture_id),
                              _parse_utc(row.get("kickoff_utc"))) if rotation_table else None
    return {
        "fixture_id": str(row.get("fixture_id") or fixture_id),
        "kickoff_utc": row.get("kickoff_utc") or None,
        "home_team": row.get("home_team") or (context or {}).get("home_team") or None,
        "away_team": row.get("away_team") or (context or {}).get("away_team") or None,
        "home_team_id": row.get("home_team_id") or (context or {}).get("home_team_id") or (rotation or {}).get("home_team_id") or None,
        "away_team_id": row.get("away_team_id") or (context or {}).get("away_team_id") or (rotation or {}).get("away_team_id") or None,
        "status": row.get("status") or None,
    }


def _confirmed_from_context(row, side):
    if not row or str(row.get("lineups_available") or "").upper() not in {"YES", "TRUE", "1"}:
        return None
    xi = _complete_xi(row.get(f"{side}_start_xi_json"))
    if len(xi) != 11:
        return None
    return {
        "captured_at_utc": row.get("captured_at_utc") or None,
        "formation": row.get(f"{side}_formation") or None,
        "coach": row.get(f"{side}_coach") or None,
        "xi": xi,
        "source": "context_latest:official_lineup",
    }


def _confirmed_from_rotation(row, side, source_table="rotation_snapshots"):
    if not row or str(row.get("current_lineups_available") or "").upper() not in {"YES", "TRUE", "1"}:
        return None
    xi = _complete_xi(row.get(f"{side}_current_xi_json"))
    if len(xi) != 11:
        return None
    return {
        "captured_at_utc": row.get("captured_at_utc") or None,
        "formation": row.get(f"{side}_current_formation") or None,
        "coach": row.get(f"{side}_current_coach") or None,
        "xi": xi,
        "source": f"{source_table}:official_lineup",
    }


def _newer(a, b):
    if a is None:
        return b
    if b is None:
        return a
    at = _parse_utc(a.get("captured_at_utc"))
    bt = _parse_utc(b.get("captured_at_utc"))
    if bt is not None and (at is None or bt >= at):
        return b
    return a


def _history_for_team(conn, team_id, cutoff, target_fixture_id, table=None):
    table = table or _rotation_table(conn)
    if not team_id or not table:
        return []
    cols = set(_columns(conn, table))
    required = {"home_team_id", "away_team_id", "kickoff_utc", "captured_at_utc"}
    if not required.issubset(cols):
        return []
    rows = _dict_rows(conn.execute(
        f'SELECT * FROM "{table}" WHERE CAST(home_team_id AS TEXT)=? OR CAST(away_team_id AS TEXT)=?',
        (str(team_id), str(team_id)),
    ))
    observations = []
    seen = set()
    for row in rows:
        fixture = str(row.get("api_fixture_id") or "")
        if fixture and fixture == str(target_fixture_id):
            continue
        kickoff = _parse_utc(row.get("kickoff_utc"))
        captured = _parse_utc(row.get("captured_at_utc"))
        if cutoff is None or kickoff is None or captured is None or kickoff >= cutoff or captured > cutoff:
            continue
        side = "home" if str(row.get("home_team_id") or "") == str(team_id) else "away"
        xi = _complete_xi(row.get(f"{side}_current_xi_json"))
        if len(xi) != 11:
            continue
        dedupe = fixture or f"{kickoff.isoformat()}:{side}"
        if dedupe in seen:
            continue
        seen.add(dedupe)
        observations.append({
            "fixture_id": fixture or None,
            "kickoff": kickoff,
            "captured": captured,
            "formation": row.get(f"{side}_current_formation") or None,
            "coach": row.get(f"{side}_current_coach") or None,
            "xi": xi,
        })
    observations.sort(key=lambda item: (item["kickoff"], item["captured"]), reverse=True)
    return observations[:MAX_EXPECTED_HISTORY]


def _mode_with_recency(values):
    present = [value for value in values if value]
    if not present:
        return None
    counts = Counter(present)
    best = max(counts.values())
    winners = {value for value, count in counts.items() if count == best}
    return next(value for value in present if value in winners)


def _expected_from_history(history, source_table="rotation_snapshots"):
    if len(history) < MIN_EXPECTED_HISTORY:
        return None
    stats = {}
    for recency, observation in enumerate(history):
        for player in observation["xi"]:
            pid = str(player.get("id") or "")
            if not pid:
                continue
            entry = stats.setdefault(pid, {
                "starts": 0,
                "best_recency": recency,
                "player": dict(player),
            })
            entry["starts"] += 1
            if recency < entry["best_recency"]:
                entry["best_recency"] = recency
                entry["player"] = dict(player)
    if len(stats) < 11:
        return None
    ranked = sorted(
        stats.items(),
        key=lambda item: (-item[1]["starts"], item[1]["best_recency"], item[0]),
    )[:11]
    xi = []
    for pid, entry in ranked:
        player = dict(entry["player"])
        player["id"] = pid
        player["historical_starts"] = entry["starts"]
        player["history_sample"] = len(history)
        xi.append(player)
    sample = len(history)
    confidence = "HIGH" if sample >= 5 else ("MEDIUM" if sample >= 3 else "LOW")
    return {
        "xi": xi,
        "formation": _mode_with_recency([row.get("formation") for row in history]),
        "coach": next((row.get("coach") for row in history if row.get("coach")), None),
        "confidence": confidence,
        "basis_fixtures": sample,
        "source": f"{source_table}:prior_official_xi",
        "captured_at_utc": max(row["captured"] for row in history).isoformat().replace("+00:00", "Z"),
        "latest_basis_kickoff_utc": history[0]["kickoff"].replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def _team_payload(name, team_id, confirmed, expected):
    limitations = []
    if confirmed is None:
        limitations.append("OFFICIAL_XI_NOT_CONFIRMED")
    if expected is None:
        limitations.append("EXPECTED_XI_HISTORY_INSUFFICIENT")
    status = "CONFIRMED" if confirmed else ("EXPECTED" if expected else "UNKNOWN")
    display = confirmed or expected or {}
    return {
        "team_id": team_id,
        "team_name": name,
        "status": status,
        "confirmed": confirmed is not None,
        "formation": display.get("formation"),
        "coach": display.get("coach"),
        "starting_xi": display.get("xi", []),
        "updated_at_utc": display.get("captured_at_utc"),
        "official": confirmed,
        "expected": expected,
        "expected_confidence": (expected or {}).get("confidence"),
        "expected_basis_fixtures": (expected or {}).get("basis_fixtures", 0),
        "limitations": limitations,
    }


def build_lineup_context(conn, fixture_id):
    fixture_id = str(fixture_id or "").strip()
    if not fixture_id:
        return 400, {
            "error": "MISSING_FIXTURE_ID", "read_only": True,
            "provider_polling": False, "no_lookahead": True,
        }
    fixture = _fixture_identity(conn, fixture_id)
    if fixture is None:
        return 404, {
            "error": "UNKNOWN_FIXTURE", "fixture_id": fixture_id,
            "read_only": True, "provider_polling": False, "no_lookahead": True,
        }
    cutoff = _parse_utc(fixture.get("kickoff_utc"))
    rotation_table = _rotation_table(conn)
    def latest_official(side):
        best = None
        for table in ("context_latest", rotation_table):
            if not table:
                continue
            for row in _fixture_rows(conn, table, fixture_id):
                observed = _parse_utc(row.get("captured_at_utc"))
                if cutoff is None or observed is None or observed > cutoff:
                    continue
                candidate = (_confirmed_from_context(row, side) if table == "context_latest"
                             else _confirmed_from_rotation(row, side, table))
                best = _newer(best, candidate)
        return best

    home_confirmed = latest_official("home")
    away_confirmed = latest_official("away")
    home_history = _history_for_team(conn, fixture.get("home_team_id"), cutoff, fixture_id, rotation_table)
    away_history = _history_for_team(conn, fixture.get("away_team_id"), cutoff, fixture_id, rotation_table)
    home_expected = _expected_from_history(home_history, rotation_table or "rotation_snapshots")
    away_expected = _expected_from_history(away_history, rotation_table or "rotation_snapshots")
    home = _team_payload(
        fixture.get("home_team"), fixture.get("home_team_id"), home_confirmed, home_expected,
    )
    away = _team_payload(
        fixture.get("away_team"), fixture.get("away_team_id"), away_confirmed, away_expected,
    )
    confirmed_count = int(home["confirmed"]) + int(away["confirmed"])
    usable_count = int(home["status"] != "UNKNOWN") + int(away["status"] != "UNKNOWN")
    limitations = []
    if not fixture.get("home_team_id") or not fixture.get("away_team_id"):
        limitations.append("TEAM_IDS_UNAVAILABLE")
    if confirmed_count < 2:
        limitations.append("OFFICIAL_LINEUPS_PARTIAL_OR_PENDING")
    if usable_count < 2:
        limitations.append("EXPECTED_XI_COVERAGE_PARTIAL")
    status = "AVAILABLE" if confirmed_count == 2 else ("PARTIAL" if usable_count else "UNKNOWN")
    payload = {
        "fixture_id": fixture_id,
        "kickoff_utc": fixture.get("kickoff_utc"),
        "fixture_status": fixture.get("status"),
        "available": usable_count > 0,
        "status": status,
        "no_lookahead": True,
        "cutoff_policy": "captured_at_utc<=kickoff_utc; prior lineup kickoff<target kickoff",
        "rotation_projection": rotation_table,
        "home": home,
        "away": away,
        "coverage": {
            "status": status,
            "confirmed_teams": confirmed_count,
            "usable_teams": usable_count,
            "limitations": limitations,
        },
        "read_only": True,
        "provider_polling": False,
        "creates_signal": False,
        "eligibility_mutation": False,
        "model_mutation": False,
    }
    return 200, payload
