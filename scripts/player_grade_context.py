#!/usr/bin/env python3
"""Provider-free Player Grade read model for Match Card v2.

The read model consumes optional historical ``player_grade_snapshots`` rows and
already-captured lineup/rotation evidence. Stage72 imports every operational CSV
as ``raw_*``, so the read model accepts either a future stable alias or the raw
projection. It never calls a provider and never writes canonical state. For a
target fixture all grade evidence is restricted to matches strictly before the
target kickoff and, when capture provenance exists, to observations available no
later than that kickoff.
"""
from __future__ import annotations

import json
from collections import defaultdict

from player_grade import rolling_form, xi_quality


def _table_exists(conn, name):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _rows(conn, sql, args=()):
    cur = conn.execute(sql, args)
    names = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(names, row)) for row in cur.fetchall()]


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
        cols = {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}
        if fid not in cols or "kickoff_utc" not in cols:
            continue
        row = conn.execute(f'SELECT kickoff_utc FROM "{table}" WHERE "{fid}"=? AND kickoff_utc IS NOT NULL AND kickoff_utc<>\'\' LIMIT 1', (str(fixture_id),)).fetchone()
        if row and row[0]:
            return str(row[0])
    return None


def _grade_table(conn):
    for table in ("player_grade_snapshots", "raw_player_grade_snapshots"):
        if _table_exists(conn, table):
            cols = {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}
            if {"player_id", "kickoff_utc", "overall_grade"}.issubset(cols):
                return table
    return None


def _history_by_player(conn, cutoff):
    table = _grade_table(conn)
    if not table or not cutoff:
        return {}
    cols = {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}
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


def _known_player_pool(conn, team_id, cutoff, current_xi):
    pool = {_player_id(p): _player_payload(p) for p in current_xi if _player_id(p)}
    if not team_id or not _table_exists(conn, "raw_rotation_snapshots"):
        return list(pool.values())
    cols = {row[1] for row in conn.execute('PRAGMA table_info("raw_rotation_snapshots")')}
    needed = {"captured_at_utc", "home_team_id", "away_team_id", "home_current_xi_json", "away_current_xi_json"}
    if not needed.issubset(cols):
        return list(pool.values())
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
    }


def build_player_grade_context(conn, fixture_id, lineup_context):
    cutoff = _kickoff(conn, fixture_id)
    history = _history_by_player(conn, cutoff)
    home = _team_context(conn, (lineup_context or {}).get("home") or {}, history, cutoff)
    away = _team_context(conn, (lineup_context or {}).get("away") or {}, history, cutoff)
    available = any(g.get("current_grade") is not None for side in (home, away) for g in side["grades"])
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
            "limitations": [] if available else ["PLAYER_GRADE_HISTORY_UNAVAILABLE"],
        },
        "research_only": True,
        "no_lookahead": True,
        "provider_polling": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
    }
