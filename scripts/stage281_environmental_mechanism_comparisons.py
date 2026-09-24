#!/usr/bin/env python3
"""PBK #281 — preregistered environmental mechanism comparisons.

Consumes Stage276 durable expectation/environment research rows and evaluates
only comparisons frozen in config/pbk_environmental_mechanism_comparisons_v1.json.

This is research-only. Thresholds are fixed research bins, not scientific
truths. The script reports sample sufficiency and descriptive differences but
cannot create predictive/betting authority.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "pbk_environmental_mechanism_comparisons_v1.json"
INPUT = ROOT / "ops" / "environmental_expectation_deviation_research.csv"
OUTPUT = ROOT / "ops" / "environmental_mechanism_comparison_results.csv"
META = ROOT / "ops" / "stage281_environmental_mechanism_comparisons_last_run.json"

VERSION = "PBK_ENVIRONMENTAL_MECHANISM_COMPARISONS_V1"

OUTPUT_FIELDS = [
    "comparison_id","exposed_group","control_group",
    "exposed_n","control_n","sample_status",
    "mean_over25_residual_exposed","mean_over25_residual_control",
    "delta_over25_residual_exposed_minus_control",
    "expected_over_actual_under_exposed",
    "expected_under_actual_over_exposed",
    "expected_over_actual_under_control",
    "expected_under_actual_over_control",
    "goals_total_delta","shots_total_delta","shots_on_goal_total_delta",
    "shots_outsidebox_total_delta","goalkeeper_saves_total_delta",
    "corners_total_delta","passes_accuracy_mean_delta","expected_goals_total_delta",
    "causal_claim_authorized","predictive_authority","betting_authority",
    "probability_mutation","eligibility_mutation","stake_changes",
    "forward_journal_mutation","automatic_model_promotion",
    "projection_version",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")


def read_json(path: Path) -> dict[str, Any]:
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,dict):
        raise ValueError("config root must be object")
    return data


def read_csv(path: Path) -> list[dict[str,str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str,Any]]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=OUTPUT_FIELDS,extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def fnum(value: Any) -> float | None:
    try:
        x=float(str(value).strip())
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):
        return None


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}".rstrip("0").rstrip(".")


def validate_contract(cfg: dict[str,Any]) -> None:
    if cfg.get("research_id")!=VERSION:
        raise ValueError("research id drift")
    if cfg.get("status")!="PREREGISTERED_RESEARCH_ONLY":
        raise ValueError("status drift")
    if cfg.get("authority")!="RESEARCH":
        raise ValueError("authority drift")
    if cfg.get("primary_expectation_baseline")!="CLOSING_OU25_NO_VIG_PROBABILITY":
        raise ValueError("baseline drift")
    guards=cfg.get("interpretation_guards") or {}
    required=[
        "thresholds_are_research_bins_not_scientific_truth",
        "threshold_retargeting_after_results_forbidden",
        "single_match_causal_claim_forbidden",
        "multiple_testing_correction_required_before_formal_claim",
        "report_both_direction_and_null_results",
        "unknown_not_zero",
        "no_predictive_authority",
        "no_betting_authority",
        "no_probability_mutation",
        "no_eligibility_mutation",
        "no_value_or_ev",
        "no_stake_changes",
        "no_forward_journal_mutation",
        "no_automatic_model_promotion",
    ]
    for key in required:
        if guards.get(key) is not True:
            raise ValueError(f"guard drift: {key}")


def exposure_flags(row: dict[str,str]) -> set[str]:
    flags=set()

    temp=fnum(row.get("temperature_mean_c"))
    humidity=fnum(row.get("relative_humidity_mean_pct"))
    precip=fnum(row.get("precipitation_sum_mm"))
    snow=fnum(row.get("snowfall_sum_cm"))
    gust=fnum(row.get("wind_gust_max_kmh"))
    visibility=fnum(row.get("visibility_min_m"))
    code=fnum(row.get("weather_code_mode"))

    if temp is not None:
        if temp<=5.0:
            flags.add("THERMAL_COLD")
        if 12.0<=temp<24.0:
            flags.add("THERMAL_NEUTRAL")
        if temp>=30.0:
            flags.add("THERMAL_HOT")

    if temp is not None and humidity is not None and temp>=24.0 and humidity>=70.0:
        flags.add("HEAT_HUMIDITY")

    if precip is not None:
        if precip>=7.5:
            flags.add("HEAVY_PRECIPITATION")
        if precip<0.1:
            flags.add("DRY")

    if snow is not None and snow>0.0:
        flags.add("SNOW_ANY")

    if gust is not None:
        if gust>=40.0:
            flags.add("STRONG_GUST")
        if gust<20.0:
            flags.add("LOW_GUST")

    if visibility is not None:
        if visibility<5000.0:
            flags.add("LOW_VISIBILITY")
        if visibility>=10000.0:
            flags.add("NORMAL_VISIBILITY")

    if code is not None:
        code_i=int(code)
        if code_i in {95,96,99}:
            flags.add("THUNDERSTORM")
        else:
            flags.add("NO_THUNDERSTORM")

    return flags


def mean_metric(rows: list[dict[str,str]], field: str) -> float | None:
    vals=[fnum(r.get(field)) for r in rows]
    vals=[x for x in vals if x is not None]
    if not vals:
        return None
    return sum(vals)/len(vals)


def delta_metric(exposed: list[dict[str,str]], control: list[dict[str,str]], field: str) -> float | None:
    a=mean_metric(exposed,field)
    b=mean_metric(control,field)
    if a is None or b is None:
        return None
    return a-b


def count_deviation(rows: list[dict[str,str]], cls: str) -> int:
    return sum(str(r.get("total_expectation_deviation_class") or "")==cls for r in rows)


def sample_status(cfg: dict[str,Any], exposed_n: int, control_n: int) -> str:
    gates=cfg["sample_gates"]
    formal=gates["formal_review_ready"]
    desc=gates["descriptive_ready"]

    if exposed_n>=int(formal["min_exposed"]) and control_n>=int(formal["min_control"]):
        return "FORMAL_REVIEW_READY"
    if exposed_n>=int(desc["min_exposed"]) and control_n>=int(desc["min_control"]):
        return "DESCRIPTIVE_READY"
    return "INSUFFICIENT_SAMPLE"


def build_results(cfg: dict[str,Any], rows: list[dict[str,str]]) -> list[dict[str,Any]]:
    flagged=[(row,exposure_flags(row)) for row in rows]
    out=[]

    for comp in cfg.get("comparisons") or []:
        exposed_name=comp["exposed"]
        control_name=comp["control"]

        exposed=[row for row,flags in flagged if exposed_name in flags]
        control=[row for row,flags in flagged if control_name in flags]

        residual_delta=delta_metric(exposed,control,"over25_residual")

        rec={
            "comparison_id":comp["comparison_id"],
            "exposed_group":exposed_name,
            "control_group":control_name,
            "exposed_n":len(exposed),
            "control_n":len(control),
            "sample_status":sample_status(cfg,len(exposed),len(control)),
            "mean_over25_residual_exposed":fmt(mean_metric(exposed,"over25_residual")),
            "mean_over25_residual_control":fmt(mean_metric(control,"over25_residual")),
            "delta_over25_residual_exposed_minus_control":fmt(residual_delta),

            "expected_over_actual_under_exposed":count_deviation(exposed,"EXPECTED_OVER_ACTUAL_UNDER"),
            "expected_under_actual_over_exposed":count_deviation(exposed,"EXPECTED_UNDER_ACTUAL_OVER"),
            "expected_over_actual_under_control":count_deviation(control,"EXPECTED_OVER_ACTUAL_UNDER"),
            "expected_under_actual_over_control":count_deviation(control,"EXPECTED_UNDER_ACTUAL_OVER"),

            "goals_total_delta":fmt(delta_metric(exposed,control,"goals_total")),
            "shots_total_delta":fmt(delta_metric(exposed,control,"shots_total")),
            "shots_on_goal_total_delta":fmt(delta_metric(exposed,control,"shots_on_goal_total")),
            "shots_outsidebox_total_delta":fmt(delta_metric(exposed,control,"shots_outsidebox_total")),
            "goalkeeper_saves_total_delta":fmt(delta_metric(exposed,control,"goalkeeper_saves_total")),
            "corners_total_delta":fmt(delta_metric(exposed,control,"corners_total")),
            "passes_accuracy_mean_delta":fmt(delta_metric(exposed,control,"passes_accuracy_mean")),
            "expected_goals_total_delta":fmt(delta_metric(exposed,control,"expected_goals_total")),

            "causal_claim_authorized":"false",
            "predictive_authority":"NOT_AUTHORIZED",
            "betting_authority":"NOT_AUTHORIZED",
            "probability_mutation":"false",
            "eligibility_mutation":"false",
            "stake_changes":"false",
            "forward_journal_mutation":"false",
            "automatic_model_promotion":"false",
            "projection_version":VERSION,
        }
        out.append(rec)

    return out


def build_meta(cfg: dict[str,Any], input_rows: list[dict[str,str]], results: list[dict[str,Any]]) -> dict[str,Any]:
    statuses=Counter(r["sample_status"] for r in results)
    exposures=Counter()
    for row in input_rows:
        exposures.update(exposure_flags(row))

    return {
        "version":VERSION,
        "generated_at_utc":now_iso(),
        "status":"OK",
        "input_rows":len(input_rows),
        "comparison_count":len(results),
        "sample_status_counts":dict(sorted(statuses.items())),
        "exposure_counts":dict(sorted(exposures.items())),
        "descriptive_ready_comparisons":sum(r["sample_status"]=="DESCRIPTIVE_READY" for r in results),
        "formal_review_ready_comparisons":sum(r["sample_status"]=="FORMAL_REVIEW_READY" for r in results),
        "thresholds_are_research_bins_not_scientific_truth":True,
        "threshold_retargeting_after_results_forbidden":True,
        "report_both_direction_and_null_results":True,
        "multiple_testing_correction_required_before_formal_claim":True,
        "single_match_causal_claim_forbidden":True,
        "research_only":True,
        "predictive_authority":"NOT_AUTHORIZED",
        "operational_betting_authority":False,
        "automatic_model_promotion":False,
        "next_stage":(
            "Accumulate Stage276 rows. Review preregistered comparisons only when sample gates are met; "
            "any operational effect must validate separately on PREMATCH_FROZEN prospective evidence."
        ),
    }


def run(config_path: Path=CONFIG,input_path: Path=INPUT,output_path: Path=OUTPUT,meta_path: Path=META) -> dict[str,Any]:
    cfg=read_json(config_path)
    validate_contract(cfg)
    rows=read_csv(input_path)
    results=build_results(cfg,rows)
    write_csv(output_path,results)
    meta=build_meta(cfg,rows,results)
    meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(meta,ensure_ascii=False))
    return meta


if __name__=="__main__":
    run()
