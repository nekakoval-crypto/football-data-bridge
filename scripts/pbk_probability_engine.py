#!/usr/bin/env python3
"""PBK Probability Engine v1.

Consumes Full Market Scanner rows and attaches market-implied probability
semantics to every exact market/line/selection. Official PBK probability,
fair odds, Edge and EV are emitted only when an exact independently validated
context exists. Today that means frozen Stage75 R1/R2/R3 predictions only.

Generic 1X2 v1 may be exposed as a research candidate only from its own frozen
forward journal; it is never promoted to official P_PBK or value authority here.
No provider/API calls are made.
"""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFG = ROOT / "config" / "pbk_probability_engine.json"


def num(value: Any) -> float | None:
    try:
        result = float(str(value).strip())
        return result if math.isfinite(result) else None
    except Exception:
        return None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def implied(price: Any) -> float | None:
    value = num(price)
    return None if value is None or value <= 1.0 else 1.0 / value


def is_integer_line(line: Any) -> bool:
    value = num(line)
    return value is not None and abs(value - round(value)) <= 1e-9


def is_half_line(line: Any) -> bool:
    value = num(line)
    if value is None:
        return False
    doubled = value * 2.0
    return abs(doubled - round(doubled)) <= 1e-9 and not is_integer_line(value)


def selection_from_prediction(value: Any) -> str | None:
    token = str(value or "").strip().upper()
    if token in {"HOME", "H", "P1", "П1", "1"}:
        return "P1"
    if token in {"DRAW", "D", "X", "Х"}:
        return "X"
    if token in {"AWAY", "A", "P2", "П2", "2"}:
        return "P2"
    return None


def _reference_probability_pair(rows: list[dict[str, Any]], row: dict[str, Any]) -> tuple[float | None, str]:
    family = str(row.get("market_family") or "")
    selection = str(row.get("selection") or "")
    line = num(row.get("line"))
    price = num(row.get("reference_price"))
    if price is None or price <= 1.0:
        return None, "NO_REFERENCE_PRICE"

    if family == "DOUBLE_CHANCE":
        return None, "RAW_IMPLIED_ONLY_OVERLAPPING_OUTCOMES"
    if family == "ASIAN_HANDICAP" and str(row.get("availability_status") or "").startswith("BLOCKED_"):
        return None, "BLOCKED_EXECUTION_LINE_RAW_ONLY"

    def valid_price(candidate: dict[str, Any]) -> float | None:
        value = num(candidate.get("reference_price"))
        return value if value is not None and value > 1.0 else None

    group: list[dict[str, Any]] = []
    status = "RAW_IMPLIED_ONLY"

    if family == "MATCH_RESULT_1X2":
        group = [x for x in rows if x.get("market_family") == family and x.get("selection_label") in {"P1", "X", "P2"}]
        if {x.get("selection_label") for x in group if valid_price(x)} == {"P1", "X", "P2"}:
            status = "NO_VIG_VALID_EXHAUSTIVE"
        else:
            group = []
    elif family == "EUROPEAN_HANDICAP":
        group = [x for x in rows if x.get("market_family") == family and num(x.get("line")) == line]
        if {x.get("selection") for x in group if valid_price(x)} == {"H", "D", "A"}:
            status = "NO_VIG_VALID_EXHAUSTIVE"
        else:
            group = []
    elif family == "BTTS":
        group = [x for x in rows if x.get("market_family") == family and x.get("selection") in {"YES", "NO"}]
        if {x.get("selection") for x in group if valid_price(x)} == {"YES", "NO"}:
            status = "NO_VIG_VALID_EXHAUSTIVE"
        else:
            group = []
    elif family in {"MATCH_TOTAL", "TEAM_TOTAL_HOME", "TEAM_TOTAL_AWAY"}:
        group = [x for x in rows if x.get("market_family") == family and num(x.get("line")) == line]
        if {x.get("selection") for x in group if valid_price(x)} != {"O", "U"}:
            group = []
        elif is_half_line(line):
            status = "NO_VIG_VALID_EXHAUSTIVE"
        elif is_integer_line(line):
            status = "NO_VIG_CONDITIONAL_ON_NO_PUSH"
        else:
            return None, "RAW_IMPLIED_ONLY_SPLIT_LINE"
    elif family == "DRAW_NO_BET":
        group = [x for x in rows if x.get("market_family") == family and num(x.get("line")) == 0.0]
        if {x.get("selection") for x in group if valid_price(x)} == {"H", "A"}:
            status = "NO_VIG_CONDITIONAL_ON_NO_PUSH"
        else:
            group = []
    elif family == "ASIAN_HANDICAP":
        if line is None:
            return None, "RAW_IMPLIED_ONLY"
        opposite = "A" if selection == "H" else "H"
        counterpart = next(
            (
                x for x in rows
                if x.get("market_family") == family
                and x.get("selection") == opposite
                and num(x.get("line")) is not None
                and abs(float(num(x.get("line"))) + line) <= 1e-9
                and valid_price(x)
            ),
            None,
        )
        if counterpart is None:
            group = []
        else:
            group = [row, counterpart]
            if is_half_line(line):
                status = "NO_VIG_VALID_EXHAUSTIVE"
            elif is_integer_line(line):
                status = "NO_VIG_CONDITIONAL_ON_NO_PUSH"
            else:
                return None, "RAW_IMPLIED_ONLY_SPLIT_LINE"

    if not group:
        return None, "RAW_IMPLIED_ONLY_INCOMPLETE_COMPLEMENT"
    inv = [1.0 / float(valid_price(x)) for x in group if valid_price(x)]
    if len(inv) != len(group) or sum(inv) <= 0:
        return None, "RAW_IMPLIED_ONLY_INCOMPLETE_COMPLEMENT"
    return (1.0 / price) / sum(inv), status


def market_probability(rows: list[dict[str, Any]], row: dict[str, Any]) -> dict[str, Any]:
    raw = implied(row.get("reference_price"))
    no_vig, status = _reference_probability_pair(rows, row)
    chosen = no_vig if no_vig is not None else raw
    return {
        "p_market": chosen,
        "p_market_raw": raw,
        "p_market_no_vig": no_vig,
        "p_market_status": status,
        "p_market_source": row.get("reference_bookmaker") or "Bet365",
    }


def build_validated_prediction_index(
    predictions: list[dict[str, str]],
    engine_cfg: dict[str, Any],
    model_cfg: dict[str, Any],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    allowed = engine_cfg.get("validated_contexts") or {}
    models = model_cfg.get("models") or {}
    priority = {rule: i for i, rule in enumerate(engine_cfg.get("validated_context_priority") or [])}
    out: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in predictions:
        rule = str(row.get("rule") or "").strip()
        context = allowed.get(rule)
        model = models.get(rule)
        if not context or not model or model.get("gate") != "PASS":
            continue
        if str(row.get("status") or "").strip() != "FROZEN_PREMATCH":
            continue
        fixture_id = str(row.get("api_fixture_id") or "").strip()
        selection = selection_from_prediction(row.get("selection"))
        if not fixture_id or selection != context.get("selection_label"):
            continue
        p_pbk = num(row.get("p_pbk"))
        p_market = num(row.get("p_market_no_vig"))
        if p_pbk is None or p_market is None or not (0 < p_pbk < 1) or not (0 < p_market < 1):
            continue
        enriched = dict(row)
        enriched["selection_label"] = selection
        enriched["priority"] = priority.get(rule, 999)
        out.setdefault((fixture_id, selection), []).append(enriched)
    for key in out:
        out[key].sort(key=lambda x: (x["priority"], str(x.get("rule") or "")))
    return out


def build_generic_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for row in rows:
        fixture_id = str(row.get("fixture_id") or row.get("api_fixture_id") or "").strip()
        p_market = row.get("p_market") or {}
        p_m1 = row.get("p_m1") or {}
        if not fixture_id or not isinstance(p_market, dict) or not isinstance(p_m1, dict):
            continue
        if not all(num(p_m1.get(key)) is not None for key in ("H", "D", "A")):
            continue
        out[fixture_id] = row
    return out


def attach_probabilities(
    scanner_payload: dict[str, Any],
    predictions: list[dict[str, str]],
    model_cfg: dict[str, Any],
    engine_cfg: dict[str, Any],
    generic_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    prediction_index = build_validated_prediction_index(predictions, engine_cfg, model_cfg)
    generic_index = build_generic_index(generic_rows or [])
    reports_out = []
    counts: dict[str, int] = {}

    generic_map = {"P1": "H", "X": "D", "P2": "A"}
    for report in scanner_payload.get("reports", []) or []:
        fixture = dict(report.get("fixture") or {})
        fixture_id = str(fixture.get("api_fixture_id") or "").strip()
        source_options = list(report.get("options") or [])
        options_out = []
        for source in source_options:
            row = dict(source)
            row.update(market_probability(source_options, source))
            row.update({
                "probability_status": "NO_VALIDATED_MODEL",
                "validated_context": None,
                "matching_validated_contexts": [],
                "model_version": None,
                "p_market_model_input": None,
                "p_pbk": None,
                "fair_odds": None,
                "execution_implied_raw": implied(row.get("executable_price")),
                "edge_vs_model_market": None,
                "edge_vs_execution_implied": None,
                "ev": None,
                "generic_1x2_research_status": None,
                "p_pbk_research_candidate": None,
            })

            if row.get("market_family") == "MATCH_RESULT_1X2":
                generic = generic_index.get(fixture_id)
                cls = generic_map.get(str(row.get("selection_label") or ""))
                candidate = num((generic.get("p_m1") or {}).get(cls)) if generic and cls else None
                if candidate is not None:
                    row["generic_1x2_research_status"] = "FORWARD_REVIEW_REQUIRED_PER_LEAGUE"
                    row["p_pbk_research_candidate"] = candidate

            key = (fixture_id, str(row.get("selection_label") or ""))
            matches = prediction_index.get(key, []) if row.get("market_family") == "MATCH_RESULT_1X2" else []
            if matches:
                chosen = matches[0]
                p_pbk = num(chosen.get("p_pbk"))
                p_model_market = num(chosen.get("p_market_no_vig"))
                executable_price = num(row.get("executable_price")) if row.get("executable") else None
                execution_implied = implied(executable_price)
                row["probability_status"] = "VALIDATED_CANONICAL_CONTEXT"
                row["validated_context"] = chosen.get("rule")
                row["matching_validated_contexts"] = [m.get("rule") for m in matches]
                row["model_version"] = chosen.get("model_version")
                row["p_market_model_input"] = p_model_market
                row["p_pbk"] = p_pbk
                row["fair_odds"] = (1.0 / p_pbk) if p_pbk else None
                row["execution_implied_raw"] = execution_implied
                row["edge_vs_model_market"] = (p_pbk - p_model_market) if p_pbk is not None and p_model_market is not None else None
                row["edge_vs_execution_implied"] = (p_pbk - execution_implied) if p_pbk is not None and execution_implied is not None else None
                row["ev"] = (p_pbk * executable_price - 1.0) if p_pbk is not None and executable_price is not None else None

            counts[row["probability_status"]] = counts.get(row["probability_status"], 0) + 1
            options_out.append(row)

        reports_out.append({
            "fixture": fixture,
            "options": options_out,
            "coverage": report.get("coverage") or {},
        })

    return {
        "status": "OK",
        "engine_version": engine_cfg.get("version") or "PBK_PROBABILITY_ENGINE_V1",
        "authority": engine_cfg.get("authority") or "GOVERNED_ANALYTIC",
        "source_scanner_status": scanner_payload.get("status"),
        "fixture_reports": len(reports_out),
        "probability_status_counts": counts,
        "reports": reports_out,
        "policy": {
            "api_calls_added": 0,
            "official_p_pbk_requires_validated_exact_context": True,
            "generic_1x2_official_p_pbk_authorized": False,
            "cross_market_probability_transfer": False,
            "cross_line_probability_transfer": False,
            "cross_selection_probability_transfer": False,
            "signals_created": 0,
            "watch_created": 0,
            "stake_changes": False,
            "canonical_changes": False,
            "r1_r2_r3_changes": False,
            "ui_changes": False,
        },
    }


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def run(config_path: Path | str = DEFAULT_CFG) -> dict[str, Any]:
    engine_cfg = load_json(Path(config_path))
    inputs = engine_cfg.get("inputs") or {}
    scanner_path = Path(os.getenv("PBK_FULL_MARKET_SCANNER", str(resolve_path(inputs["full_market_scanner"]))))
    output_path = Path(os.getenv("PBK_PROBABILITY_ENGINE_OUT", str(resolve_path(engine_cfg["output"]))))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not scanner_path.exists():
        payload = {
            "status": "WAITING_FOR_FULL_MARKET_SCANNER",
            "engine_version": engine_cfg.get("version"),
            "fixture_reports": 0,
            "reports": [],
            "policy": {"api_calls_added": 0, "signals_created": 0, "stake_changes": False},
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    scanner_payload = load_json(scanner_path)
    predictions = read_csv(resolve_path(inputs["canonical_probability_predictions"]))
    model_cfg = load_json(resolve_path(inputs["canonical_model_config"]))
    generic_path_value = inputs.get("generic_1x2_forward_journal", "ops/generic_1x2_v1_forward_prematch.jsonl")
    generic_rows = read_jsonl(resolve_path(generic_path_value))
    result = attach_probabilities(scanner_payload, predictions, model_cfg, engine_cfg, generic_rows)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return result


def main() -> None:
    result = run()
    print(json.dumps({
        "status": result.get("status"),
        "engine_version": result.get("engine_version"),
        "fixture_reports": result.get("fixture_reports"),
        "probability_status_counts": result.get("probability_status_counts", {}),
        "api_calls_added": (result.get("policy") or {}).get("api_calls_added", 0),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
