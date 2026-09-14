#!/usr/bin/env python3
"""PBK Match Card v2 read model.

This module is provider-free and read-only.  It composes already-projected
Stage72 data for one current-round fixture without changing model eligibility,
probabilities, Value Radar, Forward, or settlement state.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

CARD_VERSION = "v2"


def _table_exists(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _columns(conn, table):
    return [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]


def _dict_rows(cursor):
    names = [item[0] for item in cursor.description] if cursor.description else []
    output = []
    for row in cursor.fetchall():
        if hasattr(row, "keys"):
            output.append(dict(row))
        else:
            output.append(dict(zip(names, row)))
    return output


def _parse_utc(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def _latest(rows, *fields):
    def key(row):
        for field in fields:
            parsed = _parse_utc(row.get(field))
            if parsed is not None:
                return parsed
        return datetime.min.replace(tzinfo=timezone.utc)
    return max(rows, key=key) if rows else None


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


def _json(value, default):
    if value in (None, ""):
        return default
    try:
        parsed = json.loads(value)
        return parsed
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _int_or_value(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _fixture_section(conn, fixture_id):
    rows = _fixture_rows(conn, "current_round_matches", fixture_id)
    if not rows:
        return None
    row = rows[0]
    league = None
    if _table_exists(conn, "current_round_leagues") and row.get("provider_league_id") not in (None, ""):
        matches = _dict_rows(conn.execute(
            "SELECT * FROM current_round_leagues WHERE CAST(provider_league_id AS TEXT)=? LIMIT 1",
            (str(row.get("provider_league_id")),),
        ))
        league = matches[0] if matches else None
    score_home = _int_or_value(row.get("score_home"))
    score_away = _int_or_value(row.get("score_away"))
    score = None if score_home is None and score_away is None else {
        "home": score_home, "away": score_away,
    }
    return {
        "fixture_id": str(row.get("fixture_id") or fixture_id),
        "provider_league_id": row.get("provider_league_id") or None,
        "league_name": row.get("league_name") or (league or {}).get("league_name") or None,
        "country": row.get("country") or (league or {}).get("country") or None,
        "country_flag_url": row.get("country_flag_url") or (league or {}).get("country_flag_url") or None,
        "league_logo_url": row.get("league_logo_url") or (league or {}).get("league_logo_url") or None,
        "season": row.get("season") or (league or {}).get("season") or None,
        "round": row.get("round") or (league or {}).get("round") or None,
        "kickoff_utc": row.get("kickoff_utc") or None,
        "status": row.get("status") or None,
        "source_status": row.get("source_status") or None,
        "elapsed": _int_or_value(row.get("elapsed")),
        "score": score,
        "home": {
            "name": row.get("home_team") or None,
            "logo_url": row.get("home_team_logo_url") or None,
            "red_cards": _int_or_value(row.get("red_cards_home")),
        },
        "away": {
            "name": row.get("away_team") or None,
            "logo_url": row.get("away_team_logo_url") or None,
            "red_cards": _int_or_value(row.get("red_cards_away")),
        },
        "observed_at_utc": row.get("observed_at_utc") or None,
        "live_observed_at_utc": row.get("live_observed_at_utc") or None,
        "live_freshness_status": row.get("live_freshness_status") or "unknown",
    }


def _motivation_section(conn, fixture_id):
    rows = _fixture_rows(conn, "fixture_motivation", fixture_id)
    if not rows:
        return {
            "available": False,
            "no_lookahead": True,
            "coverage": {"status": "UNKNOWN", "limitations": ["NO_STANDINGS_SNAPSHOT"]},
        }
    row = rows[0]
    payload = _json(row.get("payload_json"), None)
    if isinstance(payload, dict):
        return payload
    return {
        "available": False,
        "no_lookahead": True,
        "coverage": {"status": "UNKNOWN", "limitations": ["INVALID_MOTIVATION_PROJECTION"]},
    }


def _context_section(conn, fixture_id):
    rows = _fixture_rows(conn, "context_latest", fixture_id)
    row = _latest(rows, "captured_at_utc")
    if not row:
        return {"available": False}
    return {
        "available": True,
        "captured_at_utc": row.get("captured_at_utc") or None,
        "snapshot_type": row.get("snapshot_type") or None,
        "fixture_status": row.get("fixture_status") or None,
        "referee": row.get("referee") or None,
        "venue": {
            "name": row.get("venue_name") or None,
            "city": row.get("venue_city") or None,
        },
        "rest_hours": {
            "home": _int_or_value(row.get("home_rest_hours")),
            "away": _int_or_value(row.get("away_rest_hours")),
        },
        "previous_fixture": {
            "home": {
                "fixture_id": row.get("home_prev_fixture_id") or None,
                "date_utc": row.get("home_prev_date_utc") or None,
                "opponent": row.get("home_prev_opponent") or None,
                "competition": row.get("home_prev_competition") or None,
                "competition_class": row.get("home_prev_comp_class") or None,
                "is_uefa_or_cup": row.get("home_prev_is_uefa_or_cup") or None,
            },
            "away": {
                "fixture_id": row.get("away_prev_fixture_id") or None,
                "date_utc": row.get("away_prev_date_utc") or None,
                "opponent": row.get("away_prev_opponent") or None,
                "competition": row.get("away_prev_competition") or None,
                "competition_class": row.get("away_prev_comp_class") or None,
                "is_uefa_or_cup": row.get("away_prev_is_uefa_or_cup") or None,
            },
        },
        "next_fixture": {
            "home": {
                "fixture_id": row.get("home_next_fixture_id") or None,
                "date_utc": row.get("home_next_date_utc") or None,
                "opponent": row.get("home_next_opponent") or None,
                "competition": row.get("home_next_competition") or None,
                "competition_class": row.get("home_next_comp_class") or None,
                "hours_to_next": _int_or_value(row.get("home_hours_to_next")),
                "is_uefa_or_cup": row.get("home_next_is_uefa_or_cup") or None,
            },
            "away": {
                "fixture_id": row.get("away_next_fixture_id") or None,
                "date_utc": row.get("away_next_date_utc") or None,
                "opponent": row.get("away_next_opponent") or None,
                "competition": row.get("away_next_competition") or None,
                "competition_class": row.get("away_next_comp_class") or None,
                "hours_to_next": _int_or_value(row.get("away_hours_to_next")),
                "is_uefa_or_cup": row.get("away_next_is_uefa_or_cup") or None,
            },
        },
        "injuries": {
            "total": _int_or_value(row.get("injuries_count")),
            "home": _int_or_value(row.get("home_injuries_count")),
            "away": _int_or_value(row.get("away_injuries_count")),
            "items": _json(row.get("injuries_json"), []),
        },
        "lineups": {
            "available": str(row.get("lineups_available") or "").upper() in {"YES", "TRUE", "1"},
            "home_formation": row.get("home_formation") or None,
            "away_formation": row.get("away_formation") or None,
            "home_coach": row.get("home_coach") or None,
            "away_coach": row.get("away_coach") or None,
            "home_start_xi": _json(row.get("home_start_xi_json"), []),
            "away_start_xi": _json(row.get("away_start_xi_json"), []),
        },
        "context_only": str(row.get("context_only") or "").upper() in {"YES", "TRUE", "1"},
        "notes": row.get("notes") or None,
    }


def _prediction_section(conn, fixture_id):
    rows = _fixture_rows(conn, "probability_predictions", fixture_id)
    items = []
    for row in sorted(rows, key=lambda item: (item.get("rule") or "", item.get("selection") or "", item.get("created_at_utc") or "")):
        items.append({key: row.get(key) or None for key in (
            "prediction_id", "model_version", "rule", "selection",
            "trigger_captured_at_utc", "trigger_b365_home", "trigger_b365_draw",
            "trigger_b365_away", "p_market_no_vig", "p_pbk", "model_alpha",
            "created_at_utc", "status",
        )})
    return {
        "available": bool(items),
        "scope": "frozen_prematch_probability",
        "items": items,
        "eligibility_mutation": False,
    }


def _latest_odds_section(conn, fixture_id):
    rows = _fixture_rows(conn, "odds_snapshots", fixture_id)
    latest = {}
    for row in rows:
        key = (str(row.get("rule") or ""), str(row.get("selection") or ""))
        previous = latest.get(key)
        if previous is None or (_parse_utc(row.get("captured_at_utc")) or datetime.min.replace(tzinfo=timezone.utc)) >= (
                _parse_utc(previous.get("captured_at_utc")) or datetime.min.replace(tzinfo=timezone.utc)):
            latest[key] = row
    items = []
    for key in sorted(latest):
        row = latest[key]
        items.append({field: row.get(field) or None for field in (
            "forward_id", "rule", "selection", "captured_at_utc", "fixture_status",
            "current_kickoff_utc", "minutes_to_kickoff", "best_odds", "best_book",
            "bet365_odds", "user_best_odds", "user_best_book",
            "user_allowlist_configured", "api_odds_update_utc",
        )})
    return {
        "available": bool(items),
        "scope": "latest_known_canonical_signal_odds",
        "items": items,
    }


def _value_radar_section(conn, fixture_id):
    rows = _fixture_rows(conn, "value_radar_events", fixture_id)
    items = []
    for row in rows:
        item = {key: row.get(key) or None for key in (
            "radar_id", "radar_kind", "primary_rule", "selection", "first_crossed_at_utc",
            "model_version", "p_market_no_vig", "p_market_pct", "p_pbk", "p_pbk_pct",
            "edge_pp", "executable_odds", "executable_bookmaker", "ev", "ev_pct",
            "probability_status", "status", "source", "creates_signal", "stake_changes",
        )}
        item["source_rules"] = _json(row.get("source_rules"), [])
        items.append(item)
    return {
        "available": bool(items),
        "research_only": True,
        "creates_signal": False,
        "stake_changes": False,
        "items": items,
    }


def _canonical_section(conn, fixture_id):
    rows = _fixture_rows(conn, "canonical_signals", fixture_id)
    items = []
    for row in rows:
        items.append({key: row.get(key) or None for key in (
            "forward_id", "rule", "selection", "stake_u", "status", "result",
            "trigger_selected_odds", "market_execution_odds", "market_execution_bookmaker",
            "paper_user_execution_odds", "paper_user_execution_bookmaker",
            "paper_user_execution_at_utc", "user_close_odds", "user_close_bookmaker",
            "user_execution_status", "notes",
        )})
    return {"available": bool(items), "items": items}


def build_match_card(conn, fixture_id):
    fixture_id = str(fixture_id or "").strip()
    if not fixture_id:
        return 400, {
            "error": "MISSING_FIXTURE_ID", "card_version": CARD_VERSION,
            "read_only": True, "provider_polling": False,
        }
    fixture = _fixture_section(conn, fixture_id)
    if fixture is None:
        return 404, {
            "error": "UNKNOWN_FIXTURE", "fixture_id": fixture_id,
            "card_version": CARD_VERSION, "read_only": True, "provider_polling": False,
        }
    meta = {}
    if _table_exists(conn, "pbk_meta"):
        meta = dict(conn.execute("SELECT key,value FROM pbk_meta").fetchall())
    motivation = _motivation_section(conn, fixture_id)
    context = _context_section(conn, fixture_id)
    prediction = _prediction_section(conn, fixture_id)
    odds = _latest_odds_section(conn, fixture_id)
    radar = _value_radar_section(conn, fixture_id)
    canonical = _canonical_section(conn, fixture_id)
    sections = {
        "motivation": bool(motivation.get("available")),
        "context": bool(context.get("available")),
        "prediction": bool(prediction.get("available")),
        "odds": bool(odds.get("available")),
        "value_radar": bool(radar.get("available")),
        "canonical": bool(canonical.get("available")),
    }
    limitations = [f"{name.upper()}_UNAVAILABLE" for name, available in sections.items() if not available]
    payload = {
        "card_version": CARD_VERSION,
        "fixture_id": fixture_id,
        "generated_at_utc": meta.get("built_at_utc"),
        "fixture": fixture,
        "motivation": motivation,
        "context": context,
        "prediction": prediction,
        "odds": odds,
        "value_radar": radar,
        "canonical": canonical,
        "coverage": {
            "status": "AVAILABLE" if not limitations else "PARTIAL",
            "sections": sections,
            "limitations": limitations,
        },
        "read_only": True,
        "provider_polling": False,
        "eligibility_mutation": False,
        "model_mutation": False,
    }
    return 200, payload
