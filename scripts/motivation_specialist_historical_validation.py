#!/usr/bin/env python3
"""PBK Item 13 ? Motivation Specialist Challenger V1.

Historical preregistration / holdout validation only.

Baseline:
    closing 1X2 market no-vig probability.

Challenger:
    market probability plus one directional motivation logit shift.

Important:
- no generic home-bias intercept;
- only preregistered no-lookahead motivation features;
- UNKNOWN rows are excluded, never treated as zero;
- source archive spans nine seasons, but closing 1X2 is available
  only for seven seasons beginning 2019/20;
- model is fit only on the first four closing-market seasons;
- the final three closing-market seasons are untouched holdout;
- no ROI/value/stake conclusion;
- even historical PASS only authorizes later forward review.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from scripts import stage80_top5_motivation_market_research as research
except ModuleNotFoundError:
    import stage80_top5_motivation_market_research as research


VERSION = "PBK_MOTIVATION_SPECIALIST_CHALLENGER_V1"

FEATURES = (
    "PRESSURE_ASYMMETRY",
    "HIGH_PRESSURE_SIDE",
    "LATE_TITLE_NEAR_3_SIDE",
    "LATE_SURVIVAL_DANGER_SIDE",
    "DRAW_TITLE_PATH_SIDE",
    "DRAW_SAFE_PATH_SIDE",
)

TRAIN_SEASONS = 4
HOLDOUT_SEASONS = 3

L2 = 0.02
LEARNING_RATE = 0.08
ITERATIONS = 1800

MIN_TRAIN_ROWS = 5000
MIN_HOLDOUT_ROWS = 2500
MAX_CLASS_CALIBRATION_ERROR = 0.03

CLASSES = ("H", "D", "A")


def fnum(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def side_value(value: Any) -> float | None:
    text = str(value or "").strip().upper()

    if text == "HOME_ONLY":
        return 1.0

    if text == "AWAY_ONLY":
        return -1.0

    if text in {"BOTH", "NEITHER"}:
        return 0.0

    return None


def asymmetry_value(value: Any) -> float | None:
    text = str(value or "").strip().upper()

    if text == "HOME_HIGHER":
        return 1.0

    if text == "AWAY_HIGHER":
        return -1.0

    if text == "BALANCED":
        return 0.0

    return None


def feature_vector(row: dict[str, Any]) -> list[float] | None:
    buckets = research.factor_buckets(row)

    values = [
        asymmetry_value(
            buckets["PRESSURE_ASYMMETRY"]
        ),
        side_value(
            buckets["HIGH_PRESSURE_SIDE"]
        ),
        side_value(
            buckets["LATE_TITLE_NEAR_3_SIDE"]
        ),
        side_value(
            buckets["LATE_SURVIVAL_DANGER_SIDE"]
        ),
        side_value(
            buckets["DRAW_TITLE_PATH_SIDE"]
        ),
        side_value(
            buckets["DRAW_SAFE_PATH_SIDE"]
        ),
    ]

    if any(value is None for value in values):
        return None

    return [float(value) for value in values]


def softmax(scores: list[float]) -> tuple[float, float, float]:
    maximum = max(scores)

    exp = [
        math.exp(score - maximum)
        for score in scores
    ]

    total = sum(exp)

    return tuple(
        value / total
        for value in exp
    )


def challenger_probabilities(
    market: list[float] | tuple[float, float, float],
    features: list[float],
    beta: list[float],
) -> tuple[float, float, float]:
    if len(features) != len(beta):
        raise ValueError("feature/beta length mismatch")

    if (
        len(market) != 3
        or any(
            value <= 0.0
            or value >= 1.0
            for value in market
        )
    ):
        raise ValueError("invalid market probability vector")

    z = sum(
        weight * feature
        for weight, feature
        in zip(beta, features)
    )

    # Motivation V1 is intentionally directional.
    # It can tilt HOME <-> AWAY but cannot invent a generic
    # home advantage or independently manipulate DRAW.
    scores = [
        math.log(market[0]) + z,
        math.log(market[1]),
        math.log(market[2]) - z,
    ]

    return softmax(scores)


def sample_row(row: dict[str, Any]) -> dict[str, Any] | None:
    market = row.get("_1x2_novig")

    if (
        not isinstance(market, list)
        or len(market) != 3
    ):
        return None

    features = feature_vector(row)

    if features is None:
        return None

    outcome = str(
        row.get("_result") or ""
    ).strip().upper()

    if outcome not in CLASSES:
        return None

    return {
        "historical_match_id": str(
            row.get("historical_match_id") or ""
        ),
        "season": str(
            row.get("season_label") or ""
        ),
        "league": str(
            row.get("league_code") or ""
        ),
        "market": tuple(
            float(value)
            for value in market
        ),
        "features": features,
        "outcome": outcome,
    }


def fit(
    rows: list[dict[str, Any]],
) -> list[float]:
    beta = [0.0] * len(FEATURES)

    n = len(rows)

    if n == 0:
        raise ValueError("empty training sample")

    for _ in range(ITERATIONS):
        gradient = [0.0] * len(beta)

        for row in rows:
            probabilities = challenger_probabilities(
                row["market"],
                row["features"],
                beta,
            )

            outcome = row["outcome"]

            # d log L / dz:
            # I(H) - I(A) - p(H) + p(A)
            error = (
                (1.0 if outcome == "H" else 0.0)
                - (1.0 if outcome == "A" else 0.0)
                - probabilities[0]
                + probabilities[2]
            )

            for index, feature in enumerate(
                row["features"]
            ):
                gradient[index] += (
                    feature * error
                )

        for index in range(len(beta)):
            gradient[index] /= n
            gradient[index] -= (
                L2 * beta[index]
            )

            beta[index] += (
                LEARNING_RATE
                * gradient[index]
            )

            # Absolute safety cap, not a tuning parameter.
            beta[index] = max(
                -2.0,
                min(2.0, beta[index]),
            )

    return beta


def brier(
    probabilities: tuple[float, float, float],
    outcome: str,
) -> float:
    return sum(
        (
            probabilities[index]
            - (
                1.0
                if outcome == label
                else 0.0
            )
        ) ** 2
        for index, label in enumerate(
            CLASSES
        )
    )


def logloss(
    probabilities: tuple[float, float, float],
    outcome: str,
) -> float:
    index = CLASSES.index(outcome)

    return -math.log(
        max(
            probabilities[index],
            1e-15,
        )
    )


def evaluate(
    rows: list[dict[str, Any]],
    beta: list[float],
) -> dict[str, Any]:
    if not rows:
        return {
            "rows": 0,
            "market_brier": None,
            "challenger_brier": None,
            "market_logloss": None,
            "challenger_logloss": None,
            "calibration": {},
            "outcomes": {},
        }

    market_brier = []
    challenger_brier = []
    market_logloss = []
    challenger_logloss = []

    sums = {
        label: 0.0
        for label in CLASSES
    }

    counts = Counter()

    for row in rows:
        market = tuple(
            row["market"]
        )

        challenger = challenger_probabilities(
            market,
            row["features"],
            beta,
        )

        outcome = row["outcome"]
        counts[outcome] += 1

        market_brier.append(
            brier(market, outcome)
        )

        challenger_brier.append(
            brier(challenger, outcome)
        )

        market_logloss.append(
            logloss(market, outcome)
        )

        challenger_logloss.append(
            logloss(challenger, outcome)
        )

        for index, label in enumerate(
            CLASSES
        ):
            sums[label] += challenger[index]

    n = len(rows)

    calibration = {}

    for label in CLASSES:
        mean_probability = (
            sums[label] / n
        )

        observed_rate = (
            counts[label] / n
        )

        calibration[label] = {
            "mean_probability": mean_probability,
            "observed_rate": observed_rate,
            "absolute_error": abs(
                mean_probability
                - observed_rate
            ),
        }

    return {
        "rows": n,
        "market_brier": (
            sum(market_brier) / n
        ),
        "challenger_brier": (
            sum(challenger_brier) / n
        ),
        "market_logloss": (
            sum(market_logloss) / n
        ),
        "challenger_logloss": (
            sum(challenger_logloss) / n
        ),
        "brier_delta": (
            sum(challenger_brier) / n
            - sum(market_brier) / n
        ),
        "logloss_delta": (
            sum(challenger_logloss) / n
            - sum(market_logloss) / n
        ),
        "calibration": calibration,
        "outcomes": {
            label: counts[label]
            for label in CLASSES
        },
    }


def season_split(
    rows: list[dict[str, Any]],
) -> tuple[
    list[str],
    list[str],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    seasons = sorted(
        {
            row["season"]
            for row in rows
            if row["season"]
        }
    )

    expected = (
        TRAIN_SEASONS
        + HOLDOUT_SEASONS
    )

    if len(seasons) != expected:
        raise ValueError(
            f"expected exactly {expected} seasons, "
            f"found {len(seasons)}: {seasons}"
        )

    train_seasons = seasons[
        :TRAIN_SEASONS
    ]

    holdout_seasons = seasons[
        TRAIN_SEASONS:
    ]

    train = [
        row
        for row in rows
        if row["season"]
        in train_seasons
    ]

    holdout = [
        row
        for row in rows
        if row["season"]
        in holdout_seasons
    ]

    return (
        train_seasons,
        holdout_seasons,
        train,
        holdout,
    )


def run(
    matches_path: Path,
    context_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    matches = research.read_csv(
        matches_path
    )

    contexts = research.read_csv(
        context_path
    )

    joined, diagnostics = research.enrich(
        matches,
        contexts,
    )

    samples = []

    excluded_unknown = 0
    excluded_no_market = 0

    for row in joined:
        if not row.get("_1x2_novig"):
            excluded_no_market += 1
            continue

        sample = sample_row(row)

        if sample is None:
            excluded_unknown += 1
            continue

        samples.append(sample)

    (
        train_seasons,
        holdout_seasons,
        train,
        holdout,
    ) = season_split(samples)

    if len(train) < MIN_TRAIN_ROWS:
        raise ValueError(
            f"training sample too small: {len(train)}"
        )

    if len(holdout) < MIN_HOLDOUT_ROWS:
        raise ValueError(
            f"holdout sample too small: {len(holdout)}"
        )

    beta = fit(train)

    train_metrics = evaluate(
        train,
        beta,
    )

    holdout_metrics = evaluate(
        holdout,
        beta,
    )

    season_metrics = {}

    improved_seasons = 0

    for season in holdout_seasons:
        season_rows = [
            row
            for row in holdout
            if row["season"] == season
        ]

        metrics = evaluate(
            season_rows,
            beta,
        )

        season_metrics[season] = metrics

        if (
            metrics["challenger_brier"]
            < metrics["market_brier"]
            and metrics["challenger_logloss"]
            < metrics["market_logloss"]
        ):
            improved_seasons += 1

    max_calibration_error = max(
        row["absolute_error"]
        for row in holdout_metrics[
            "calibration"
        ].values()
    )

    gates = {
        "train_sample": (
            len(train)
            >= MIN_TRAIN_ROWS
        ),
        "holdout_sample": (
            len(holdout)
            >= MIN_HOLDOUT_ROWS
        ),
        "holdout_brier_strict_improvement": (
            holdout_metrics[
                "challenger_brier"
            ]
            < holdout_metrics[
                "market_brier"
            ]
        ),
        "holdout_logloss_strict_improvement": (
            holdout_metrics[
                "challenger_logloss"
            ]
            < holdout_metrics[
                "market_logloss"
            ]
        ),
        "holdout_class_calibration": (
            max_calibration_error
            <= MAX_CLASS_CALIBRATION_ERROR
        ),
        "holdout_season_stability": (
            improved_seasons >= 2
        ),
        "no_unknown_as_zero": True,
        "no_posthoc_tuning": True,
        "no_intercept_home_bias": True,
    }

    passed = all(
        gates.values()
    )

    verdict = (
        "PASS_HISTORICAL_MOTIVATION_CHALLENGER_V1"
        if passed
        else "FAIL_HISTORICAL_MOTIVATION_CHALLENGER_V1"
    )

    payload = {
        "version": VERSION,
        "status": "COMPLETE",
        "final_verdict": verdict,
        "baseline": (
            "CLOSING_1X2_MARKET_NOVIG"
        ),
        "challenger": (
            "MARKET_OFFSET_PLUS_DIRECTIONAL_MOTIVATION_LOGIT_V1"
        ),
        "features": list(FEATURES),
        "feature_semantics": (
            "Directional HOME=+1, AWAY=-1, "
            "known symmetric/neutral=0. "
            "UNKNOWN observations are excluded."
        ),
        "fit_contract": {
            "archive_seasons_total": 9,
            "closing_market_seasons_total": 7,
            "closing_market_first_season": "2019/2020",
            "closing_market_availability_amendment": (
                "PREREGISTRATION_DATA_AVAILABILITY_ONLY_"
                "BEFORE_HOLDOUT_METRICS_SEEN"
            ),
            "train_seasons": train_seasons,
            "holdout_seasons": holdout_seasons,
            "l2": L2,
            "learning_rate": LEARNING_RATE,
            "iterations": ITERATIONS,
            "intercept": False,
            "parameters_fit_on_holdout": False,
            "posthoc_tuning": False,
        },
        "fit": {
            feature: beta[index]
            for index, feature
            in enumerate(FEATURES)
        },
        "samples": {
            "joined_rows": len(joined),
            "usable_model_rows": len(samples),
            "train_rows": len(train),
            "holdout_rows": len(holdout),
            "excluded_no_closing_1x2": (
                excluded_no_market
            ),
            "excluded_unknown_features": (
                excluded_unknown
            ),
        },
        "train_metrics": train_metrics,
        "holdout_metrics": holdout_metrics,
        "holdout_season_metrics": (
            season_metrics
        ),
        "holdout_seasons_with_both_metrics_improved": (
            improved_seasons
        ),
        "maximum_holdout_class_calibration_error": (
            max_calibration_error
        ),
        "gates": gates,
        "source_diagnostics": diagnostics,
        "authorization": {
            "historical_research_complete": True,
            "forward_review_required": passed,
            "predictive_authority": "NOT_AUTHORIZED",
            "production_integration_authorized": False,
            "operational_betting_authority": False,
            "probability_mutation_authorized": False,
            "eligibility_mutation_authorized": False,
            "stake_changes_authorized": False,
            "value_or_ev_authorized": False,
            "automatic_promotion": False,
        },
        "governance": {
            "research_only": True,
            "market_probability_is_baseline_not_pbk_opinion": True,
            "unknown_not_zero": True,
            "no_lookahead_context_required": True,
            "historical_holdout_is_not_forward_validation": True,
            "profitability_conclusion": False,
        },
    }

    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return payload


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--matches",
        required=True,
    )

    parser.add_argument(
        "--context",
        required=True,
    )

    parser.add_argument(
        "--out",
        required=True,
    )

    args = parser.parse_args()

    payload = run(
        Path(args.matches),
        Path(args.context),
        Path(args.out),
    )

    print(
        json.dumps(
            {
                "final_verdict": payload[
                    "final_verdict"
                ],
                "train_rows": payload[
                    "samples"
                ]["train_rows"],
                "holdout_rows": payload[
                    "samples"
                ]["holdout_rows"],
                "holdout_brier_market": payload[
                    "holdout_metrics"
                ]["market_brier"],
                "holdout_brier_challenger": payload[
                    "holdout_metrics"
                ]["challenger_brier"],
                "holdout_logloss_market": payload[
                    "holdout_metrics"
                ]["market_logloss"],
                "holdout_logloss_challenger": payload[
                    "holdout_metrics"
                ]["challenger_logloss"],
                "improved_holdout_seasons": payload[
                    "holdout_seasons_with_both_metrics_improved"
                ],
                "max_class_calibration_error": payload[
                    "maximum_holdout_class_calibration_error"
                ],
                "gates": payload["gates"],
                "predictive_authority": payload[
                    "authorization"
                ]["predictive_authority"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
