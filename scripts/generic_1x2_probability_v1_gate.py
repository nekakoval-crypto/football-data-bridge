#!/usr/bin/env python3
"""Fail-closed, pre-TEST readiness gate for Generic 1X2 Probability v1.

The scanner deliberately never obtains FTR from a TEST row.  It counts only
schema-valid, complete-price TEST rows and cannot produce TEST metrics.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "pbk_generic_1x2_probability_v1_gate.json"
CLASSES = ("H", "D", "A")


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_season(value: str) -> str:
    value = (value or "").strip().replace("-", "/")
    return value[:5] + value[-2:] if len(value) == 9 and value[4] == "/" else value


def market_probabilities(row: dict) -> tuple[float, float, float]:
    try:
        odds = tuple(float(row[key]) for key in ("B365H", "B365D", "B365A"))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("invalid B365 1X2 odds") from error
    if any(not math.isfinite(odd) or odd <= 1.0 for odd in odds):
        raise ValueError("invalid B365 1X2 odds")
    inverse = tuple(1.0 / odd for odd in odds)
    total = sum(inverse)
    if not math.isfinite(total) or total <= 0:
        raise ValueError("invalid B365 inverse-odds total")
    return tuple(value / total for value in inverse)


def shifted_probabilities(p: tuple[float, float, float], alpha_h: float, alpha_a: float) -> tuple[float, float, float]:
    if len(p) != 3 or any(not math.isfinite(x) or x <= 0.0 for x in p):
        raise ValueError("invalid input probabilities")
    scores = (math.log(p[0]) + alpha_h, math.log(p[1]), math.log(p[2]) + alpha_a)
    peak = max(scores)
    exponentials = tuple(math.exp(score - peak) for score in scores)
    total = sum(exponentials)
    result = tuple(value / total for value in exponentials)
    if any(not math.isfinite(x) or x <= 0.0 or x >= 1.0 for x in result):
        raise ValueError("invalid output probabilities")
    return result


def logloss(rows, alpha_h: float, alpha_a: float) -> float:
    if not rows:
        return math.inf
    value = 0.0
    for probabilities, outcome in rows:
        value -= math.log(shifted_probabilities(probabilities, alpha_h, alpha_a)[CLASSES.index(outcome)])
    return value / len(rows)


def fit_train(rows: list[tuple[tuple[float, float, float], str]]) -> dict:
    """Locked deterministic grid refinement from the PR #59 configuration."""
    if not rows:
        raise ValueError("TRAIN has no usable rows")
    candidates = []
    for h_index in range(41):
        for a_index in range(41):
            alpha_h, alpha_a = -1.0 + h_index * 0.05, -1.0 + a_index * 0.05
            candidates.append((logloss(rows, alpha_h, alpha_a), abs(alpha_h) + abs(alpha_a), alpha_h, alpha_a))
    best = min(candidates)
    for step in (0.01, 0.002):
        _, _, centre_h, centre_a = best
        candidates = []
        for delta_h in range(-5, 6):
            for delta_a in range(-5, 6):
                alpha_h, alpha_a = centre_h + delta_h * step, centre_a + delta_a * step
                candidates.append((logloss(rows, alpha_h, alpha_a), abs(alpha_h) + abs(alpha_a), alpha_h, alpha_a))
        best = min(candidates)
    return {"alpha_h": best[2], "alpha_d": 0.0, "alpha_a": best[3], "train_logloss": best[0]}


def check(status: bool, detail: dict) -> dict:
    return {"status": "PASS" if status else "FAIL", **detail}


def run_gate(source: Path, config: dict) -> dict:
    expected = config["expected_source"]
    checks: dict[str, dict] = {}
    if not source.exists():
        return failed_missing_source(source, config)
    fingerprint = sha256(source)
    checks["SOURCE_IDENTITY"] = check(fingerprint == expected["sha256"], {"sha256": fingerprint, "expected_sha256": expected["sha256"]})
    train_seasons, test_seasons = set(config["train_seasons"]), set(config["test_seasons"])
    split_ok = not (train_seasons & test_seasons)
    raw_rows = 0
    all_seasons, all_divisions, match_ids, source_urls = set(), set(), set(), set()
    duplicate_ids = 0
    missing_b365 = Counter()
    invalid_b365 = Counter()
    train_rows: list[tuple[tuple[float, float, float], str]] = []
    test_eligible_rows = 0
    probability_ok = True
    test_labels_read = False
    required_schema_ok = True
    schema_detail: dict = {}
    try:
        with source.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            missing_columns = sorted(set(config["required_columns"]) - set(fieldnames))
            required_schema_ok = not missing_columns and len(fieldnames) == expected["columns"]
            schema_detail = {"column_count": len(fieldnames), "expected_column_count": expected["columns"], "missing_columns": missing_columns}
            if not required_schema_ok:
                raise ValueError("required schema failed")
            for row in reader:
                raw_rows += 1
                season, division = normalize_season(row["season"]), row["Div"].strip()
                all_seasons.add(season); all_divisions.add(division); source_urls.add(row["source_url"].strip())
                match_id = row["match_id"].strip()
                if not match_id or match_id in match_ids:
                    duplicate_ids += 1
                match_ids.add(match_id)
                if season not in train_seasons | test_seasons:
                    continue
                prices = (row["B365H"].strip(), row["B365D"].strip(), row["B365A"].strip())
                if not all(prices):
                    missing_b365[season] += 1
                    continue
                try:
                    probabilities = market_probabilities(row)
                    shifted = shifted_probabilities(probabilities, 0.0, 0.0)
                    probability_ok = probability_ok and abs(sum(probabilities) - 1.0) <= config["probability_sum_tolerance"] and abs(sum(shifted) - 1.0) <= config["probability_sum_tolerance"]
                except ValueError:
                    invalid_b365[season] += 1
                    continue
                if season in test_seasons:
                    # Do not access row["FTR"] here: TEST remains blind.
                    test_eligible_rows += 1
                else:
                    outcome = row["FTR"].strip().upper()
                    if outcome in CLASSES:
                        train_rows.append((probabilities, outcome))
    except (OSError, csv.Error, ValueError) as error:
        checks["REQUIRED_SCHEMA"] = check(False, {"error": str(error), **schema_detail})
        return finalize(checks, config, source, fingerprint, raw_rows, test_labels_read)
    checks["SOURCE_COVERAGE"] = check(
        raw_rows == expected["rows"] and all_seasons == set(expected["seasons"]) and all_divisions == set(expected["divisions"]) and len(match_ids) == expected["rows"] and duplicate_ids == 0 and len(source_urls) == expected["unique_source_urls"],
        {"raw_rows": raw_rows, "expected_rows": expected["rows"], "seasons": sorted(all_seasons), "divisions": sorted(all_divisions), "unique_match_id": len(match_ids), "duplicate_or_missing_match_id": duplicate_ids, "unique_source_url": len(source_urls)},
    )
    checks["REQUIRED_SCHEMA"] = check(required_schema_ok, schema_detail)
    excluded = sum(missing_b365.values())
    checks["B365_FILTER"] = check(not invalid_b365 and all(season not in test_seasons for season in missing_b365), {"excluded_missing_b365": excluded, "excluded_by_season": dict(sorted(missing_b365.items())), "invalid_complete_b365_by_season": dict(sorted(invalid_b365.items())), "fallback_bookmaker": "FORBIDDEN"})
    checks["SPLIT_INTEGRITY"] = check(split_ok and len(train_rows) > 0 and test_eligible_rows > 0, {"train_seasons": sorted(train_seasons), "test_seasons": sorted(test_seasons), "overlap": sorted(train_seasons & test_seasons), "test_labels_read": test_labels_read})
    counts = Counter(outcome for _, outcome in train_rows)
    checks["CLASS_SUPPORT"] = check(all(counts[item] > 0 for item in CLASSES), {"train_outcomes": dict(counts)})
    checks["MARKET_PROBABILITY"] = check(probability_ok and not invalid_b365, {"formula": "B365 inverse-odds, normalized no-vig", "invalid_complete_prices": sum(invalid_b365.values())})
    try:
        fit_one, fit_two = fit_train(train_rows), fit_train(train_rows)
        deterministic = fit_one == fit_two
        checks["TRAIN_FIT_READINESS"] = check(True, {"usable_rows": len(train_rows), "fit": fit_one})
        checks["DETERMINISM"] = check(deterministic, {"first_fit": fit_one, "second_fit": fit_two})
        probability_guards = probability_ok and all(abs(sum(shifted_probabilities(p, fit_one["alpha_h"], fit_one["alpha_a"])) - 1.0) <= config["probability_sum_tolerance"] for p, _ in train_rows)
        checks["PROBABILITY_GUARDS"] = check(probability_guards, {"tolerance": config["probability_sum_tolerance"]})
    except ValueError as error:
        checks["TRAIN_FIT_READINESS"] = check(False, {"error": str(error)})
        checks["DETERMINISM"] = check(False, {"error": str(error)})
        checks["PROBABILITY_GUARDS"] = check(False, {"error": str(error)})
    allowed = set(config["allowed_feature_columns"])
    leakage_ok = allowed == {"B365H", "B365D", "B365A"} and "FTR" not in allowed and not test_labels_read
    checks["LEAKAGE/NO-LOOKAHEAD"] = check(leakage_ok, {"allowed_feature_columns": sorted(allowed), "test_labels_read": test_labels_read, "future_or_target_features": sorted(allowed - {"B365H", "B365D", "B365A"})})
    return finalize(checks, config, source, fingerprint, raw_rows, test_labels_read, excluded, len(train_rows), test_eligible_rows)


def finalize(checks, config, source, fingerprint, raw_rows, test_labels_read, excluded_b365=None, train_usable_rows=None, test_eligible_rows=None):
    overall = "PASS" if checks and all(item["status"] == "PASS" for item in checks.values()) and len(checks) == 11 else "FAIL"
    return {"gate": config["version"], "overall_status": overall, "research_status": "TEST_ALLOWED" if overall == "PASS" else "PREREGISTERED_DATA_REQUIRED", "source": {"path": str(source), "sha256": fingerprint, "raw_rows": raw_rows}, "excluded_b365_count": excluded_b365, "train_usable_rows": train_usable_rows, "test_eligible_rows": test_eligible_rows, "test_labels_read": test_labels_read, "test_results_reported": False, "gate_checks": checks, "fail_closed": True}


def failed_missing_source(source, config):
    return finalize({"SOURCE_IDENTITY": check(False, {"error": "DATA_REQUIRED: historical source not found"})}, config, source, None, 0, False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run_gate(args.input, load_config(args.config))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["overall_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

