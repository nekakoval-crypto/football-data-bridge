#!/usr/bin/env python3
"""PBK Item 13 ? Motivation Specialist V2 development.

V1 historical holdout has already been observed and may never be reused
as fresh independent proof.

V2 development scope is therefore locked to:
- 2019/2020
- 2020/2021
- 2021/2022
- 2022/2023

Development uses expanding walk-forward only:
Fold A:
    train 2019/20 + 2020/21
    test  2021/22
Fold B:
    train 2019/20 + 2020/21 + 2021/22
    test  2022/23

Each motivation feature is tested independently against closing-market
no-vig baseline. A feature may enter the frozen V2 candidate only if:
- both development folds have sufficient samples;
- Brier strictly improves in both folds;
- log-loss strictly improves in both folds;
- fitted coefficient sign is stable across folds;
- coefficient is non-zero in both folds.

This is development evidence only. It never grants predictive,
production, betting, probability, eligibility, value or stake authority.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

try:
    from scripts import stage80_top5_motivation_market_research as research
    from scripts import motivation_specialist_historical_validation as v1
except ModuleNotFoundError:
    import stage80_top5_motivation_market_research as research
    import motivation_specialist_historical_validation as v1


VERSION = "PBK_MOTIVATION_SPECIALIST_V2_DEVELOPMENT_V1"

DEV_SEASONS = (
    "2019/2020",
    "2020/2021",
    "2021/2022",
    "2022/2023",
)

V1_OBSERVED_HOLDOUT = (
    "2023/2024",
    "2024/2025",
    "2025/2026",
)

FOLDS = (
    {
        "fold": "DEV_FOLD_A",
        "train": (
            "2019/2020",
            "2020/2021",
        ),
        "test": "2021/2022",
    },
    {
        "fold": "DEV_FOLD_B",
        "train": (
            "2019/2020",
            "2020/2021",
            "2021/2022",
        ),
        "test": "2022/2023",
    },
)

FEATURES = v1.FEATURES

MIN_TRAIN_ROWS = 2500
MIN_TEST_ROWS = 1200

L2 = 0.02
LEARNING_RATE = 0.08
ITERATIONS = 1800

SIGN_EPSILON = 1e-8


def sample_rows(
    matches_path: Path,
    context_path: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
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

    rows = []
    excluded_no_market = 0
    excluded_unknown = 0
    excluded_observed_holdout = 0

    for row in joined:
        season = str(
            row.get("season_label") or ""
        ).strip()

        if season in V1_OBSERVED_HOLDOUT:
            excluded_observed_holdout += 1
            continue

        if season not in DEV_SEASONS:
            continue

        if not row.get("_1x2_novig"):
            excluded_no_market += 1
            continue

        sample = v1.sample_row(row)

        if sample is None:
            excluded_unknown += 1
            continue

        rows.append(sample)

    seasons = sorted({
        row["season"]
        for row in rows
    })

    if tuple(seasons) != DEV_SEASONS:
        raise ValueError(
            f"development season scope drift: {seasons}"
        )

    return rows, {
        **diagnostics,
        "development_rows": len(rows),
        "excluded_dev_no_closing_market": (
            excluded_no_market
        ),
        "excluded_dev_unknown_features": (
            excluded_unknown
        ),
        "observed_v1_holdout_rows_excluded_before_v2_metrics": (
            excluded_observed_holdout
        ),
        "v1_observed_holdout_reused_as_proof": False,
    }


def single_feature_rows(
    rows: list[dict[str, Any]],
    feature_index: int,
) -> list[dict[str, Any]]:
    result = []

    for row in rows:
        clone = dict(row)
        clone["features"] = [
            float(
                row["features"][
                    feature_index
                ]
            )
        ]
        result.append(clone)

    return result


def fit_single(
    rows: list[dict[str, Any]],
) -> float:
    beta = [0.0]
    n = len(rows)

    if not n:
        raise ValueError(
            "empty single-feature train sample"
        )

    for _ in range(ITERATIONS):
        gradient = 0.0

        for row in rows:
            probabilities = (
                v1.challenger_probabilities(
                    row["market"],
                    row["features"],
                    beta,
                )
            )

            outcome = row["outcome"]

            error = (
                (
                    1.0
                    if outcome == "H"
                    else 0.0
                )
                - (
                    1.0
                    if outcome == "A"
                    else 0.0
                )
                - probabilities[0]
                + probabilities[2]
            )

            gradient += (
                row["features"][0]
                * error
            )

        gradient /= n
        gradient -= L2 * beta[0]

        beta[0] += (
            LEARNING_RATE
            * gradient
        )

        beta[0] = max(
            -2.0,
            min(2.0, beta[0]),
        )

    return beta[0]


def evaluate_single(
    rows: list[dict[str, Any]],
    beta: float,
) -> dict[str, Any]:
    return v1.evaluate(
        rows,
        [beta],
    )


def sign(value: float) -> str:
    if value > SIGN_EPSILON:
        return "POSITIVE"

    if value < -SIGN_EPSILON:
        return "NEGATIVE"

    return "ZERO"


def fold_rows(
    rows: list[dict[str, Any]],
    train_seasons: tuple[str, ...],
    test_season: str,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    train = [
        row
        for row in rows
        if row["season"]
        in train_seasons
    ]

    test = [
        row
        for row in rows
        if row["season"]
        == test_season
    ]

    return train, test


def develop_feature(
    rows: list[dict[str, Any]],
    feature_index: int,
    feature_name: str,
) -> dict[str, Any]:
    folds = []

    for contract in FOLDS:
        train, test = fold_rows(
            rows,
            contract["train"],
            contract["test"],
        )

        train = single_feature_rows(
            train,
            feature_index,
        )

        test = single_feature_rows(
            test,
            feature_index,
        )

        sample_ready = (
            len(train) >= MIN_TRAIN_ROWS
            and len(test) >= MIN_TEST_ROWS
        )

        if not sample_ready:
            folds.append({
                "fold": contract["fold"],
                "train_seasons": list(
                    contract["train"]
                ),
                "test_season": contract[
                    "test"
                ],
                "train_rows": len(train),
                "test_rows": len(test),
                "sample_ready": False,
            })
            continue

        beta = fit_single(train)

        train_metrics = evaluate_single(
            train,
            beta,
        )

        test_metrics = evaluate_single(
            test,
            beta,
        )

        folds.append({
            "fold": contract["fold"],
            "train_seasons": list(
                contract["train"]
            ),
            "test_season": contract[
                "test"
            ],
            "train_rows": len(train),
            "test_rows": len(test),
            "sample_ready": True,
            "beta": beta,
            "beta_sign": sign(beta),
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
            "brier_improved": (
                test_metrics[
                    "challenger_brier"
                ]
                < test_metrics[
                    "market_brier"
                ]
            ),
            "logloss_improved": (
                test_metrics[
                    "challenger_logloss"
                ]
                < test_metrics[
                    "market_logloss"
                ]
            ),
        })

    ready = (
        len(folds) == len(FOLDS)
        and all(
            fold.get(
                "sample_ready"
            ) is True
            for fold in folds
        )
    )

    signs = [
        fold.get("beta_sign")
        for fold in folds
        if fold.get("sample_ready")
    ]

    sign_stable = (
        ready
        and len(set(signs)) == 1
        and signs[0]
        in {"POSITIVE", "NEGATIVE"}
    )

    all_brier = (
        ready
        and all(
            fold.get(
                "brier_improved"
            ) is True
            for fold in folds
        )
    )

    all_logloss = (
        ready
        and all(
            fold.get(
                "logloss_improved"
            ) is True
            for fold in folds
        )
    )

    selected = (
        ready
        and sign_stable
        and all_brier
        and all_logloss
    )

    return {
        "feature": feature_name,
        "feature_index": feature_index,
        "folds": folds,
        "sample_ready_all_folds": ready,
        "coefficient_sign_stable": (
            sign_stable
        ),
        "brier_improved_all_folds": (
            all_brier
        ),
        "logloss_improved_all_folds": (
            all_logloss
        ),
        "selected_for_frozen_v2": (
            selected
        ),
    }


def fit_selected(
    rows: list[dict[str, Any]],
    selected_indexes: list[int],
) -> list[float]:
    projected = []

    for row in rows:
        clone = dict(row)
        clone["features"] = [
            row["features"][index]
            for index
            in selected_indexes
        ]
        projected.append(clone)

    if not projected:
        return []

    beta = [
        0.0
        for _ in selected_indexes
    ]

    n = len(projected)

    for _ in range(ITERATIONS):
        gradient = [
            0.0
            for _ in beta
        ]

        for row in projected:
            probabilities = (
                v1.challenger_probabilities(
                    row["market"],
                    row["features"],
                    beta,
                )
            )

            outcome = row["outcome"]

            error = (
                (
                    1.0
                    if outcome == "H"
                    else 0.0
                )
                - (
                    1.0
                    if outcome == "A"
                    else 0.0
                )
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

            beta[index] = max(
                -2.0,
                min(2.0, beta[index]),
            )

    return beta


def run(
    matches_path: Path,
    context_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    rows, diagnostics = sample_rows(
        matches_path,
        context_path,
    )

    feature_results = [
        develop_feature(
            rows,
            index,
            feature,
        )
        for index, feature
        in enumerate(FEATURES)
    ]

    selected = [
        row
        for row in feature_results
        if row[
            "selected_for_frozen_v2"
        ]
    ]

    selected_indexes = [
        int(row["feature_index"])
        for row in selected
    ]

    selected_names = [
        row["feature"]
        for row in selected
    ]

    frozen_beta = fit_selected(
        rows,
        selected_indexes,
    )

    candidate_created = bool(
        selected_names
    )

    status = (
        "FROZEN_FORWARD_CANDIDATE_READY"
        if candidate_created
        else "REJECTED_DEVELOPMENT_NO_STABLE_FEATURES"
    )

    payload = {
        "version": VERSION,
        "status": status,
        "development_scope": {
            "seasons": list(
                DEV_SEASONS
            ),
            "folds": [
                {
                    "fold": row["fold"],
                    "train": list(
                        row["train"]
                    ),
                    "test": row["test"],
                }
                for row in FOLDS
            ],
            "v1_observed_holdout": list(
                V1_OBSERVED_HOLDOUT
            ),
            "v1_observed_holdout_reused_as_proof": False,
        },
        "baseline": (
            "CLOSING_1X2_MARKET_NOVIG"
        ),
        "candidate_formula": (
            "softmax(log(p_market_H)+z, "
            "log(p_market_D), "
            "log(p_market_A)-z)"
        ),
        "feature_screen": (
            feature_results
        ),
        "selected_features": (
            selected_names
        ),
        "frozen_candidate": {
            "created": candidate_created,
            "features": selected_names,
            "beta": {
                name: frozen_beta[index]
                for index, name
                in enumerate(
                    selected_names
                )
            },
            "training_seasons": list(
                DEV_SEASONS
            ),
            "training_rows": len(rows),
            "parameters_may_change_after_freeze": False,
        },
        "diagnostics": diagnostics,
        "authorization": {
            "development_complete": True,
            "forward_review_allowed": candidate_created,
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
            "historical_development_is_not_forward_validation": True,
            "old_v1_holdout_is_not_fresh_proof": True,
            "unknown_not_zero": True,
            "no_posthoc_rescue_on_v1_holdout": True,
            "forward_evidence_required_for_any_later_authorization": True,
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

    result = run(
        Path(args.matches),
        Path(args.context),
        Path(args.out),
    )

    print(
        json.dumps(
            {
                "status": result[
                    "status"
                ],
                "development_rows": result[
                    "diagnostics"
                ]["development_rows"],
                "selected_features": result[
                    "selected_features"
                ],
                "frozen_beta": result[
                    "frozen_candidate"
                ]["beta"],
                "v1_holdout_reused": result[
                    "development_scope"
                ][
                    "v1_observed_holdout_reused_as_proof"
                ],
                "forward_review_allowed": result[
                    "authorization"
                ]["forward_review_allowed"],
                "predictive_authority": result[
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
