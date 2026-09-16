#!/usr/bin/env python3
"""PBK Generic 1X2 Probability V1 historical evaluator.

Research-only. Fits only on preregistered TRAIN seasons and opens TEST once.
It never changes canonical eligibility, stakes or forward ledgers.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFG = ROOT / "config" / "pbk_generic_1x2_probability_v1.json"
CLASSES = ("H", "D", "A")


def load_cfg(path=DEFAULT_CFG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_season(value: str) -> str:
    s = str(value or "").strip().replace("-", "/")
    if len(s) == 9 and s[4] == "/":  # 2019/2020 -> 2019/20
        return s[:5] + s[-2:]
    return s


def market_probabilities(row: dict) -> tuple[float, float, float]:
    odds = [float(row[k]) for k in ("B365H", "B365D", "B365A")]
    if any((not math.isfinite(x) or x <= 1.0) for x in odds):
        raise ValueError("invalid 1X2 odds")
    inv = [1.0 / x for x in odds]
    total = sum(inv)
    return tuple(x / total for x in inv)


def shifted_probabilities(p: tuple[float, float, float], alpha_h: float, alpha_a: float):
    scores = [math.log(p[0]) + alpha_h, math.log(p[1]), math.log(p[2]) + alpha_a]
    m = max(scores)
    exp = [math.exp(x - m) for x in scores]
    z = sum(exp)
    return tuple(x / z for x in exp)


def multiclass_logloss(rows, alpha_h=0.0, alpha_a=0.0, shifted=False):
    if not rows:
        return math.inf
    loss = 0.0
    for p, y in rows:
        q = shifted_probabilities(p, alpha_h, alpha_a) if shifted else p
        idx = CLASSES.index(y)
        loss -= math.log(max(q[idx], 1e-15))
    return loss / len(rows)


def multiclass_brier(rows, alpha_h=0.0, alpha_a=0.0, shifted=False):
    if not rows:
        return math.inf
    total = 0.0
    for p, y in rows:
        q = shifted_probabilities(p, alpha_h, alpha_a) if shifted else p
        total += sum((q[i] - (1.0 if y == c else 0.0)) ** 2 for i, c in enumerate(CLASSES))
    return total / len(rows)


def class_calibration(rows, alpha_h=0.0, alpha_a=0.0, shifted=False):
    out = {}
    for i, c in enumerate(CLASSES):
        probs = []
        hits = 0
        for p, y in rows:
            q = shifted_probabilities(p, alpha_h, alpha_a) if shifted else p
            probs.append(q[i]); hits += int(y == c)
        mean_p = sum(probs) / len(probs)
        rate = hits / len(rows)
        out[c] = {"mean_probability": mean_p, "observed_rate": rate, "abs_error": abs(mean_p - rate), "outcomes": hits}
    return out


def fit_train(rows, cfg):
    opt = cfg["candidate_m1"]["optimizer"]
    lo, hi, step = float(opt["coarse_min"]), float(opt["coarse_max"]), float(opt["coarse_step"])
    best = (math.inf, 0.0, 0.0)
    n = int(round((hi - lo) / step))
    for ih in range(n + 1):
        ah = lo + ih * step
        for ia in range(n + 1):
            aa = lo + ia * step
            ll = multiclass_logloss(rows, ah, aa, True)
            if (ll, abs(ah) + abs(aa), ah, aa) < (best[0], abs(best[1]) + abs(best[2]), best[1], best[2]):
                best = (ll, ah, aa)
    radius = int(opt["refine_radius_steps"])
    for rstep in opt["refine_steps"]:
        center_h, center_a = best[1], best[2]
        candidates = []
        for dh in range(-radius, radius + 1):
            for da in range(-radius, radius + 1):
                ah = center_h + dh * float(rstep); aa = center_a + da * float(rstep)
                ll = multiclass_logloss(rows, ah, aa, True)
                candidates.append((ll, abs(ah) + abs(aa), ah, aa))
        chosen = min(candidates)
        best = (chosen[0], chosen[2], chosen[3])
    return {"alpha_h": best[1], "alpha_d": 0.0, "alpha_a": best[2], "train_logloss": best[0]}


def load_rows(path: Path, cfg: dict):
    required = set(cfg["dataset"]["required_columns"])
    allowed = set(cfg["dataset"]["allowed_divisions"])
    train_s = set(cfg["split"]["train_seasons"]); test_s = set(cfg["split"]["test_seasons"])
    train, test, rejected = [], [], Counter()
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing required columns: {sorted(missing)}")
        for row in reader:
            if row.get("Div") not in allowed:
                rejected["division"] += 1; continue
            season = normalize_season(row.get("season"))
            if season not in train_s | test_s:
                rejected["season"] += 1; continue
            y = str(row.get("FTR") or "").strip().upper()
            if y not in CLASSES:
                rejected["result"] += 1; continue
            try:
                p = market_probabilities(row)
            except (ValueError, TypeError, KeyError):
                rejected["price"] += 1; continue
            (train if season in train_s else test).append((p, y))
    return train, test, dict(rejected)


def evaluate(train, test, cfg):
    fit = fit_train(train, cfg)
    ah, aa = fit["alpha_h"], fit["alpha_a"]
    base_ll = multiclass_logloss(test); model_ll = multiclass_logloss(test, ah, aa, True)
    base_bs = multiclass_brier(test); model_bs = multiclass_brier(test, ah, aa, True)
    cal = class_calibration(test, ah, aa, True)
    gate = cfg["test_gate"]
    counts = Counter(y for _, y in test)
    checks = {
        "minimum_test_rows": len(test) >= int(gate["minimum_test_rows"]),
        "minimum_test_outcomes_per_class": all(counts[c] >= int(gate["minimum_test_outcomes_per_class"]) for c in CLASSES),
        "brier_strict_improvement": model_bs < base_bs,
        "logloss_strict_improvement": model_ll < base_ll,
        "class_calibration": all(cal[c]["abs_error"] <= float(gate["maximum_absolute_class_calibration_error"]) for c in CLASSES),
        "probability_sum": all(abs(sum(shifted_probabilities(p, ah, aa)) - 1.0) <= float(gate["probabilities_must_sum_to_one_tolerance"]) for p, _ in test),
    }
    return {
        "model_version": cfg["version"],
        "status": "PASS_HISTORICAL_PROBABILITY_GATE" if all(checks.values()) else "FAIL_HISTORICAL_PROBABILITY_GATE",
        "authority": "RESEARCH",
        "train_rows": len(train), "test_rows": len(test), "test_outcomes": dict(counts),
        "fit": fit,
        "test": {
            "m0_logloss": base_ll, "m1_logloss": model_ll,
            "m0_multiclass_brier": base_bs, "m1_multiclass_brier": model_bs,
            "m1_class_calibration": cal,
        },
        "gate_checks": checks,
        "canonical_rules_changed": False,
        "value_authorized": False,
        "stake_changes_authorized": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    cfg = load_cfg(args.config)
    if not args.input.exists():
        raise SystemExit(f"DATA_REQUIRED: historical source not found: {args.input}")
    train, test, rejected = load_rows(args.input, cfg)
    result = evaluate(train, test, cfg); result["rejected_rows"] = rejected
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

