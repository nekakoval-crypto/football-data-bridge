#!/usr/bin/env python3
"""PBK Full Market Scanner.

Research-only market normalizer. It consumes already-fetched API-Football odds
payloads and inventories the requested PBK market families without making any
provider calls, creating signals, calculating PBK probability/EV, changing
stakes, or promoting a strategy.

The only "best" choice made here is the highest observed price for the exact
same market + line + selection. Cross-market best-bet selection belongs to the
later Probability/Value/Decision layers.
"""
from __future__ import annotations

import json
import math
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "pbk_full_market_scanner.json"

FIXED_SELECTIONS = {
    "MATCH_RESULT_1X2": ("P1", "X", "P2"),
    "DOUBLE_CHANCE": ("1X", "X2", "12"),
    "DRAW_NO_BET": ("F1(0)", "F2(0)"),
    "BTTS": ("YES", "NO"),
}
DYNAMIC_FAMILIES = (
    "ASIAN_HANDICAP",
    "EUROPEAN_HANDICAP",
    "MATCH_TOTAL",
    "TEAM_TOTAL_HOME",
    "TEAM_TOTAL_AWAY",
)


def num(value: Any) -> float | None:
    try:
        result = float(str(value).strip().replace(",", "."))
        return result if math.isfinite(result) else None
    except Exception:
        return None


def norm(value: Any) -> str:
    text = str(value or "").lower().replace("−", "-").replace("–", "-")
    return " ".join(re.sub(r"[^a-z0-9+./-]+", " ", text).split())


def norm_team(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def load_config(path: Path | str = DEFAULT_CONFIG) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _bet_id(bet: dict[str, Any]) -> int | None:
    try:
        return int(bet.get("id") or 0) or None
    except Exception:
        return None


def classify_bet(bet: dict[str, Any], known_ids: dict[str, Any]) -> str | None:
    bid = _bet_id(bet)
    name = norm(bet.get("name"))
    by_id = {int(v): k for k, v in known_ids.items() if str(v).strip()}
    if bid in by_id:
        return by_id[bid]

    if name in {"match winner", "1x2", "full time result", "match result"}:
        return "MATCH_RESULT_1X2"
    if "match winner" in name and "half" not in name:
        return "MATCH_RESULT_1X2"
    if name == "double chance" or ("double chance" in name and "half" not in name):
        return "DOUBLE_CHANCE"
    if (
        ("both teams" in name and "score" in name) or "btts" in name
    ) and "half" not in name:
        return "BTTS"

    forbidden = ("corner", "card", "booking", "shot", "offside", "foul", "throw in", "goal kick")
    if any(token in name for token in forbidden):
        return None
    if any(token in name for token in ("first half", "second half", "1st half", "2nd half")):
        return None
    if "over/under" in name or "over under" in name:
        if "home" in name or "away" in name or "team" in name:
            return None
        if "goal" in name or name in {"over/under", "over under"}:
            return "MATCH_TOTAL"
    return None


def _match_1x2(value: dict[str, Any], fixture_meta: dict[str, Any]) -> str | None:
    raw = str(value.get("value") or "").strip()
    low = norm(raw).replace(" ", "")
    if low in {"home", "1", "h"}:
        return "P1"
    if low in {"draw", "x", "d"}:
        return "X"
    if low in {"away", "2", "a"}:
        return "P2"

    label = norm_team(raw)
    home = norm_team(fixture_meta.get("home_team"))
    away = norm_team(fixture_meta.get("away_team"))
    if label and home and (label == home or SequenceMatcher(None, label, home).ratio() >= 0.84):
        return "P1"
    if label and away and (label == away or SequenceMatcher(None, label, away).ratio() >= 0.84):
        return "P2"
    return None


def _match_double_chance(value: dict[str, Any]) -> str | None:
    low = norm(value.get("value"))
    tokens = set(low.split())
    has_h = bool(tokens & {"home", "1"})
    has_a = bool(tokens & {"away", "2"})
    has_d = bool(tokens & {"draw", "x"})
    if has_h and has_d and not has_a:
        return "1X"
    if has_a and has_d and not has_h:
        return "X2"
    if has_h and has_a and not has_d:
        return "12"
    compact = re.sub(r"[^a-z0-9]", "", low)
    if compact in {"1x", "x1"}:
        return "1X"
    if compact in {"x2", "2x"}:
        return "X2"
    if compact in {"12", "21"}:
        return "12"
    return None


def _extract_line(value: dict[str, Any]) -> float | None:
    text = f"{value.get('value') or ''} {value.get('handicap') or ''}".replace(",", ".")
    found = re.findall(r"(?<!\d)([+-]?\d+(?:\.\d+)?)(?!\d)", text)
    return num(found[-1]) if found else None


def _match_ah(value: dict[str, Any]) -> tuple[str, float] | None:
    text = norm(value.get("value"))
    side = None
    if re.search(r"(^|\s)home(\s|$)", text):
        side = "H"
    elif re.search(r"(^|\s)away(\s|$)", text):
        side = "A"
    line = _extract_line(value)
    if not side or line is None or abs(line) > 10:
        return None
    return side, line


def _match_eh(value: dict[str, Any]) -> tuple[str, int] | None:
    text = norm(value.get("value"))
    m = re.match(r"^(home|draw|away)\s+([+-]?\d+(?:\.0+)?)$", text)
    if not m:
        return None
    line = num(m.group(2))
    if line is None or abs(line - round(line)) > 1e-9 or line == 0 or abs(line) > 10:
        return None
    return {"home": "H", "draw": "D", "away": "A"}[m.group(1)], int(round(line))


def _match_over_under(value: dict[str, Any]) -> tuple[str, float] | None:
    text = norm(f"{value.get('value') or ''} {value.get('handicap') or ''}")
    if "over" in text:
        side = "O"
    elif "under" in text:
        side = "U"
    else:
        return None
    line = _extract_line(value)
    if line is None or line < 0 or line > 20:
        return None
    return side, line


def _match_btts(value: dict[str, Any]) -> str | None:
    low = norm(value.get("value"))
    if low in {"yes", "y"} or ("yes" in low and "no" not in low):
        return "YES"
    if low in {"no", "n"} or ("no" in low and "yes" not in low):
        return "NO"
    return None


def _fmt_line(line: float | int | None) -> str:
    if line is None:
        return ""
    x = float(line)
    return f"{x:g}"


def _selection_label(family: str, selection: str, line: float | int | None) -> str:
    if family == "MATCH_RESULT_1X2":
        return selection
    if family == "DOUBLE_CHANCE":
        return selection
    if family == "DRAW_NO_BET":
        return "F1(0)" if selection == "H" else "F2(0)"
    if family == "ASIAN_HANDICAP":
        return f"F1({_fmt_line(line)})" if selection == "H" else f"F2({_fmt_line(line)})"
    if family == "EUROPEAN_HANDICAP":
        prefix = {"H": "EH1", "D": "EHX", "A": "EH2"}[selection]
        return f"{prefix}({_fmt_line(line)})"
    if family == "MATCH_TOTAL":
        return f"TB({_fmt_line(line)})" if selection == "O" else f"TM({_fmt_line(line)})"
    if family == "BTTS":
        return selection
    if family == "TEAM_TOTAL_HOME":
        return f"ITB1({_fmt_line(line)})" if selection == "O" else f"ITM1({_fmt_line(line)})"
    if family == "TEAM_TOTAL_AWAY":
        return f"ITB2({_fmt_line(line)})" if selection == "O" else f"ITM2({_fmt_line(line)})"
    return selection


def _is_half_grid(line: float | int | None) -> bool:
    if line is None:
        return False
    return abs(float(line) * 2 - round(float(line) * 2)) <= 1e-9


def _quote_key(family: str, selection: str, line: float | int | None) -> tuple[str, str, str]:
    return family, selection, _fmt_line(line)


def _parse_value(
    family: str,
    value: dict[str, Any],
    fixture_meta: dict[str, Any],
) -> tuple[str, float | int | None, str | None] | None:
    if family == "MATCH_RESULT_1X2":
        sel = _match_1x2(value, fixture_meta)
        return (sel, None, None) if sel else None
    if family == "DOUBLE_CHANCE":
        sel = _match_double_chance(value)
        return (sel, None, None) if sel else None
    if family == "ASIAN_HANDICAP":
        parsed = _match_ah(value)
        if not parsed:
            return None
        sel, line = parsed
        if abs(line) <= 1e-9:
            return sel, 0.0, "DRAW_NO_BET"
        return sel, line, None
    if family == "EUROPEAN_HANDICAP":
        parsed = _match_eh(value)
        return (parsed[0], parsed[1], None) if parsed else None
    if family in {"MATCH_TOTAL", "TEAM_TOTAL_HOME", "TEAM_TOTAL_AWAY"}:
        parsed = _match_over_under(value)
        return (parsed[0], parsed[1], None) if parsed else None
    if family == "BTTS":
        sel = _match_btts(value)
        return (sel, None, None) if sel else None
    return None


def _extract_fixture_meta_from_odds(payload: dict[str, Any]) -> dict[str, Any]:
    response = (payload or {}).get("response") or []
    if not response:
        return {}
    item = response[0] or {}
    league = item.get("league") or {}
    fixture = item.get("fixture") or {}
    return {
        "api_fixture_id": str(fixture.get("id") or item.get("fixture") or ""),
        "league": str(league.get("name") or ""),
        "league_id": league.get("id") or "",
        "kickoff_utc": str(fixture.get("date") or ""),
    }


def scan_fixture_odds(
    payload: dict[str, Any],
    fixture_meta: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_config()
    meta = _extract_fixture_meta_from_odds(payload)
    meta.update({k: v for k, v in (fixture_meta or {}).items() if v not in (None, "")})
    known_ids = cfg.get("known_api_football_bet_ids") or {}
    reference_book = str(cfg.get("reference_bookmaker") or "Bet365")
    user_book = str(cfg.get("executable_bookmaker") or "Marathonbet")

    quotes: dict[tuple[str, str, str], dict[str, Any]] = {}
    observed_bets: set[tuple[int | None, str]] = set()

    for item in (payload or {}).get("response", []) or []:
        update = str(item.get("update") or "")
        for bookmaker in item.get("bookmakers", []) or []:
            book_name = str(bookmaker.get("name") or "").strip()
            if not book_name:
                continue
            for bet in bookmaker.get("bets", []) or []:
                family = classify_bet(bet, known_ids)
                if not family:
                    continue
                bid = _bet_id(bet)
                bname = str(bet.get("name") or "").strip()
                observed_bets.add((bid, bname))
                for value in bet.get("values", []) or []:
                    odd = num(value.get("odd"))
                    if odd is None or odd <= 1:
                        continue
                    parsed = _parse_value(family, value, meta)
                    if not parsed:
                        continue
                    selection, line, override_family = parsed
                    actual_family = override_family or family
                    key = _quote_key(actual_family, selection, line)
                    row = quotes.setdefault(
                        key,
                        {
                            "market_family": actual_family,
                            "selection": selection,
                            "selection_label": _selection_label(actual_family, selection, line),
                            "line": line,
                            "bet_id": bid,
                            "bet_name": bname,
                            "bookmakers": {},
                        },
                    )
                    current = row["bookmakers"].get(book_name)
                    if current is None or odd > current["price"]:
                        row["bookmakers"][book_name] = {"price": odd, "update_utc": update}

    options: list[dict[str, Any]] = []
    for key in sorted(quotes, key=lambda x: (x[0], x[2], x[1])):
        row = quotes[key]
        books = row.pop("bookmakers")
        reference = books.get(reference_book)
        user = books.get(user_book)
        best_book, best_quote = max(books.items(), key=lambda pair: pair[1]["price"])
        quarter_blocked = row["market_family"] == "ASIAN_HANDICAP" and not _is_half_grid(row["line"])
        if quarter_blocked:
            status = "BLOCKED_QUARTER_ASIAN_HANDICAP"
            executable = False
        elif user is not None:
            status = "AVAILABLE_EXECUTABLE"
            executable = True
        elif reference is not None:
            status = "REFERENCE_ONLY"
            executable = False
        else:
            status = "AVAILABLE_OTHER_BOOK_ONLY"
            executable = False
        options.append(
            {
                **row,
                "reference_bookmaker": reference_book,
                "reference_price": reference["price"] if reference else None,
                "executable_bookmaker": user_book,
                "executable_price": user["price"] if user else None,
                "best_observed_price": best_quote["price"],
                "best_observed_bookmaker": best_book,
                "source_update_utc": max(
                    [q.get("update_utc") or "" for q in books.values()] or [""]
                ),
                "availability_status": status,
                "executable": executable,
                "probability_status": "NOT_EVALUATED_BY_SCANNER",
                "best_alternative_scope": "EXACT_MARKET_LINE_SELECTION_PRICE_ONLY",
            }
        )

    present_fixed = {
        family: {row["selection_label"] for row in options if row["market_family"] == family}
        for family in FIXED_SELECTIONS
    }
    for family, selections in FIXED_SELECTIONS.items():
        for selection_label in selections:
            if selection_label not in present_fixed[family]:
                options.append(
                    {
                        "market_family": family,
                        "selection": selection_label,
                        "selection_label": selection_label,
                        "line": 0.0 if family == "DRAW_NO_BET" else None,
                        "bet_id": None,
                        "bet_name": None,
                        "reference_bookmaker": reference_book,
                        "reference_price": None,
                        "executable_bookmaker": user_book,
                        "executable_price": None,
                        "best_observed_price": None,
                        "best_observed_bookmaker": None,
                        "source_update_utc": None,
                        "availability_status": "MISSING",
                        "executable": False,
                        "probability_status": "NOT_EVALUATED_BY_SCANNER",
                        "best_alternative_scope": "EXACT_MARKET_LINE_SELECTION_PRICE_ONLY",
                    }
                )

    coverage: dict[str, Any] = {}
    for family in cfg.get("target_market_families", []):
        family_rows = [row for row in options if row["market_family"] == family]
        available = [row for row in family_rows if row["availability_status"] != "MISSING"]
        executable = [row for row in available if row["executable"]]
        blocked = [row for row in available if row["availability_status"].startswith("BLOCKED_")]
        if family in FIXED_SELECTIONS:
            required = len(FIXED_SELECTIONS[family])
            seen = len({row["selection_label"] for row in available})
            if seen == 0:
                state = "MISSING"
            elif seen < required:
                state = "PARTIAL"
            elif executable:
                state = "AVAILABLE_EXECUTABLE"
            else:
                state = "AVAILABLE_NOT_EXECUTABLE"
            coverage[family] = {
                "status": state,
                "required_selections": list(FIXED_SELECTIONS[family]),
                "available_selection_count": seen,
                "executable_selection_count": len(executable),
            }
        else:
            if not available:
                state = "MISSING"
            elif executable:
                state = "AVAILABLE_EXECUTABLE"
            elif blocked and len(blocked) == len(available):
                state = "BLOCKED_BY_EXECUTION_POLICY"
            else:
                state = "AVAILABLE_NOT_EXECUTABLE"
            coverage[family] = {
                "status": state,
                "observed_selection_count": len(available),
                "executable_selection_count": len(executable),
                "blocked_selection_count": len(blocked),
                "observed_lines": sorted(
                    {_fmt_line(row.get("line")) for row in available if row.get("line") is not None},
                    key=lambda x: float(x),
                ),
            }

    options.sort(
        key=lambda row: (
            str(row["market_family"]),
            float(row["line"]) if row.get("line") is not None else -999.0,
            str(row["selection_label"]),
        )
    )
    return {
        "scanner_version": cfg.get("version", 1),
        "authority": "RESEARCH",
        "fixture": {
            "api_fixture_id": str(meta.get("api_fixture_id") or ""),
            "league": meta.get("league") or "",
            "league_id": meta.get("league_id") or "",
            "kickoff_utc": meta.get("kickoff_utc") or "",
            "home_team": meta.get("home_team") or "",
            "away_team": meta.get("away_team") or "",
        },
        "reference_bookmaker": reference_book,
        "executable_bookmaker": user_book,
        "options": options,
        "coverage": coverage,
        "observed_supported_bets": [
            {"bet_id": bid, "bet_name": name} for bid, name in sorted(observed_bets, key=lambda x: (x[0] or 0, x[1]))
        ],
        "policy": {
            "api_calls_added": 0,
            "cross_market_best_bet": False,
            "pbk_probability_calculated": False,
            "ev_calculated": False,
            "signals_created": 0,
            "watch_created": 0,
            "stake_changes": False,
            "canonical_changes": False,
            "quarter_asian_handicap_executable": False,
        },
    }


def _params_from_cache_key(key: Any) -> dict[str, str]:
    if not isinstance(key, tuple) or len(key) < 2:
        return {}
    try:
        return {str(k): str(v) for k, v in key[1]}
    except Exception:
        return {}


def _fixture_meta_from_cache(cache: dict[Any, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for key, payload in cache.items():
        if not isinstance(key, tuple) or not key or key[0] != "/fixtures":
            continue
        for item in (payload or {}).get("response", []) or []:
            fixture = item.get("fixture") or {}
            teams = item.get("teams") or {}
            league = item.get("league") or {}
            fid = str(fixture.get("id") or "")
            if not fid:
                continue
            result[fid] = {
                "api_fixture_id": fid,
                "league": league.get("name") or "",
                "league_id": league.get("id") or "",
                "kickoff_utc": fixture.get("date") or "",
                "home_team": (teams.get("home") or {}).get("name") or "",
                "away_team": (teams.get("away") or {}).get("name") or "",
            }
    return result


def materialize_from_stage71j_cache(
    cache: dict[Any, Any],
    fixture_ids: list[str],
    out_path: Path | str,
    config_path: Path | str = DEFAULT_CONFIG,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    meta = _fixture_meta_from_cache(cache)
    odds_by_fixture: dict[str, dict[str, Any]] = {}
    for key, payload in cache.items():
        if not isinstance(key, tuple) or not key or key[0] != "/odds":
            continue
        params = _params_from_cache_key(key)
        fid = params.get("fixture", "")
        if fid and set(params) == {"fixture"}:
            odds_by_fixture[fid] = payload

    reports = []
    missing_payloads = []
    for fixture_id in fixture_ids:
        fid = str(fixture_id)
        payload = odds_by_fixture.get(fid)
        if payload is None:
            missing_payloads.append(fid)
            continue
        reports.append(scan_fixture_odds(payload, meta.get(fid, {}), cfg))

    family_counts: dict[str, dict[str, int]] = {}
    for report in reports:
        for family, row in report["coverage"].items():
            counts = family_counts.setdefault(family, {})
            state = str(row.get("status") or "UNKNOWN")
            counts[state] = counts.get(state, 0) + 1

    payload = {
        "status": "OK",
        "scanner_version": cfg.get("version", 1),
        "authority": "RESEARCH",
        "fixture_reports": len(reports),
        "requested_fixtures": len(fixture_ids),
        "missing_cached_odds_payloads": missing_payloads,
        "family_status_counts": family_counts,
        "reports": reports,
        "policy": {
            "api_calls_added": 0,
            "source": "Stage71J already-fetched unfiltered fixture odds cache",
            "signals_created": 0,
            "cross_market_best_bet": False,
            "probability_or_ev_authority": False,
        },
    }
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "OK",
        "fixture_reports": len(reports),
        "requested_fixtures": len(fixture_ids),
        "missing_cached_odds_payloads": len(missing_payloads),
        "api_calls_added": 0,
        "signals_created": 0,
        "output": str(path),
    }
