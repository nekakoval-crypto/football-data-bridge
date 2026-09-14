#!/usr/bin/env python3
"""PBK Match Card v2 read model.

This module is provider-free and read-only. It composes already-projected
Stage72 data for one current-round fixture without changing model eligibility,
probabilities, Value Radar, Forward, or settlement state.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

CARD_VERSION = "v2"

MARKET_FAMILY_ORDER = (
    "MATCH_RESULT_1X2",
    "DOUBLE_CHANCE",
    "DRAW_NO_BET",
    "ASIAN_HANDICAP",
    "EUROPEAN_HANDICAP",
    "MATCH_TOTAL",
    "TEAM_TOTAL",
    "BTTS",
)
MARKET_LABELS = {
    "MATCH_RESULT_1X2": "Исход матча — П1 / Х / П2",
    "DOUBLE_CHANCE": "Двойной шанс — 1Х / Х2 / 12",
    "DRAW_NO_BET": "Фора 0 — Ф1(0) / Ф2(0)",
    "ASIAN_HANDICAP": "Азиатская фора",
    "EUROPEAN_HANDICAP": "Европейская фора 3-way",
    "MATCH_TOTAL": "Тотал матча — ТБ / ТМ",
    "TEAM_TOTAL": "Индивидуальные тоталы — ИТБ / ИТМ",
    "BTTS": "Обе забьют — Да / Нет",
}


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


def _float_or_none(value):
    try:
        number = float(str(value).strip())
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _novig_three_way(home, draw, away):
    odds = [_float_or_none(home), _float_or_none(draw), _float_or_none(away)]
    if any(value is None or value <= 1 for value in odds):
        return [None, None, None]
    implied = [1 / value for value in odds]
    total = sum(implied)
    if total <= 0:
        return [None, None, None]
    return [value / total for value in implied]


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
        item = {key: row.get(key) or None for key in (
            "prediction_id", "model_version", "rule", "selection",
            "trigger_captured_at_utc", "trigger_b365_home", "trigger_b365_draw",
            "trigger_b365_away", "p_market_no_vig", "p_pbk", "model_alpha",
            "created_at_utc", "status",
        )}
        item["market_family"] = "MATCH_RESULT_1X2" if str(row.get("rule") or "").upper() in {"R1", "R2", "R3"} else None
        items.append(item)
    return {
        "available": bool(items),
        "scope": "frozen_prematch_probability",
        "items": items,
        "eligibility_mutation": False,
    }


def _market_rows_before_kickoff(conn, table, fixture_id, kickoff_utc, timestamp_field="captured_at_utc"):
    cutoff = _parse_utc(kickoff_utc)
    if cutoff is None:
        return []
    output = []
    for row in _fixture_rows(conn, table, fixture_id):
        observed = _parse_utc(row.get(timestamp_field))
        if observed is not None and observed <= cutoff:
            output.append(row)
    return output


def _latest_market_row(conn, table, fixture_id, kickoff_utc, timestamp_field="captured_at_utc"):
    return _latest(_market_rows_before_kickoff(conn, table, fixture_id, kickoff_utc, timestamp_field), timestamp_field)


def _latest_market_groups(conn, table, fixture_id, kickoff_utc, key_fields):
    rows = _market_rows_before_kickoff(conn, table, fixture_id, kickoff_utc)
    latest = {}
    for row in rows:
        key = tuple(str(row.get(field) or "") for field in key_fields)
        previous = latest.get(key)
        if previous is None:
            latest[key] = row
            continue
        current_dt = _parse_utc(row.get("captured_at_utc"))
        previous_dt = _parse_utc(previous.get("captured_at_utc"))
        if current_dt and (previous_dt is None or current_dt >= previous_dt):
            latest[key] = row
    return [latest[key] for key in sorted(latest)]


def _market_item(selection, row, bet365=None, user=None, probability=None, *, line=None,
                 team_side=None, team_name=None, movement=None, best_odds=None, best_book=None):
    return {
        "selection": selection,
        "line": line,
        "team_side": team_side,
        "team_name": team_name,
        "bet365_odds": row.get(bet365) or None if bet365 else None,
        "user_odds": row.get(user) or None if user else None,
        "user_bookmaker": row.get("user_bookmaker") or None,
        "best_odds": row.get(best_odds) or None if best_odds else None,
        "best_book": row.get(best_book) or None if best_book else None,
        "market_no_vig": row.get(probability) or None if probability else None,
        "movement_pp": row.get(movement) or None if movement else None,
    }


def _market_family(family_id, *, items=None, observed_at=None, source=None, scope="OBSERVATION_ONLY",
                   limitations=None, no_quarter_lines=False):
    items = items or []
    limitations = limitations or []
    return {
        "id": family_id,
        "label_ru": MARKET_LABELS[family_id],
        "available": bool(items),
        "scope": scope,
        "research_only": scope in {"RESEARCH_ONLY", "PROSPECTIVE_DATA", "WATCH_RESEARCH"},
        "creates_signal": False,
        "stake_changes": False,
        "observed_at_utc": observed_at,
        "source": source,
        "pre_match_frozen": True,
        "no_quarter_lines": bool(no_quarter_lines),
        "items": items,
        "limitations": limitations,
    }


def _match_result_family(conn, fixture_id, kickoff_utc):
    row = _latest_market_row(conn, "match_result_snapshots", fixture_id, kickoff_utc)
    if row:
        items = [
            _market_item("П1", row, "b365_home", "user_home", "p_home"),
            _market_item("Х", row, "b365_draw", "user_draw", "p_draw"),
            _market_item("П2", row, "b365_away", "user_away", "p_away"),
        ]
        return _market_family("MATCH_RESULT_1X2", items=items, observed_at=row.get("captured_at_utc") or None,
                              source="stage61_market_snapshots", scope="WATCH_RESEARCH")
    screen = _latest_market_row(conn, "screen_matches", fixture_id, kickoff_utc, "screened_at_utc")
    if screen:
        p_home, p_draw, p_away = _novig_three_way(screen.get("b365_home"), screen.get("b365_draw"), screen.get("b365_away"))
        items = []
        for selection, odds_field, best_field, book_field, probability in (
            ("П1", "b365_home", "best_home_odds", "best_home_book", p_home),
            ("Х", "b365_draw", "best_draw_odds", "best_draw_book", p_draw),
            ("П2", "b365_away", "best_away_odds", "best_away_book", p_away),
        ):
            item = _market_item(selection, screen, odds_field, best_odds=best_field, best_book=book_field)
            item["market_no_vig"] = probability
            items.append(item)
        if any(any(item.get(field) not in (None, "") for field in ("bet365_odds", "best_odds")) for item in items):
            return _market_family("MATCH_RESULT_1X2", items=items, observed_at=screen.get("screened_at_utc") or None,
                                  source="stage53_latest_screen", scope="CANONICAL_INPUT_OBSERVATION")
    return _market_family("MATCH_RESULT_1X2", limitations=["NO_PREMATCH_1X2_SNAPSHOT"])


def _double_chance_family(conn, fixture_id, kickoff_utc):
    row = _latest_market_row(conn, "double_chance_snapshots", fixture_id, kickoff_utc)
    if not row:
        return _market_family("DOUBLE_CHANCE", scope="PROSPECTIVE_DATA", limitations=["NO_PREMATCH_DOUBLE_CHANCE_SNAPSHOT"])
    items = [
        _market_item("1Х", row, "b365_1x", "user_1x", "p_1x", movement="move_1x_pp"),
        _market_item("Х2", row, "b365_x2", "user_x2", "p_x2", movement="move_x2_pp"),
        _market_item("12", row, "b365_12", "user_12", "p_12", movement="move_12_pp"),
    ]
    return _market_family("DOUBLE_CHANCE", items=items, observed_at=row.get("captured_at_utc") or None,
                          source="stage71e_double_chance_snapshots", scope="PROSPECTIVE_DATA")


def _dnb_family(conn, fixture_id, kickoff_utc):
    row = _latest_market_row(conn, "dnb_snapshots", fixture_id, kickoff_utc)
    if not row:
        return _market_family("DRAW_NO_BET", scope="PROSPECTIVE_DATA", limitations=["NO_PREMATCH_DNB_SNAPSHOT"])
    items = [
        _market_item("Ф1(0)", row, "b365_f1_0", "user_f1_0", "p_f1_0", line="0", movement="move_f1_0_pp"),
        _market_item("Ф2(0)", row, "b365_f2_0", "user_f2_0", "p_f2_0", line="0", movement="move_f2_0_pp"),
    ]
    return _market_family("DRAW_NO_BET", items=items, observed_at=row.get("captured_at_utc") or None,
                          source="stage71g_dnb_snapshots", scope="PROSPECTIVE_DATA", no_quarter_lines=True)


def _european_handicap_family(conn, fixture_id, kickoff_utc):
    rows = _latest_market_groups(conn, "european_handicap_snapshots", fixture_id, kickoff_utc, ("home_handicap_line",))
    items = []
    observed = None
    for row in rows:
        line = str(row.get("home_handicap_line") or "").strip()
        try:
            numeric_line = float(line)
        except ValueError:
            continue
        if not numeric_line.is_integer():
            continue
        observed_dt = _parse_utc(row.get("captured_at_utc"))
        if observed_dt and (observed is None or observed_dt > observed):
            observed = observed_dt
        items.extend([
            _market_item("П1", row, "b365_home", "user_home", "p_home", line=line, movement="move_home_pp"),
            _market_item("Х", row, "b365_draw", "user_draw", "p_draw", line=line, movement="move_draw_pp"),
            _market_item("П2", row, "b365_away", "user_away", "p_away", line=line, movement="move_away_pp"),
        ])
    return _market_family(
        "EUROPEAN_HANDICAP", items=items,
        observed_at=observed.replace(microsecond=0).isoformat().replace("+00:00", "Z") if observed else None,
        source="stage71f_european_handicap_snapshots" if items else None,
        scope="PROSPECTIVE_DATA", limitations=[] if items else ["NO_PREMATCH_EUROPEAN_HANDICAP_SNAPSHOT"],
        no_quarter_lines=True,
    )


def _match_total_family(conn, fixture_id, kickoff_utc):
    row = _latest_market_row(conn, "match_total_snapshots", fixture_id, kickoff_utc)
    if not row:
        return _market_family("MATCH_TOTAL", scope="WATCH_RESEARCH", limitations=["NO_PREMATCH_MATCH_TOTAL_SNAPSHOT"])
    items = [
        _market_item("ТБ(2.5)", row, "b365_over25", "user_over25", "p_over25", line="2.5", movement="over_move_pp"),
        _market_item("ТМ(2.5)", row, "b365_under25", "user_under25", "p_under25", line="2.5"),
    ]
    return _market_family("MATCH_TOTAL", items=items, observed_at=row.get("captured_at_utc") or None,
                          source="stage62_ou_snapshots", scope="WATCH_RESEARCH")


def _team_total_family(conn, fixture_id, kickoff_utc):
    rows = _latest_market_groups(conn, "team_total_snapshots", fixture_id, kickoff_utc, ("team_side", "line"))
    items = []
    observed = None
    for row in rows:
        observed_dt = _parse_utc(row.get("captured_at_utc"))
        if observed_dt and (observed is None or observed_dt > observed):
            observed = observed_dt
        side = str(row.get("team_side") or "").upper() or None
        line = row.get("line") or None
        name = row.get("team_name") or None
        items.extend([
            _market_item("ИТБ", row, "b365_over", "user_over", "p_over", line=line, team_side=side,
                         team_name=name, movement="over_move_pp"),
            _market_item("ИТМ", row, "b365_under", "user_under", "p_under", line=line, team_side=side,
                         team_name=name),
        ])
    return _market_family(
        "TEAM_TOTAL", items=items,
        observed_at=observed.replace(microsecond=0).isoformat().replace("+00:00", "Z") if observed else None,
        source="stage71c_team_total_snapshots" if items else None,
        scope="PROSPECTIVE_DATA", limitations=[] if items else ["NO_PREMATCH_TEAM_TOTAL_SNAPSHOT"],
    )


def _btts_family(conn, fixture_id, kickoff_utc):
    row = _latest_market_row(conn, "btts_snapshots", fixture_id, kickoff_utc)
    if not row:
        return _market_family("BTTS", scope="WATCH_RESEARCH", limitations=["NO_PREMATCH_BTTS_SNAPSHOT"])
    items = [
        _market_item("ОЗ — Да", row, "b365_yes", "user_yes", "p_yes", movement="yes_move_pp"),
        _market_item("ОЗ — Нет", row, "b365_no", "user_no", "p_no"),
    ]
    return _market_family("BTTS", items=items, observed_at=row.get("captured_at_utc") or None,
                          source="stage63_btts_snapshots", scope="WATCH_RESEARCH")


def _markets_section(conn, fixture_id, kickoff_utc):
    families = {
        "MATCH_RESULT_1X2": _match_result_family(conn, fixture_id, kickoff_utc),
        "DOUBLE_CHANCE": _double_chance_family(conn, fixture_id, kickoff_utc),
        "DRAW_NO_BET": _dnb_family(conn, fixture_id, kickoff_utc),
        "ASIAN_HANDICAP": _market_family(
            "ASIAN_HANDICAP", scope="REFERENCE_ONLY",
            limitations=["GENERAL_ASIAN_HANDICAP_NOT_EXPOSED", "QUARTER_LINES_SUPPRESSED"],
            no_quarter_lines=True,
        ),
        "EUROPEAN_HANDICAP": _european_handicap_family(conn, fixture_id, kickoff_utc),
        "MATCH_TOTAL": _match_total_family(conn, fixture_id, kickoff_utc),
        "TEAM_TOTAL": _team_total_family(conn, fixture_id, kickoff_utc),
        "BTTS": _btts_family(conn, fixture_id, kickoff_utc),
    }
    ordered = [families[family_id] for family_id in MARKET_FAMILY_ORDER]
    available_count = sum(1 for family in ordered if family.get("available"))
    return {
        "available": available_count > 0,
        "scope": "PREMATCH_MARKET_OBSERVATIONS",
        "pre_match_frozen": True,
        "creates_signal": False,
        "stake_changes": False,
        "model_probability_created": False,
        "user_line_policy": "NO_QUARTER_ASIAN_HANDICAPS",
        "available_family_count": available_count,
        "total_family_count": len(ordered),
        "coverage_status": "AVAILABLE" if available_count == len(ordered) else ("PARTIAL" if available_count else "UNKNOWN"),
        "families": ordered,
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
    markets = _markets_section(conn, fixture_id, fixture.get("kickoff_utc"))
    odds = _latest_odds_section(conn, fixture_id)
    radar = _value_radar_section(conn, fixture_id)
    canonical = _canonical_section(conn, fixture_id)
    sections = {
        "motivation": bool(motivation.get("available")),
        "context": bool(context.get("available")),
        "prediction": bool(prediction.get("available")),
        "markets": bool(markets.get("available")),
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
        "markets": markets,
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
