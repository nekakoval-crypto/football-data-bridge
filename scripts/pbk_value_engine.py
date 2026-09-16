#!/usr/bin/env python3
"""PBK Value Engine v2.

Consumes Probability Engine exact-market rows. Value metrics are emitted only
for rows carrying an official independently validated P_PBK. Research-only
probabilities (including Generic 1X2 during per-league forward review) are kept
visible but are excluded from official value classification and ranking.

This module never calls a provider and never creates bets, WATCH signals,
stakes, canonical promotions, or UI output.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFG = ROOT / "config" / "pbk_value_engine.json"


def num(value: Any) -> float | None:
    try:
        result = float(str(value).strip())
        return result if math.isfinite(result) else None
    except Exception:
        return None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def exact_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    family = str(row.get("market_family") or "")
    line = "" if row.get("line") is None else str(row.get("line"))
    selection = str(row.get("selection") or row.get("selection_label") or "")
    return family, line, selection


def research_only_row(row: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any] | None:
    candidate = num(row.get("p_pbk_research_candidate"))
    status = row.get("generic_1x2_research_status")
    if candidate is None and not status:
        return None
    return {
        "market_family": row.get("market_family"),
        "line": row.get("line"),
        "selection": row.get("selection"),
        "selection_label": row.get("selection_label"),
        "reference_price": row.get("reference_price"),
        "executable_price": row.get("executable_price"),
        "p_market": row.get("p_market"),
        "p_pbk_research_candidate": candidate,
        "research_probability_status": status,
        "value_status": cfg["research_probability_policy"]["status"],
        "official_p_pbk": None,
        "fair_odds": None,
        "edge": None,
        "ev": None,
        "official_ranking_eligible": False,
    }


def classify_official(row: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    p_pbk = num(row.get("p_pbk"))
    if p_pbk is None or not 0.0 < p_pbk < 1.0:
        return {
            "value_status": "INVALID_OFFICIAL_PROBABILITY",
            "official_ranking_eligible": False,
            "p_pbk": None,
            "fair_odds": None,
            "reference_edge": None,
            "execution_edge": None,
            "ev": None,
            "tags": [],
        }

    fair_odds = 1.0 / p_pbk
    current_market = num(row.get("p_market"))
    reference_edge = (p_pbk - current_market) if current_market is not None and 0.0 < current_market < 1.0 else None

    executable = bool(row.get("executable"))
    executable_price = num(row.get("executable_price")) if executable else None
    if executable_price is not None and executable_price <= 1.0:
        executable_price = None
    execution_implied = (1.0 / executable_price) if executable_price is not None else None
    execution_edge = (p_pbk - execution_implied) if execution_implied is not None else None
    ev = (p_pbk * executable_price - 1.0) if executable_price is not None else None

    strong = cfg["classifications"]["STRONG_VALUE"]
    watch = cfg["classifications"]["VALUE_WATCH"]
    disagree = cfg["classifications"]["MARKET_DISAGREEMENT"]
    high_prob = cfg["classifications"]["HIGH_PROB_LOW_VALUE"]

    if ev is not None and execution_edge is not None and ev >= float(strong["minimum_ev"]) and execution_edge >= float(strong["minimum_execution_edge"]):
        status = "STRONG_VALUE"
    elif ev is not None and execution_edge is not None and ev >= float(watch["minimum_ev"]) and execution_edge >= float(watch["minimum_execution_edge"]):
        status = "VALUE_WATCH"
    elif executable_price is None and reference_edge is not None and reference_edge >= float(disagree["minimum_reference_edge"]):
        status = "MARKET_DISAGREEMENT"
    elif ev is not None and p_pbk >= float(high_prob["minimum_p_pbk"]) and ev < float(high_prob["maximum_ev_exclusive"]):
        status = "HIGH_PROB_LOW_VALUE"
    elif executable_price is None:
        status = "NO_EXECUTABLE_PRICE"
    else:
        status = "NO_VALUE_THRESHOLD"

    tags: list[str] = []
    if status == cfg["longshot"]["requires_classification"] and executable_price is not None and executable_price >= float(cfg["longshot"]["minimum_executable_odds"]):
        tags.append("LONGSHOT_STRONG")

    ranking_eligible = status in set(cfg["ranking"]["eligible_classes"])
    return {
        "value_status": status,
        "official_ranking_eligible": ranking_eligible,
        "p_pbk": p_pbk,
        "fair_odds": fair_odds,
        "p_market_current": current_market,
        "p_market_model_input": num(row.get("p_market_model_input")),
        "reference_edge": reference_edge,
        "reference_edge_pp": reference_edge * 100.0 if reference_edge is not None else None,
        "executable_price": executable_price,
        "executable_bookmaker": row.get("executable_bookmaker") if executable_price is not None else None,
        "execution_implied_raw": execution_implied,
        "execution_edge": execution_edge,
        "execution_edge_pp": execution_edge * 100.0 if execution_edge is not None else None,
        "ev": ev,
        "ev_pct": ev * 100.0 if ev is not None else None,
        "tags": tags,
    }


def _rank_key(item: dict[str, Any], cfg: dict[str, Any]) -> tuple[Any, ...]:
    priority = {name: index for index, name in enumerate(cfg["ranking"]["class_priority"])}
    ev = num(item.get("ev"))
    edge = num(item.get("execution_edge"))
    p_pbk = num(item.get("p_pbk"))
    return (
        priority.get(str(item.get("value_status")), 999),
        -(ev if ev is not None else -1e99),
        -(edge if edge is not None else -1e99),
        -(p_pbk if p_pbk is not None else -1e99),
        str(item.get("market_family") or ""),
        str(item.get("line") or ""),
        str(item.get("selection") or ""),
    )


def build_value_engine(probability_payload: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    if probability_payload.get("status") != "OK":
        return {
            "status": "WAITING_FOR_PROBABILITY_ENGINE",
            "engine_version": cfg["version"],
            "source_probability_status": probability_payload.get("status"),
            "fixture_reports": 0,
            "official_value_candidates": 0,
            "official_ranked_candidates": 0,
            "research_only_candidates": 0,
            "reports": [],
            "policy": policy_payload(cfg),
        }

    official_status = cfg["official_probability_status"]
    reports_out: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    official_total = 0
    ranked_total = 0
    research_total = 0

    for report in probability_payload.get("reports", []) or []:
        fixture = dict(report.get("fixture") or {})
        official_rows: list[dict[str, Any]] = []
        research_rows: list[dict[str, Any]] = []

        for source in report.get("options", []) or []:
            row = dict(source)
            research = research_only_row(row, cfg)
            if research is not None:
                research_rows.append(research)
                research_total += 1

            if row.get("probability_status") != official_status:
                continue

            metrics = classify_official(row, cfg)
            out = {
                "market_family": row.get("market_family"),
                "line": row.get("line"),
                "selection": row.get("selection"),
                "selection_label": row.get("selection_label"),
                "availability_status": row.get("availability_status"),
                "reference_bookmaker": row.get("reference_bookmaker"),
                "reference_price": row.get("reference_price"),
                "validated_context": row.get("validated_context"),
                "matching_validated_contexts": row.get("matching_validated_contexts") or [],
                "model_version": row.get("model_version"),
                "probability_status": row.get("probability_status"),
                **metrics,
                "creates_signal": False,
                "creates_stage_watch": False,
                "stake_changes": False,
                "canonical_changes": False,
            }
            official_rows.append(out)
            official_total += 1
            if out["official_ranking_eligible"]:
                ranked_total += 1
            counts[out["value_status"]] = counts.get(out["value_status"], 0) + 1

        official_rows.sort(key=lambda item: _rank_key(item, cfg))
        ranked = [item for item in official_rows if item["official_ranking_eligible"]]
        best = dict(ranked[0]) if ranked and cfg["ranking"].get("best_official_value_per_fixture") else None
        reports_out.append({
            "fixture": fixture,
            "best_official_value": best,
            "official_candidates": official_rows,
            "research_only_candidates": research_rows,
        })

    reports_out.sort(key=lambda report: str((report.get("fixture") or {}).get("kickoff_utc") or ""))
    return {
        "status": "OK",
        "engine_version": cfg["version"],
        "authority": cfg["authority"],
        "source_probability_engine": probability_payload.get("engine_version"),
        "fixture_reports": len(reports_out),
        "official_value_candidates": official_total,
        "official_ranked_candidates": ranked_total,
        "research_only_candidates": research_total,
        "value_status_counts": counts,
        "reports": reports_out,
        "policy": policy_payload(cfg),
    }


def policy_payload(cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "api_calls_added": 0,
        "official_ranking_only": True,
        "no_value_without_official_p_pbk": True,
        "generic_1x2_official_value_authorized": False,
        "generic_1x2_official_ranking_authorized": False,
        "cross_market_probability_transfer": False,
        "cross_line_probability_transfer": False,
        "cross_selection_probability_transfer": False,
        "signals_created": 0,
        "stage_watch_created": 0,
        "stake_changes": False,
        "canonical_changes": False,
        "r1_r2_r3_changes": False,
        "ui_changes": False,
    }


def run(config_path: Path | str = DEFAULT_CFG) -> dict[str, Any]:
    cfg = load_json(Path(config_path))
    input_path = Path(os.getenv("PBK_PROBABILITY_ENGINE", str(resolve_path(cfg["input"]))))
    output_path = Path(os.getenv("PBK_VALUE_ENGINE_OUT", str(resolve_path(cfg["output"]))))
    if input_path.exists():
        probability_payload = load_json(input_path)
    else:
        probability_payload = {"status": "MISSING_PROBABILITY_ENGINE", "reports": []}
    result = build_value_engine(probability_payload, cfg)
    atomic_write_json(output_path, result)
    return result


def main() -> None:
    result = run()
    print(json.dumps({
        "status": result.get("status"),
        "engine_version": result.get("engine_version"),
        "fixture_reports": result.get("fixture_reports"),
        "official_value_candidates": result.get("official_value_candidates"),
        "official_ranked_candidates": result.get("official_ranked_candidates"),
        "research_only_candidates": result.get("research_only_candidates"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
