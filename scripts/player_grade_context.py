#!/usr/bin/env python3
"""Provider-free Player Grade read model for Match Card v2.

Consumes historical Player Grade plus already-captured lineup/rotation/roster
evidence. Stage72 imports operational CSVs as ``raw_*`` tables. No provider
calls occur here. All historical grade/roster evidence is restricted to data
available no later than target kickoff.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict

from player_grade import rolling_form, xi_quality

TEAM_ID_RE = re.compile(r"/teams/(\d+)(?:\.[A-Za-z0-9]+)?(?:\?|$)")


def _table_exists(conn, name):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _rows(conn, sql, args=()):
    cur = conn.execute(sql, args)
    names = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(names, row)) for row in cur.fetchall()]


def _columns(conn, table):
    return {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}


def _player_id(player):
    if not isinstance(player, dict):
        return ""
    raw = player.get("player") if isinstance(player.get("player"), dict) else player
    return str(raw.get("id") or raw.get("player_id") or "").strip()


def _player_payload(player):
    raw = player.get("player") if isinstance(player, dict) and isinstance(player.get("player"), dict) else (player or {})
    return {
        "id": _player_id(raw),
        "name": raw.get("name") or raw.get("player_name"),
        "lastname": raw.get("lastname") or raw.get("last_name"),
        "number": raw.get("number"),
        "pos": raw.get("pos") or raw.get("position"),
        "grid": raw.get("grid"),
    }


def _position_short(value):
    value = str(value or "").strip().upper()
    if value.startswith("G"):
        return "G"
    if value.startswith("D"):
        return "D"
    if value.startswith("M"):
        return "M"
    if value.startswith("A") or value.startswith("F") or value in {"ST", "CF", "LW", "RW"}:
        return "F"
    return value[:1] if value else ""


def _selected_xi(team):
    team = team or {}
    official = team.get("official") or {}
    expected = team.get("expected") or {}
    if isinstance(official.get("xi"), list) and len(official["xi"]) == 11:
        return official["xi"], "OFFICIAL"
    if isinstance(team.get("starting_xi"), list) and len(team["starting_xi"]) == 11:
        return team["starting_xi"], str(team.get("status") or "CURRENT")
    if isinstance(expected.get("xi"), list) and len(expected["xi"]) == 11:
        return expected["xi"], "EXPECTED"
    return [], "UNKNOWN"


def _kickoff(conn, fixture_id):
    for table, fid in (("current_round_matches", "fixture_id"), ("screen_matches", "api_fixture_id"), ("canonical_signals", "api_fixture_id")):
        if not _table_exists(conn, table):
            continue
        cols = _columns(conn, table)
        if fid not in cols or "kickoff_utc" not in cols:
            continue
        row = conn.execute(f'SELECT kickoff_utc FROM "{table}" WHERE "{fid}"=? AND kickoff_utc IS NOT NULL AND kickoff_utc<>\'\' LIMIT 1', (str(fixture_id),)).fetchone()
        if row and row[0]:
            return str(row[0])
    return None


def _fixture_identity(conn, fixture_id):
    if not _table_exists(conn, "current_round_matches"):
        return {"home": {}, "away": {}}
    cols = _columns(conn, "current_round_matches")
    if "fixture_id" not in cols:
        return {"home": {}, "away": {}}
    rows = _rows(conn, 'SELECT * FROM current_round_matches WHERE CAST(fixture_id AS TEXT)=? LIMIT 1', (str(fixture_id),))
    if not rows:
        return {"home": {}, "away": {}}
    row = rows[0]
    out = {}
    for side in ("home", "away"):
        tid = str(row.get(f"{side}_team_id") or "").strip()
        if not tid:
            match = TEAM_ID_RE.search(str(row.get(f"{side}_team_logo_url") or ""))
            tid = match.group(1) if match else ""
        out[side] = {"team_id": tid or None, "team_name": row.get(f"{side}_team") or None}
    return out


def _grade_table(conn):
    for table in ("player_grade_snapshots", "raw_player_grade_snapshots"):
        if _table_exists(conn, table):
            cols = _columns(conn, table)
            if {"player_id", "kickoff_utc", "overall_grade"}.issubset(cols):
                return table
    return None


def _history_by_player(conn, cutoff):
    table = _grade_table(conn)
    if not table or not cutoff:
        return {}
    cols = _columns(conn, table)
    if "observed_at_utc" in cols:
        rows = _rows(
            conn,
            f'''SELECT * FROM "{table}"
                WHERE kickoff_utc < ?
                  AND (observed_at_utc IS NULL OR observed_at_utc='' OR observed_at_utc <= ?)
                ORDER BY kickoff_utc ASC''',
            (str(cutoff), str(cutoff)),
        )
    else:
        rows = _rows(conn, f'SELECT * FROM "{table}" WHERE kickoff_utc < ? ORDER BY kickoff_utc ASC', (str(cutoff),))
    out = defaultdict(list)
    for row in rows:
        pid = str(row.get("player_id") or "").strip()
        if not pid:
            continue
        try:
            grade = float(row.get("overall_grade"))
        except (TypeError, ValueError):
            continue
        item = dict(row)
        item["overall_grade"] = grade
        out[pid].append(item)
    return dict(out)


def _grade_for_player(player, history, cutoff):
    pid = _player_id(player)
    rows = history.get(pid, [])
    form = rolling_form(rows, before_utc=cutoff)
    last = rows[-1] if rows else None
    form5 = form.get("form_5")
    form10 = form.get("form_10")
    selected = form5 if form.get("sample_5", 0) >= 2 else (last.get("overall_grade") if last else None)
    confidence = "UNKNOWN"
    if form.get("sample_10", 0) >= 8:
        confidence = "HIGH"
    elif form.get("sample_5", 0) >= 3:
        confidence = "MEDIUM"
    elif rows:
        confidence = "LOW"
    return {
        "player_id": pid,
        "player_name": _player_payload(player).get("name"),
        "current_grade": selected,
        "grade_basis": "FORM_5" if form.get("sample_5", 0) >= 2 else ("LAST_MATCH" if last else None),
        "form_5": form5,
        "form_10": form10,
        "sample_5": form.get("sample_5", 0),
        "sample_10": form.get("sample_10", 0),
        "last_grade": last.get("overall_grade") if last else None,
        "last_grade_kickoff_utc": last.get("kickoff_utc") if last else None,
        "last_grade_observed_at_utc": last.get("observed_at_utc") if last else None,
        "confidence": confidence,
        "source": last.get("source") if last else None,
    }


def _roster_players(conn, team_id, cutoff):
    table = "team_rosters" if _table_exists(conn, "team_rosters") else ("raw_team_rosters" if _table_exists(conn, "raw_team_rosters") else None)
    if not team_id or not table:
        return []
    cols = _columns(conn, table)
    if not {"team_id", "player_id"}.issubset(cols):
        return []
    args = [str(team_id)]
    sql = f'SELECT * FROM "{table}" WHERE CAST(team_id AS TEXT)=?'
    if cutoff and "captured_at_utc" in cols:
        sql += " AND captured_at_utc <= ?"
        args.append(str(cutoff))
    rows = _rows(conn, sql, tuple(args))
    if not rows:
        return []
    if "captured_at_utc" in cols:
        latest = max(str(row.get("captured_at_utc") or "") for row in rows)
        rows = [row for row in rows if str(row.get("captured_at_utc") or "") == latest]
    players = []
    for row in rows:
        pid = str(row.get("player_id") or "").strip()
        if not pid:
            continue
        players.append({
            "id": pid,
            "name": row.get("player_name") or None,
            "lastname": row.get("last_name") or None,
            "number": row.get("number") or None,
            "pos": _position_short(row.get("position")),
            "grid": None,
        })
    return players


def _known_player_pool(conn, team_id, cutoff, current_xi):
    pool = {_player_id(p): _player_payload(p) for p in current_xi if _player_id(p)}
    for player in _roster_players(conn, team_id, cutoff):
        pid = _player_id(player)
        if pid:
            pool[pid] = {**pool.get(pid, {}), **_player_payload(player)}
    if team_id and _table_exists(conn, "raw_rotation_snapshots"):
        cols = _columns(conn, "raw_rotation_snapshots")
        needed = {"captured_at_utc", "home_team_id", "away_team_id", "home_current_xi_json", "away_current_xi_json"}
        if needed.issubset(cols):
            rows = _rows(conn, "SELECT * FROM raw_rotation_snapshots WHERE captured_at_utc <= ? ORDER BY captured_at_utc ASC", (str(cutoff or "9999"),))
            for row in rows:
                for side in ("home", "away"):
                    if str(row.get(f"{side}_team_id") or "") != str(team_id):
                        continue
                    try:
                        xi = json.loads(row.get(f"{side}_current_xi_json") or "[]")
                    except (TypeError, ValueError, json.JSONDecodeError):
                        xi = []
                    for player in xi if isinstance(xi, list) else []:
                        pid = _player_id(player)
                        if pid:
                            pool[pid] = {**pool.get(pid, {}), **_player_payload(player)}
    return sorted(pool.values(), key=lambda p: (str(p.get("pos") or ""), str(p.get("name") or ""), str(p.get("id") or "")))


def _team_context(conn, team, history, cutoff):
    xi, status = _selected_xi(team)
    grades = [_grade_for_player(player, history, cutoff) for player in xi]
    grades_by_player = {
        g["player_id"]: {"overall_grade": g["current_grade"]}
        for g in grades if g.get("player_id") and g.get("current_grade") is not None
    }
    quality = xi_quality([_player_payload(p) for p in xi], grades_by_player)
    team_id = str((team or {}).get("team_id") or "")
    pool = _known_player_pool(conn, team_id, cutoff, xi)
    grade_map = {g["player_id"]: g for g in grades}
    for player in pool:
        pid = _player_id(player)
        if pid not in grade_map:
            grade_map[pid] = _grade_for_player(player, history, cutoff)
    return {
        "team_id": team_id or None,
        "team_name": (team or {}).get("team_name"),
        "lineup_status": status,
        "formation": (team or {}).get("formation") or ((team or {}).get("official") or {}).get("formation") or ((team or {}).get("expected") or {}).get("formation"),
        "xi": [_player_payload(p) for p in xi],
        "grades": [grade_map[_player_id(p)] for p in xi if _player_id(p)],
        "grades_by_player": grade_map,
        "xi_quality": quality,
        "player_pool": pool,
        "pool_size": len(pool),
        "roster_available": bool(_roster_players(conn, team_id, cutoff)),
    }


def build_player_grade_context(conn, fixture_id, lineup_context):
    cutoff = _kickoff(conn, fixture_id)
    history = _history_by_player(conn, cutoff)
    identity = _fixture_identity(conn, fixture_id)
    home_team = dict((lineup_context or {}).get("home") or {})
    away_team = dict((lineup_context or {}).get("away") or {})
    for side, team in (("home", home_team), ("away", away_team)):
        if not team.get("team_id"):
            team["team_id"] = identity.get(side, {}).get("team_id")
        if not team.get("team_name"):
            team["team_name"] = identity.get(side, {}).get("team_name")
    home = _team_context(conn, home_team, history, cutoff)
    away = _team_context(conn, away_team, history, cutoff)
    available = any(g.get("current_grade") is not None for side in (home, away) for g in side["grades"])
    roster_available = bool(home.get("roster_available") or away.get("roster_available"))
    limitations = [] if available else ["PLAYER_GRADE_HISTORY_UNAVAILABLE"]
    if not roster_available:
        limitations.append("TEAM_ROSTER_UNAVAILABLE")
    return {
        "version": "PBK_PLAYER_GRADE_CONTEXT_V1",
        "fixture_id": str(fixture_id or ""),
        "kickoff_utc": cutoff,
        "available": available,
        "home": home,
        "away": away,
        "coverage": {
            "home_covered_players": home["xi_quality"].get("covered_players", 0),
            "away_covered_players": away["xi_quality"].get("covered_players", 0),
            "historical_player_rows": sum(len(v) for v in history.values()),
            "grade_table": _grade_table(conn),
            "roster_available": roster_available,
            "limitations": limitations,
        },
        "research_only": True,
        "no_lookahead": True,
        "provider_polling": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }
