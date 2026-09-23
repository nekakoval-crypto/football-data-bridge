#!/usr/bin/env python3
"""PBK Item 13 ? Motivation Interaction Specialist V1.

Purpose:
Test whether motivation becomes useful only when combined with
strict no-lookahead prematch context.

This is NOT a standalone motivation probability model.

Development scope:
2019/20?2022/23 only.

The already-observed V1 historical holdout:
2023/24?2025/26
is explicitly excluded from development proof.

Preregistered interactions:
1. HIGH_PRESSURE_X_FORM_ALIGNMENT
2. HIGH_PRESSURE_X_SHORT_REST_DISADVANTAGE
3. HIGH_PRESSURE_X_LARGE_RANK_DISADVANTAGE
4. LATE_SURVIVAL_X_SHORT_REST

UNKNOWN is never converted to zero.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts import stage80_top5_motivation_market_research as mot
    from scripts import stage80_prematch_factor_research as prem
    from scripts import motivation_specialist_historical_validation as base
except ModuleNotFoundError:
    import stage80_top5_motivation_market_research as mot
    import stage80_prematch_factor_research as prem
    import motivation_specialist_historical_validation as base


VERSION = "PBK_MOTIVATION_INTERACTION_SPECIALIST_V1"

DEV_SEASONS = (
    "2019/2020",
    "2020/2021",
    "2021/2022",
    "2022/2023",
)

OBSERVED_V1_HOLDOUT = (
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

INTERACTIONS = (
    "HIGH_PRESSURE_X_FORM_ALIGNMENT",
    "HIGH_PRESSURE_X_SHORT_REST_DISADVANTAGE",
    "HIGH_PRESSURE_X_LARGE_RANK_DISADVANTAGE",
    "LATE_SURVIVAL_X_SHORT_REST",
)

MIN_TRAIN_ROWS = 2500
MIN_TEST_ROWS = 1200

MIN_ACTIVE_TRAIN_ROWS = 100
MIN_ACTIVE_TEST_ROWS = 40

L2 = 0.02
LEARNING_RATE = 0.08
ITERATIONS = 1800
SIGN_EPSILON = 1e-8


def side_value(value: Any) -> float | None:
    text = str(value or "").strip().upper()

    if text == "HOME_ONLY":
        return 1.0

    if text == "AWAY_ONLY":
        return -1.0

    if text in {"BOTH", "NEITHER"}:
        return 0.0

    return None


def form_advantage_side(bucket: Any) -> float | None:
    text = str(bucket or "").strip().upper()

    if text in {
        "HOME_075PLUS_BETTER",
        "HOME_025_074_BETTER",
    }:
        return 1.0

    if text in {
        "AWAY_075PLUS_BETTER",
        "AWAY_025_074_BETTER",
    }:
        return -1.0

    if text == "BALANCED":
        return 0.0

    return None


def short_rest_disadvantage_side(
    bucket: Any,
) -> float | None:
    text = str(bucket or "").strip().upper()

    if text == "HOME_SHORT_ONLY":
        return 1.0

    if text == "AWAY_SHORT_ONLY":
        return -1.0

    if text in {
        "BOTH_SHORT_LE3D",
        "NEITHER_SHORT",
    }:
        return 0.0

    return None


def large_rank_disadvantage_side(
    bucket: Any,
) -> float | None:
    text = str(bucket or "").strip().upper()

    # Home 5+ better -> away is the clearly lower-ranked side.
    if text == "HOME_5PLUS_BETTER":
        return -1.0

    # Away 5+ better -> home is the clearly lower-ranked side.
    if text == "AWAY_5PLUS_BETTER":
        return 1.0

    if text in {
        "HOME_1_4_BETTER",
        "AWAY_1_4_BETTER",
        "EQUAL",
    }:
        return 0.0

    return None


def aligned_side(
    motivation_side: float | None,
    context_side: float | None,
) -> float | None:
    if (
        motivation_side is None
        or context_side is None
    ):
        return None

    if motivation_side == 0.0:
        return 0.0

    if context_side == motivation_side:
        return motivation_side

    return 0.0


def interaction_vector(
    motivation_row: dict[str, Any],
    prematch_row: dict[str, Any],
) -> list[float] | None:
    mb = mot.factor_buckets(
        motivation_row
    )

    pb = prem.factor_buckets(
        prematch_row
    )

    high_pressure = side_value(
        mb["HIGH_PRESSURE_SIDE"]
    )

    survival = side_value(
        mb["LATE_SURVIVAL_DANGER_SIDE"]
    )

    form_side = form_advantage_side(
        pb["FORM5_PPG_DIFF"]
    )

    short_rest_side = (
        short_rest_disadvantage_side(
            pb["SHORT_REST"]
        )
    )

    rank_disadvantage = (
        large_rank_disadvantage_side(
            pb["TABLE_RANK_DIFF"]
        )
    )

    values = [
        aligned_side(
            high_pressure,
            form_side,
        ),
        aligned_side(
            high_pressure,
            short_rest_side,
        ),
        aligned_side(
            high_pressure,
            rank_disadvantage,
        ),
        aligned_side(
            survival,
            short_rest_side,
        ),
    ]

    if any(
        value is None
        for value in values
    ):
        return None

    return [
        float(value)
        for value in values
    ]


def build_samples(
    matches_path: Path,
    motivation_path: Path,
    prematch_path: Path,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
]:
    matches = mot.read_csv(
        matches_path
    )

    motivation = mot.read_csv(
        motivation_path
    )

    prematch = prem.read_csv(
        prematch_path
    )

    enriched, mot_diag = mot.enrich(
        matches,
        motivation,
    )

    prematch_by_id = {
        str(
            row.get(
                "historical_match_id"
            ) or ""
        ).strip(): row
        for row in prematch
        if str(
            row.get(
                "historical_match_id"
            ) or ""
        ).strip()
    }

    if len(prematch_by_id) != 16111:
        raise ValueError(
            "prematch context must contain "
            "16111 unique match ids"
        )

    invalid_prematch_governance = sum(
        not prem.valid_context(row)
        for row in prematch
    )

    samples = []

    excluded_observed_holdout = 0
    excluded_no_market = 0
    excluded_unknown_interaction = 0
    missing_prematch = 0

    for row in enriched:
        season = str(
            row.get("season_label") or ""
        ).strip()

        if season in OBSERVED_V1_HOLDOUT:
            excluded_observed_holdout += 1
            continue

        if season not in DEV_SEASONS:
            continue

        if not row.get("_1x2_novig"):
            excluded_no_market += 1
            continue

        mid = str(
            row.get(
                "historical_match_id"
            ) or ""
        ).strip()

        context = prematch_by_id.get(mid)

        if context is None:
            missing_prematch += 1
            continue

        if not prem.valid_context(context):
            continue

        vector = interaction_vector(
            row,
            context,
        )

        if vector is None:
            excluded_unknown_interaction += 1
            continue

        outcome = str(
            row.get("_result") or ""
        ).strip().upper()

        if outcome not in base.CLASSES:
            continue

        samples.append({
            "historical_match_id": mid,
            "season": season,
            "league": str(
                row.get("league_code") or ""
            ).strip(),
            "market": tuple(
                float(value)
                for value
                in row["_1x2_novig"]
            ),
            "features": vector,
            "outcome": outcome,
        })

    seasons = tuple(sorted({
        row["season"]
        for row in samples
    }))

    if seasons != DEV_SEASONS:
        raise ValueError(
            f"development season scope drift: {seasons}"
        )

    return samples, {
        **mot_diag,
        "prematch_rows": len(prematch),
        "prematch_unique_ids": (
            len(prematch_by_id)
        ),
        "invalid_prematch_governance_rows": (
            invalid_prematch_governance
        ),
        "development_rows": len(samples),
        "excluded_observed_v1_holdout_before_metrics": (
            excluded_observed_holdout
        ),
        "excluded_dev_no_closing_market": (
            excluded_no_market
        ),
        "excluded_unknown_interaction": (
            excluded_unknown_interaction
        ),
        "missing_prematch_context": (
            missing_prematch
        ),
        "observed_v1_holdout_reused_as_proof": False,
    }


def project_feature(
    rows: list[dict[str, Any]],
    index: int,
) -> list[dict[str, Any]]:
    result = []

    for row in rows:
        clone = dict(row)
        clone["features"] = [
            float(
                row["features"][index]
            )
        ]
        result.append(clone)

    return result


def active_rows(
    rows: list[dict[str, Any]],
) -> int:
    return sum(
        abs(float(row["features"][0]))
        > 0.0
        for row in rows
    )


def fit_single(
    rows: list[dict[str, Any]],
) -> float:
    beta = [0.0]
    n = len(rows)

    if not n:
        raise ValueError(
            "empty interaction train sample"
        )

    for _ in range(ITERATIONS):
        gradient = 0.0

        for row in rows:
            probability = (
                base.challenger_probabilities(
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
                - probability[0]
                + probability[2]
            )

            gradient += (
                row["features"][0]
                * error
            )

        gradient /= n
        gradient -= (
            L2 * beta[0]
        )

        beta[0] += (
            LEARNING_RATE
            * gradient
        )

        beta[0] = max(
            -2.0,
            min(2.0, beta[0]),
        )

    return beta[0]


def sign(value: float) -> str:
    if value > SIGN_EPSILON:
        return "POSITIVE"

    if value < -SIGN_EPSILON:
        return "NEGATIVE"

    return "ZERO"


def evaluate(
    rows: list[dict[str, Any]],
    beta: float,
) -> dict[str, Any]:
    return base.evaluate(
        rows,
        [beta],
    )


def split_fold(
    rows: list[dict[str, Any]],
    contract: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    train = [
        row
        for row in rows
        if row["season"]
        in contract["train"]
    ]

    test = [
        row
        for row in rows
        if row["season"]
        == contract["test"]
    ]

    return train, test


def develop_interaction(
    rows: list[dict[str, Any]],
    index: int,
    name: str,
) -> dict[str, Any]:
    folds = []

    for contract in FOLDS:
        train, test = split_fold(
            rows,
            contract,
        )

        train = project_feature(
            train,
            index,
        )

        test = project_feature(
            test,
            index,
        )

        active_train = active_rows(
            train
        )

        active_test = active_rows(
            test
        )

        sample_ready = (
            len(train) >= MIN_TRAIN_ROWS
            and len(test) >= MIN_TEST_ROWS
            and active_train
            >= MIN_ACTIVE_TRAIN_ROWS
            and active_test
            >= MIN_ACTIVE_TEST_ROWS
        )

        fold = {
            "fold": contract["fold"],
            "train_seasons": list(
                contract["train"]
            ),
            "test_season": (
                contract["test"]
            ),
            "train_rows": len(train),
            "test_rows": len(test),
            "active_train_rows": (
                active_train
            ),
            "active_test_rows": (
                active_test
            ),
            "sample_ready": sample_ready,
        }

        if not sample_ready:
            folds.append(fold)
            continue

        beta = fit_single(
            train
        )

        test_metrics = evaluate(
            test,
            beta,
        )

        fold.update({
            "beta": beta,
            "beta_sign": sign(beta),
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

        folds.append(fold)

    ready = all(
        fold["sample_ready"]
        for fold in folds
    )

    signs = [
        fold.get("beta_sign")
        for fold in folds
        if fold["sample_ready"]
    ]

    sign_stable = (
        ready
        and len(set(signs)) == 1
        and signs[0]
        in {"POSITIVE", "NEGATIVE"}
    )

    brier_both = (
        ready
        and all(
            fold.get(
                "brier_improved"
            ) is True
            for fold in folds
        )
    )

    logloss_both = (
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
        and brier_both
        and logloss_both
    )

    return {
        "interaction": name,
        "index": index,
        "folds": folds,
        "sample_ready_all_folds": ready,
        "coefficient_sign_stable": (
            sign_stable
        ),
        "brier_improved_all_folds": (
            brier_both
        ),
        "logloss_improved_all_folds": (
            logloss_both
        ),
        "selected_for_forward_candidate": (
            selected
        ),
    }


def fit_selected(
    rows: list[dict[str, Any]],
    indexes: list[int],
) -> list[float]:
    if not indexes:
        return []

    projected = []

    for row in rows:
        clone = dict(row)
        clone["features"] = [
            row["features"][index]
            for index in indexes
        ]
        projected.append(clone)

    beta = [
        0.0
        for _ in indexes
    ]

    n = len(projected)

    for _ in range(ITERATIONS):
        gradient = [
            0.0
            for _ in beta
        ]

        for row in projected:
            probability = (
                base.challenger_probabilities(
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
                - probability[0]
                + probability[2]
            )

            for idx, feature in enumerate(
                row["features"]
            ):
                gradient[idx] += (
                    feature * error
                )

        for idx in range(len(beta)):
            gradient[idx] /= n
            gradient[idx] -= (
                L2 * beta[idx]
            )

            beta[idx] += (
                LEARNING_RATE
                * gradient[idx]
            )

            beta[idx] = max(
                -2.0,
                min(2.0, beta[idx]),
            )

    return beta


def run(
    matches_path: Path,
    motivation_path: Path,
    prematch_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    rows, diagnostics = (
        build_samples(
            matches_path,
            motivation_path,
            prematch_path,
        )
    )

    screens = [
        develop_interaction(
            rows,
            index,
            name,
        )
        for index, name
        in enumerate(INTERACTIONS)
    ]

    selected = [
        row
        for row in screens
        if row[
            "selected_for_forward_candidate"
        ]
    ]

    indexes = [
        int(row["index"])
        for row in selected
    ]

    names = [
        row["interaction"]
        for row in selected
    ]

    beta = fit_selected(
        rows,
        indexes,
    )

    created = bool(names)

    status = (
        "FROZEN_FORWARD_INTERACTION_CANDIDATE_READY"
        if created
        else "REJECTED_DEVELOPMENT_NO_STABLE_INTERACTIONS"
    )

    result = {
        "version": VERSION,
        "status": status,
        "development_scope": {
            "development_seasons": list(
                DEV_SEASONS
            ),
            "observed_v1_holdout": list(
                OBSERVED_V1_HOLDOUT
            ),
            "observed_v1_holdout_reused_as_proof": False,
            "folds": [
                {
                    "fold": item["fold"],
                    "train": list(
                        item["train"]
                    ),
                    "test": item["test"],
                }
                for item in FOLDS
            ],
        },
        "preregistered_interactions": list(
            INTERACTIONS
        ),
        "interaction_screen": screens,
        "selected_interactions": names,
        "frozen_candidate": {
            "created": created,
            "formula": (
                "softmax(log(p_market_H)+z, "
                "log(p_market_D), "
                "log(p_market_A)-z)"
            ),
            "interactions": names,
            "beta": {
                name: beta[index]
                for index, name
                in enumerate(names)
            },
            "development_rows": len(
                rows
            ),
            "parameters_may_change_after_freeze": False,
        },
        "diagnostics": diagnostics,
        "authorization": {
            "development_complete": True,
            "forward_review_allowed": created,
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
            "unknown_not_zero": True,
            "historical_development_is_not_forward_validation": True,
            "standalone_motivation_models_v1_v2_remain_rejected": True,
            "old_holdout_not_reused_as_fresh_proof": True,
            "forward_evidence_required_for_any_later_authorization": True,
        },
    }

    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return result


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--matches",
        required=True,
    )

    parser.add_argument(
        "--motivation",
        required=True,
    )

    parser.add_argument(
        "--prematch",
        required=True,
    )

    parser.add_argument(
        "--out",
        required=True,
    )

    args = parser.parse_args()

    result = run(
        Path(args.matches),
        Path(args.motivation),
        Path(args.prematch),
        Path(args.out),
    )

    print(json.dumps({
        "status": result["status"],
        "development_rows": result[
            "diagnostics"
        ]["development_rows"],
        "selected_interactions": result[
            "selected_interactions"
        ],
        "frozen_beta": result[
            "frozen_candidate"
        ]["beta"],
        "old_holdout_reused": result[
            "development_scope"
        ][
            "observed_v1_holdout_reused_as_proof"
        ],
        "forward_review_allowed": result[
            "authorization"
        ]["forward_review_allowed"],
        "predictive_authority": result[
            "authorization"
        ]["predictive_authority"],
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
