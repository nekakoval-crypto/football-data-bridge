#!/usr/bin/env python3
"""PBK Value Engine v2.

Read-only governed classification/ranking layer over Probability Engine.

The arithmetic and descriptive rating thresholds are delegated to the canonical
PBK_CALC_V1 calculation contract. This module does not create probabilities,
signals, Stage WATCH rows, stakes, canonical promotions, Forward Journal events
or provider traffic.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from pbk_calculation_contract import CONTRACT_VERSION, evaluate_value

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
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


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
        "reference_bookmaker": row.get("reference_bookmaker"),
        "reference_price": row.get("reference_price"),
        "executable": bool(row.get("executable")),
        "executable_bookmaker": row.get("executable_bookmaker"),
        "executable_price": row.get("executable_price"),
        "p_market": row.get("p_market"),
        "p_market_status": row.get("p_market_status"),
        "p_pbk_research_candidate": candidate,
        "research_probability_status": status,
        "value_status": cfg["research_probability_policy"]["status"],
        "official_p_pbk": None,
        "fair_odds": None,
        "edge": None,
        "edge_pp": None,
        "execution_edge": None,
        "execution_edge_pp": None,
        "ev": None,
        "ev_pct": None,
        "tags": [],
        "official_ranking_eligible": False,
        "creates_signal": False,
        "creates_stage_watch": False,
        "stake_changes": False,
        "eligibility_mutation": False,
        "forward_journal_mutation": False,
    }


def _invalid_official(status: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "value_status": status,
        "official_ranking_eligible": False,
        "p_pbk": num(row.get("p_pbk")),
        "fair_odds": None,
        "p_market_current": num(row.get("p_market")),
        "p_market_status": row.get("p_market_status"),
        "p_market_model_input": num(row.get("p_market_model_input")),
        "edge": None,
        "edge_pp": None,
        "executable_price": None,
        "executable_bookmaker": None,
        "execution_implied_raw": None,
        "execution_edge": None,
        "execution_edge_pp": None,
        "ev": None,
        "ev_pct": None,
        "tags": [],
        "calculation_contract_version": CONTRACT_VERSION,
    }


def classify_official(row: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    p_pbk = num(row.get("p_pbk"))
    if p_pbk is None or not 0.0 < p_pbk < 1.0:
        return _invalid_official("INVALID_OFFICIAL_PROBABILITY", row)

    required_market_status = cfg.get("required_current_market_status")
    if required_market_status and row.get("p_market_status") != required_market_status:
        return _invalid_official("NO_VALID_CURRENT_MARKET_PROBABILITY", row)

    p_market = num(row.get("p_market"))
    if p_market is None or not 0.0 < p_market < 1.0:
        return _invalid_official("NO_VALID_CURRENT_MARKET_PROBABILITY", row)

    executable = bool(row.get("executable"))
    executable_price = num(row.get("executable_price")) if executable else None
    if executable_price is None or executable_price <= 1.0:
        executable = False
        executable_price = None

    value = evaluate_value(
        p_pbk,
        p_market,
        executable_price,
        executable=executable,
    )
    if value is None:
        return _invalid_official("INVALID_OFFICIAL_PROBABILITY", row)

    rating = value["rating"]
    if rating == "NO_VALUE":
        rating = "NO_VALUE_THRESHOLD" if executable else "NO_EXECUTABLE_PRICE"

    execution_implied = (1.0 / executable_price) if executable_price is not None else None
    execution_edge = (p_pbk - execution_implied) if execution_implied is not None else None
    eligible = rating in set(cfg["ranking"]["eligible_classes"])

    return {
        "value_status": rating,
        "official_ranking_eligible": eligible,
        "p_pbk": p_pbk,
        "fair_odds": 1.0 / p_pbk,
        "p_market_current": p_market,
        "p_market_status": row.get("p_market_status"),
        "p_market_model_input": num(row.get("p_market_model_input")),
        "edge": value["edge"],
        "edge_pp": value["edge_pp"],
        "executable_price": executable_price,
        "executable_bookmaker": row.get("executable_bookmaker") if executable_price is not None else None,
        "execution_implied_raw": execution_implied,
        "execution_edge": execution_edge,
        "execution_edge_pp": execution_edge * 100.0 if execution_edge is not None else None,
        "ev": value["ev"],
        "ev_pct": value["ev_pct"],
        "tags": list(value.get("tags") or []),
        "calculation_contract_version": value["contract_version"],
    }


def _rank_key(item: dict[str, Any], cfg: dict[str, Any]) -> tuple[Any, ...]:
    priority = {
        name: index
        for index, name in enumerate(cfg["ranking"]["class_priority"])
    }
    ev = num(item.get("ev"))
    edge = num(item.get("edge"))
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


def policy_payload(cfg: dict[str, Any]) -> dict[str, Any]:
    guardrails = cfg.get("guardrails") or {}
    return {
        "api_calls_added": 0,
        "calculation_contract_version": CONTRACT_VERSION,
        "classification_source_of_truth": "PBK_CALC_V1",
        "execution_edge_is_informational_only": True,
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
        "eligibility_mutation": False,
        "canonical_changes": False,
        "r1_r2_r3_changes": False,
        "forward_journal_mutation": False,
        "ui_changes": False,
        "configured_guardrails": guardrails,
    }


def build_value_engine(
    probability_payload: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    if probability_payload.get("status") != "OK":
        return {
            "status": "WAITING_FOR_PROBABILITY_ENGINE",
            "engine_version": cfg["version"],
            "authority": cfg.get("authority"),
            "source_probability_status": probability_payload.get("status"),
            "source_probability_engine": probability_payload.get("engine_version"),
            "fixture_reports": 0,
            "official_value_candidates": 0,
            "official_ranked_candidates": 0,
            "research_only_candidates": 0,
            "value_status_counts": {},
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
                "eligibility_mutation": False,
                "canonical_changes": False,
                "forward_journal_mutation": False,
            }
            official_rows.append(out)
            official_total += 1
            if out["official_ranking_eligible"]:
                ranked_total += 1
            counts[out["value_status"]] = counts.get(out["value_status"], 0) + 1

        official_rows.sort(key=lambda item: _rank_key(item, cfg))
        research_rows.sort(
            key=lambda item: (
                str(item.get("market_family") or ""),
                str(item.get("line") or ""),
                str(item.get("selection") or ""),
            )
        )
        ranked = [item for item in official_rows if item["official_ranking_eligible"]]
        best = (
            dict(ranked[0])
            if ranked and cfg["ranking"].get("best_official_value_per_fixture")
            else None
        )
        reports_out.append(
            {
                "fixture": fixture,
                "best_official_value": best,
                "official_candidates": official_rows,
                "research_only_candidates": research_rows,
            }
        )

    reports_out.sort(
        key=lambda report: (
            str((report.get("fixture") or {}).get("kickoff_utc") or ""),
            str((report.get("fixture") or {}).get("api_fixture_id") or ""),
        )
    )
    return {
        "status": "OK",
        "engine_version": cfg["version"],
        "authority": cfg.get("authority"),
        "source_probability_engine": probability_payload.get("engine_version"),
        "calculation_contract_version": CONTRACT_VERSION,
        "fixture_reports": len(reports_out),
        "official_value_candidates": official_total,
        "official_ranked_candidates": ranked_total,
        "research_only_candidates": research_total,
        "value_status_counts": counts,
        "reports": reports_out,
        "policy": policy_payload(cfg),
    }


def run(config_path: Path | str = DEFAULT_CFG) -> dict[str, Any]:
    cfg = load_json(Path(config_path))
    expected_contract = ((cfg.get("calculation_contract") or {}).get("version"))
    if expected_contract and expected_contract != CONTRACT_VERSION:
        raise RuntimeError(
            f"Value Engine expects {expected_contract}, runtime calculation contract is {CONTRACT_VERSION}"
        )

    input_path = Path(
        os.getenv("PBK_PROBABILITY_ENGINE", str(resolve_path(cfg["input"])))
    )
    output_path = Path(
        os.getenv("PBK_VALUE_ENGINE_OUT", str(resolve_path(cfg["output"])))
    )
    probability_payload = (
        load_json(input_path)
        if input_path.exists()
        else {"status": "MISSING_PROBABILITY_ENGINE", "reports": []}
    )
    result = build_value_engine(probability_payload, cfg)
    atomic_write_json(output_path, result)
    return result


def main() -> None:
    result = run()
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "engine_version": result.get("engine_version"),
                "calculation_contract_version": result.get(
                    "calculation_contract_version"
                )
                or (result.get("policy") or {}).get("calculation_contract_version"),
                "fixture_reports": result.get("fixture_reports"),
                "official_value_candidates": result.get("official_value_candidates"),
                "official_ranked_candidates": result.get("official_ranked_candidates"),
                "research_only_candidates": result.get("research_only_candidates"),
                "value_status_counts": result.get("value_status_counts", {}),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
