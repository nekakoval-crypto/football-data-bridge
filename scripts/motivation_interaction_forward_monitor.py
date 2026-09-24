#!/usr/bin/env python3
"""PBK Item 13 — frozen Motivation Interaction V1 prospective monitor.

The frozen config is the single source of truth for:
- frozen interactions and beta;
- prospective inputs;
- output journal names;
- forward sample gates;
- review thresholds;
- governance restrictions.

This monitor is research-only and can never automatically grant predictive,
betting, value, eligibility, R1/R2/R3, UI or stake authority.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "PBK_MOTIVATION_INTERACTION_FORWARD_MONITOR_V2"

ROOT = Path(__file__).resolve().parents[1]
OPS = Path(os.getenv("OPS_DIR", str(ROOT / "ops")))

DEFAULT_CONFIG = (
    ROOT
    / "config"
    / "pbk_motivation_interaction_v1_forward.json"
)

EXPECTED_RESEARCH_ID = (
    "PBK_MOTIVATION_INTERACTION_V1_FORWARD"
)
EXPECTED_MODEL_VERSION = (
    "PBK_MOTIVATION_INTERACTION_SPECIALIST_V1"
)

SELECTED = (
    "HIGH_PRESSURE_X_FORM_ALIGNMENT",
    "HIGH_PRESSURE_X_LARGE_RANK_DISADVANTAGE",
)

EXPECTED_BETA = {
    "HIGH_PRESSURE_X_FORM_ALIGNMENT":
        -0.08139028122268811,
    "HIGH_PRESSURE_X_LARGE_RANK_DISADVANTAGE":
        -0.04354603042978898,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_iso(value: Any) -> datetime | None:
    text = str(value or "").strip()

    if not text:
        return None

    try:
        parsed = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return None

    return parsed.astimezone(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(
            f"required JSON missing: {path}"
        )

    value = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"{path.name}: root must be object"
        )

    return value


def read_jsonl(
    path: Path,
) -> tuple[bytes, list[dict[str, Any]]]:
    if not path.exists():
        return b"", []

    raw = path.read_bytes()
    rows = []

    for line_number, line in enumerate(
        raw.decode("utf-8-sig").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        value = json.loads(line)

        if not isinstance(value, dict):
            raise ValueError(
                f"{path}:{line_number}: row must be object"
            )

        rows.append(value)

    ids = [
        str(row.get("event_id") or "")
        for row in rows
    ]

    if (
        any(not value for value in ids)
        or len(ids) != len(set(ids))
    ):
        raise ValueError(
            f"{path.name}: duplicate/invalid event_id"
        )

    return raw, rows


def atomic_append(
    path: Path,
    original: bytes,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    separator = (
        b"\n"
        if original
        and not original.endswith(b"\n")
        else b""
    )

    addition = b"".join(
        (
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        for row in rows
    )

    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    with tmp.open("wb") as handle:
        handle.write(
            original + separator + addition
        )
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(tmp, path)


def atomic_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    tmp.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(tmp, path)


def fingerprint(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def event_id(
    kind: str,
    fixture_id: str,
) -> str:
    material = (
        f"{VERSION}|{kind}|{fixture_id}"
    )

    return hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()[:32]


def ops_ref(
    value: Any,
    ops: Path,
) -> Path:
    text = str(value or "").strip()

    if not text:
        raise ValueError(
            "empty frozen contract path"
        )

    path = Path(text)

    if path.is_absolute():
        raise ValueError(
            "absolute path forbidden in frozen contract"
        )

    if ".." in path.parts:
        raise ValueError(
            "parent traversal forbidden in frozen contract"
        )

    # Config historically stores prospective inputs as ops/foo,
    # while outputs are frozen as basenames.
    if path.parts and path.parts[0] == "ops":
        path = Path(*path.parts[1:])

    if len(path.parts) != 1:
        raise ValueError(
            f"unexpected operational path: {text}"
        )

    return ops / path.name


def validate_contract(
    config: dict[str, Any],
) -> dict[str, Any]:
    if (
        config.get("research_id")
        != EXPECTED_RESEARCH_ID
    ):
        raise ValueError(
            "forward research_id drift"
        )

    if (
        config.get("model_version")
        != EXPECTED_MODEL_VERSION
    ):
        raise ValueError(
            "forward model_version drift"
        )

    if (
        config.get("status")
        != "FORWARD_REVIEW_CONTRACT"
    ):
        raise ValueError(
            "forward contract status drift"
        )

    if config.get("authority") != "RESEARCH":
        raise ValueError(
            "forward contract authority drift"
        )

    frozen = config.get("frozen_model") or {}

    if tuple(
        frozen.get("interactions") or []
    ) != SELECTED:
        raise ValueError(
            "frozen config interactions drift"
        )

    if frozen.get("refit_allowed") is not False:
        raise ValueError(
            "refit must stay forbidden"
        )

    if (
        frozen.get(
            "parameter_change_after_freeze"
        )
        is not False
    ):
        raise ValueError(
            "parameter mutation must stay forbidden"
        )

    beta = frozen.get("beta") or {}

    for name in SELECTED:
        try:
            value = float(beta[name])
        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"missing frozen beta: {name}"
            ) from exc

        if not math.isclose(
            value,
            EXPECTED_BETA[name],
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise ValueError(
                f"frozen config beta drift: {name}"
            )

    inputs = (
        config.get("prospective_inputs")
        or {}
    )

    if inputs.get("join_key") != "fixture_id":
        raise ValueError(
            "forward join key drift"
        )

    if (
        inputs.get("historical_backfill")
        is not False
    ):
        raise ValueError(
            "historical backfill must stay forbidden"
        )

    if (
        inputs.get(
            "first_frozen_observation_only"
        )
        is not True
    ):
        raise ValueError(
            "first frozen observation guard drift"
        )

    if (
        inputs.get(
            "observation_must_precede_kickoff"
        )
        is not True
    ):
        raise ValueError(
            "prematch timing guard drift"
        )

    scope = config.get("forward_scope") or {}

    if (
        scope.get("review_unit")
        != "ACTIVE_INTERACTION_OBSERVATION"
    ):
        raise ValueError(
            "forward review unit drift"
        )

    review = config.get("forward_review") or {}

    minimum = int(
        review.get(
            "minimum_active_settled_rows_for_formal_review",
            0,
        )
    )

    minimum_class = int(
        review.get(
            "minimum_outcomes_per_class",
            0,
        )
    )

    calibration = float(
        review.get(
            "maximum_absolute_class_calibration_error",
            -1,
        )
    )

    if minimum <= 0:
        raise ValueError(
            "invalid formal review sample gate"
        )

    if minimum_class <= 0:
        raise ValueError(
            "invalid class sample gate"
        )

    if calibration < 0.0:
        raise ValueError(
            "invalid calibration threshold"
        )

    if (
        review.get(
            "brier_strict_improvement_required"
        )
        is not True
    ):
        raise ValueError(
            "Brier gate drift"
        )

    if (
        review.get(
            "logloss_strict_improvement_required"
        )
        is not True
    ):
        raise ValueError(
            "logloss gate drift"
        )

    if (
        review.get(
            "interaction_direction_stability_required"
        )
        is not True
    ):
        raise ValueError(
            "direction stability gate drift"
        )

    if (
        review.get(
            "manual_governance_review_required"
        )
        is not True
    ):
        raise ValueError(
            "manual governance must remain required"
        )

    if (
        review.get(
            "automatic_canonical_promotion"
        )
        is not False
    ):
        raise ValueError(
            "automatic promotion must remain forbidden"
        )

    guards = config.get("guards") or {}

    required_false = (
        "creates_signal",
        "operational_betting_authority",
        "probability_mutation_authorized",
        "eligibility_mutation_authorized",
        "value_or_ev_authorized",
        "stake_changes_authorized",
        "r1_r2_r3_changes_authorized",
        "production_integration_authorized",
        "ui_integration_authorized",
    )

    for key in required_false:
        if guards.get(key) is not False:
            raise ValueError(
                f"guard must remain false: {key}"
            )

    required_true = (
        "unknown_not_zero",
        "no_lookahead",
        "prematch_frozen_required",
        "postmatch_labels_separate",
        "market_probability_is_baseline_not_pbk_opinion",
        "standalone_motivation_v1_rejected",
        "standalone_motivation_v2_rejected",
    )

    for key in required_true:
        if guards.get(key) is not True:
            raise ValueError(
                f"guard must remain true: {key}"
            )

    if (
        guards.get("predictive_authority")
        != "NOT_AUTHORIZED"
    ):
        raise ValueError(
            "predictive authority drift"
        )

    outputs = config.get("outputs") or {}

    for key in (
        "prematch_journal",
        "settlement_journal",
        "performance_report",
    ):
        value = str(
            outputs.get(key) or ""
        ).strip()

        if not value:
            raise ValueError(
                f"missing frozen output: {key}"
            )

        if (
            Path(value).is_absolute()
            or ".." in Path(value).parts
            or len(Path(value).parts) != 1
        ):
            raise ValueError(
                f"invalid frozen output: {key}"
            )

    return {
        "beta": {
            name: float(beta[name])
            for name in SELECTED
        },
        "formula": str(
            frozen.get("formula") or ""
        ),
        "inputs": inputs,
        "review": review,
        "scope": scope,
        "guards": guards,
        "outputs": outputs,
        "required_candidate_status": str(
            config.get(
                "required_candidate_status"
            )
            or ""
        ),
        "candidate_source": str(
            config.get(
                "frozen_candidate_source"
            )
            or ""
        ),
    }


def validate_spec(
    spec: dict[str, Any],
    contract: dict[str, Any],
) -> None:
    required_status = (
        contract["required_candidate_status"]
    )

    if (
        required_status
        and spec.get("status")
        != required_status
    ):
        raise ValueError(
            "frozen candidate status drift"
        )

    selected = tuple(
        spec.get("selected_interactions")
        or []
    )

    frozen = spec.get("frozen_candidate") or {}
    auth = spec.get("authorization") or {}

    if selected != SELECTED:
        raise ValueError(
            "specialist selected interactions drift"
        )

    if tuple(
        frozen.get("interactions") or []
    ) != SELECTED:
        raise ValueError(
            "specialist frozen interactions drift"
        )

    if (
        frozen.get(
            "parameters_may_change_after_freeze"
        )
        is not False
    ):
        raise ValueError(
            "specialist parameter guard drift"
        )

    if (
        auth.get("forward_review_allowed")
        is not True
    ):
        raise ValueError(
            "specialist forward review closed"
        )

    if (
        auth.get("predictive_authority")
        != "NOT_AUTHORIZED"
    ):
        raise ValueError(
            "specialist predictive authority drift"
        )

    spec_beta = frozen.get("beta") or {}

    for name in SELECTED:
        value = float(spec_beta[name])

        if not math.isclose(
            value,
            contract["beta"][name],
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise ValueError(
                f"config/spec beta mismatch: {name}"
            )


def pressure_side(
    payload: dict[str, Any],
) -> float | None:
    comparison = payload.get("comparison") or {}

    home = str(
        comparison.get("home_pressure")
        or ""
    ).strip().upper()

    away = str(
        comparison.get("away_pressure")
        or ""
    ).strip().upper()

    valid = {
        "HIGH",
        "MEDIUM",
        "LOW",
        "NONE_VERIFIED",
    }

    if home not in valid or away not in valid:
        return None

    if home == "HIGH" and away == "HIGH":
        return 0.0

    if home == "HIGH":
        return 1.0

    if away == "HIGH":
        return -1.0

    return 0.0


def form_ppg(value: Any) -> float | None:
    text = str(value or "").strip().upper()

    if len(text) < 5:
        return None

    last5 = text[-5:]

    if any(
        char not in {"W", "D", "L"}
        for char in last5
    ):
        return None

    points = sum(
        3 if char == "W"
        else 1 if char == "D"
        else 0
        for char in last5
    )

    return points / 5.0


def form_side(
    payload: dict[str, Any],
) -> float | None:
    home = (
        payload.get("home")
        or {}
    ).get("standings") or {}

    away = (
        payload.get("away")
        or {}
    ).get("standings") or {}

    hp = form_ppg(home.get("form"))
    ap = form_ppg(away.get("form"))

    if hp is None or ap is None:
        return None

    diff = hp - ap

    if diff >= 0.75:
        return 1.0

    if diff >= 0.25:
        return 1.0

    if diff > -0.25:
        return 0.0

    if diff > -0.75:
        return -1.0

    return -1.0


def rank_disadvantage_side(
    payload: dict[str, Any],
) -> float | None:
    home = (
        payload.get("home")
        or {}
    ).get("standings") or {}

    away = (
        payload.get("away")
        or {}
    ).get("standings") or {}

    try:
        hr = int(home["rank"])
        ar = int(away["rank"])
    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None

    diff = hr - ar

    if diff <= -5:
        return -1.0

    if diff >= 5:
        return 1.0

    return 0.0


def aligned(
    motivation: float | None,
    context: float | None,
) -> float | None:
    if motivation is None or context is None:
        return None

    if motivation == 0.0:
        return 0.0

    if context == motivation:
        return motivation

    return 0.0


def interactions(
    motivation_payload: dict[str, Any],
) -> dict[str, float] | None:
    pressure = pressure_side(
        motivation_payload
    )

    form = form_side(
        motivation_payload
    )

    rank = rank_disadvantage_side(
        motivation_payload
    )

    first = aligned(
        pressure,
        form,
    )

    second = aligned(
        pressure,
        rank,
    )

    if first is None or second is None:
        return None

    return {
        SELECTED[0]: float(first),
        SELECTED[1]: float(second),
    }


def active_interaction(
    values: dict[str, Any],
) -> bool:
    return any(
        abs(float(values.get(name) or 0.0))
        > 0.0
        for name in SELECTED
    )


def candidate_probability(
    market: dict[str, Any],
    features: dict[str, float],
    beta: dict[str, float],
) -> tuple[dict[str, float], float]:
    try:
        ph = float(market["H"])
        pd = float(market["D"])
        pa = float(market["A"])
    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "invalid frozen market probability"
        ) from exc

    if (
        min(ph, pd, pa) <= 0.0
        or not math.isclose(
            ph + pd + pa,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-6,
        )
    ):
        raise ValueError(
            "market probability vector invalid"
        )

    z = sum(
        beta[name] * features[name]
        for name in SELECTED
    )

    raw = {
        "H": math.log(ph) + z,
        "D": math.log(pd),
        "A": math.log(pa) - z,
    }

    top = max(raw.values())

    exp = {
        key: math.exp(value - top)
        for key, value in raw.items()
    }

    total = sum(exp.values())

    return (
        {
            key: value / total
            for key, value in exp.items()
        },
        z,
    )


def score(
    probability: dict[str, float],
    result: str,
) -> dict[str, float]:
    target = {
        "H": 1.0 if result == "H" else 0.0,
        "D": 1.0 if result == "D" else 0.0,
        "A": 1.0 if result == "A" else 0.0,
    }

    return {
        "brier": sum(
            (
                probability[key]
                - target[key]
            ) ** 2
            for key in ("H", "D", "A")
        ) / 3.0,
        "logloss": -math.log(
            max(
                probability[result],
                1e-15,
            )
        ),
    }


def mean(values: list[float]) -> float | None:
    if not values:
        return None

    return sum(values) / len(values)


def performance_report(
    contract: dict[str, Any],
    prematch_rows: list[dict[str, Any]],
    settlement_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    review = contract["review"]

    prematch_by_id = {
        str(row.get("event_id") or ""):
        row
        for row in prematch_rows
    }

    active_prematch = [
        row
        for row in prematch_rows
        if active_interaction(
            (
                row.get("payload")
                or {}
            ).get("interactions") or {}
        )
    ]

    active_settlements = []

    for row in settlement_rows:
        payload = row.get("payload") or {}

        prematch = prematch_by_id.get(
            str(
                payload.get(
                    "prematch_event_id"
                )
                or ""
            )
        )

        if prematch is None:
            continue

        values = (
            prematch.get("payload")
            or {}
        ).get("interactions") or {}

        if active_interaction(values):
            active_settlements.append(
                (prematch, row)
            )

    outcomes = Counter(
        str(
            (
                settlement.get("payload")
                or {}
            ).get("result")
            or ""
        )
        for _, settlement
        in active_settlements
    )

    n = len(active_settlements)

    market_brier = []
    candidate_brier = []
    market_logloss = []
    candidate_logloss = []

    candidate_probabilities = {
        "H": [],
        "D": [],
        "A": [],
    }

    hits = Counter()

    for prematch, settlement in active_settlements:
        pp = prematch.get("payload") or {}
        sp = settlement.get("payload") or {}

        result = str(
            sp.get("result") or ""
        )

        market = pp.get("p_market") or {}
        candidate = (
            pp.get(
                "p_frozen_interaction_candidate"
            )
            or {}
        )

        ms = score(market, result)
        cs = score(candidate, result)

        market_brier.append(ms["brier"])
        candidate_brier.append(cs["brier"])
        market_logloss.append(
            ms["logloss"]
        )
        candidate_logloss.append(
            cs["logloss"]
        )

        for cls in ("H", "D", "A"):
            candidate_probabilities[cls].append(
                float(candidate[cls])
            )

        hits[result] += 1

    avg_market_brier = mean(market_brier)
    avg_candidate_brier = mean(
        candidate_brier
    )
    avg_market_logloss = mean(
        market_logloss
    )
    avg_candidate_logloss = mean(
        candidate_logloss
    )

    calibration = {}

    for cls in ("H", "D", "A"):
        if not n:
            calibration[cls] = None
            continue

        predicted = mean(
            candidate_probabilities[cls]
        )

        observed = hits[cls] / n

        calibration[cls] = abs(
            float(predicted) - observed
        )

    calibration_values = [
        value
        for value in calibration.values()
        if value is not None
    ]

    max_calibration_error = (
        max(calibration_values)
        if calibration_values
        else None
    )

    minimum_rows = int(
        review[
            "minimum_active_settled_rows_for_formal_review"
        ]
    )

    minimum_class = int(
        review[
            "minimum_outcomes_per_class"
        ]
    )

    sample_ready = (
        n >= minimum_rows
        and all(
            outcomes[cls] >= minimum_class
            for cls in ("H", "D", "A")
        )
    )

    brier_improved = (
        sample_ready
        and avg_candidate_brier
        is not None
        and avg_market_brier
        is not None
        and avg_candidate_brier
        < avg_market_brier
    )

    logloss_improved = (
        sample_ready
        and avg_candidate_logloss
        is not None
        and avg_market_logloss
        is not None
        and avg_candidate_logloss
        < avg_market_logloss
    )

    calibration_passed = (
        sample_ready
        and max_calibration_error
        is not None
        and max_calibration_error
        <= float(
            review[
                "maximum_absolute_class_calibration_error"
            ]
        )
    )

    metric_gate_passed = (
        sample_ready
        and brier_improved
        and logloss_improved
        and calibration_passed
    )

    if not sample_ready:
        status = (
            "INSUFFICIENT_FORWARD_SAMPLE"
        )
    elif not metric_gate_passed:
        status = (
            "FORWARD_METRIC_GATE_FAILED"
        )
    else:
        status = (
            "READY_FOR_MANUAL_GOVERNANCE_REVIEW"
        )

    checkpoints = [
        int(value)
        for value in (
            review.get(
                "diagnostic_checkpoints_active_rows"
            )
            or []
        )
    ]

    return {
        "version": VERSION,
        "status": status,
        "review_unit":
            "ACTIVE_INTERACTION_OBSERVATION",
        "active_prematch_rows":
            len(active_prematch),
        "active_settled_rows": n,
        "outcomes": {
            cls: outcomes[cls]
            for cls in ("H", "D", "A")
        },
        "diagnostic_checkpoints": {
            str(value): (
                len(active_prematch)
                >= value
            )
            for value in checkpoints
        },
        "sample_gate": {
            "minimum_active_settled_rows":
                minimum_rows,
            "minimum_outcomes_per_class":
                minimum_class,
            "sample_ready":
                sample_ready,
        },
        "market_baseline": {
            "mean_brier":
                avg_market_brier,
            "mean_logloss":
                avg_market_logloss,
        },
        "frozen_candidate": {
            "mean_brier":
                avg_candidate_brier,
            "mean_logloss":
                avg_candidate_logloss,
            "class_calibration_absolute_error":
                calibration,
            "maximum_absolute_class_calibration_error":
                max_calibration_error,
        },
        "gates": {
            "brier_strict_improvement":
                brier_improved,
            "logloss_strict_improvement":
                logloss_improved,
            "calibration_passed":
                calibration_passed,
            "metric_gate_passed":
                metric_gate_passed,
            "interaction_direction_stability":
                (
                    "REQUIRES_MANUAL_GOVERNANCE_REVIEW"
                ),
        },
        "manual_governance_review_required":
            True,
        "automatic_canonical_promotion":
            False,
        "predictive_authority":
            "NOT_AUTHORIZED",
        "operational_betting_authority":
            False,
        "value_or_ev_authorized":
            False,
        "stake_changes_authorized":
            False,
        "r1_r2_r3_changes_authorized":
            False,
        "production_integration_authorized":
            False,
        "ui_integration_authorized":
            False,
    }


def run(
    *,
    observed_at: datetime | None = None,
    ops: Path = OPS,
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    observed_at = (
        observed_at or utc_now()
    ).astimezone(timezone.utc)

    config = read_json(
        Path(config_path)
    )

    contract = validate_contract(config)

    spec_path = ops_ref(
        contract["candidate_source"],
        ops,
    )

    spec = read_json(spec_path)

    validate_spec(
        spec,
        contract,
    )

    inputs = contract["inputs"]
    outputs = contract["outputs"]

    motivation_path = ops_ref(
        inputs[
            "motivation_prematch_journal"
        ],
        ops,
    )

    market_path = ops_ref(
        inputs[
            "market_prematch_journal"
        ],
        ops,
    )

    motivation_labels_path = ops_ref(
        inputs[
            "motivation_postmatch_labels"
        ],
        ops,
    )

    prematch_path = ops_ref(
        outputs["prematch_journal"],
        ops,
    )

    settlement_path = ops_ref(
        outputs["settlement_journal"],
        ops,
    )

    performance_path = ops_ref(
        outputs["performance_report"],
        ops,
    )

    _, motivation_rows = read_jsonl(
        motivation_path
    )

    _, market_rows = read_jsonl(
        market_path
    )

    _, motivation_labels = read_jsonl(
        motivation_labels_path
    )

    prematch_raw, prematch_rows = read_jsonl(
        prematch_path
    )

    settlement_raw, settlement_rows = read_jsonl(
        settlement_path
    )

    motivation_by_fixture = {
        str(row.get("fixture_id") or ""):
        row
        for row in motivation_rows
        if row.get("event_type")
        == "MOTIVATION_PREMATCH_FROZEN"
    }

    market_by_fixture = {
        str(row.get("fixture_id") or ""):
        row
        for row in market_rows
        if row.get("event_type")
        == "GENERIC_1X2_V1_PREMATCH_FROZEN"
    }

    existing_fixtures = {
        str(row.get("fixture_id") or "")
        for row in prematch_rows
    }

    created = []

    skipped_after_kickoff = 0
    skipped_missing_source = 0
    skipped_unknown_interaction = 0

    fixture_ids = sorted(
        set(motivation_by_fixture)
        & set(market_by_fixture)
    )

    for fixture_id in fixture_ids:
        if fixture_id in existing_fixtures:
            continue

        motivation = (
            motivation_by_fixture[
                fixture_id
            ]
        )

        market = market_by_fixture[
            fixture_id
        ]

        mp = motivation.get("payload") or {}
        kp = market.get("payload") or {}

        kickoff = parse_iso(
            mp.get("kickoff_utc")
        )

        if kickoff is None:
            skipped_missing_source += 1
            continue

        if observed_at >= kickoff:
            skipped_after_kickoff += 1
            continue

        motivation_frozen = parse_iso(
            motivation.get("frozen_at_utc")
        )

        market_observed = parse_iso(
            kp.get("observed_at_utc")
        )

        if (
            motivation_frozen is None
            or market_observed is None
            or motivation_frozen >= kickoff
            or market_observed >= kickoff
        ):
            skipped_missing_source += 1
            continue

        feature_values = interactions(mp)

        if feature_values is None:
            skipped_unknown_interaction += 1
            continue

        market_probability = kp.get(
            "p_market"
        )

        if not isinstance(
            market_probability,
            dict,
        ):
            skipped_missing_source += 1
            continue

        candidate, z = (
            candidate_probability(
                market_probability,
                feature_values,
                contract["beta"],
            )
        )

        payload = {
            "fixture_id": fixture_id,
            "kickoff_utc":
                mp.get("kickoff_utc"),
            "home_team":
                mp.get("home_team"),
            "away_team":
                mp.get("away_team"),
            "captured_at_utc":
                iso(observed_at),
            "motivation_source_event_id":
                motivation["event_id"],
            "market_source_event_id":
                market["event_id"],
            "market_observed_at_utc":
                kp.get("observed_at_utc"),
            "review_unit":
                "ACTIVE_INTERACTION_OBSERVATION",
            "active_interaction_observation":
                active_interaction(
                    feature_values
                ),
            "interactions":
                feature_values,
            "beta":
                contract["beta"],
            "z": z,
            "p_market": {
                key: float(
                    market_probability[key]
                )
                for key in ("H", "D", "A")
            },
            "p_frozen_interaction_candidate":
                candidate,
            "formula":
                contract["formula"],
            "forward_only": True,
            "historical_backfill":
                "FORBIDDEN",
            "old_holdout_reused":
                False,
            "parameters_refit":
                False,
            "interaction_reselection":
                False,
            "prematch_frozen":
                True,
            "research_only":
                True,
            "predictive_authority":
                "NOT_AUTHORIZED",
            "operational_betting_authority":
                False,
            "value_or_ev_authorized":
                False,
            "eligibility_mutation":
                False,
            "stake_changes":
                False,
            "r1_r2_r3_changes":
                False,
            "production_integration_authorized":
                False,
            "ui_integration_authorized":
                False,
            "automatic_promotion":
                False,
        }

        created.append({
            "event_id": event_id(
                "INTERACTION_PREMATCH",
                fixture_id,
            ),
            "event_type":
                "MOTIVATION_INTERACTION_V1_PREMATCH_FROZEN",
            "version": VERSION,
            "fixture_id": fixture_id,
            "frozen_at_utc":
                iso(observed_at),
            "immutable_fingerprint":
                fingerprint(payload),
            "payload": payload,
        })

    atomic_append(
        prematch_path,
        prematch_raw,
        created,
    )

    all_prematch = (
        prematch_rows + created
    )

    factual_by_fixture = {
        str(row.get("fixture_id") or ""):
        row
        for row in motivation_labels
        if row.get("event_type")
        == "MOTIVATION_POSTMATCH_LABEL"
    }

    settled_prematch_ids = {
        str(
            (
                row.get("payload")
                or {}
            ).get(
                "prematch_event_id"
            )
            or ""
        )
        for row in settlement_rows
    }

    new_settlements = []

    result_map = {
        "HOME_WIN": "H",
        "DRAW": "D",
        "AWAY_WIN": "A",
    }

    for prematch in all_prematch:
        if (
            prematch["event_id"]
            in settled_prematch_ids
        ):
            continue

        factual = factual_by_fixture.get(
            str(
                prematch.get(
                    "fixture_id"
                )
                or ""
            )
        )

        if factual is None:
            continue

        result = result_map.get(
            str(
                (
                    factual.get("payload")
                    or {}
                ).get("match_result")
                or ""
            ).upper()
        )

        if result is None:
            continue

        pp = prematch.get("payload") or {}

        market_score = score(
            pp["p_market"],
            result,
        )

        candidate_score = score(
            pp[
                "p_frozen_interaction_candidate"
            ],
            result,
        )

        payload = {
            "fixture_id":
                prematch["fixture_id"],
            "prematch_event_id":
                prematch["event_id"],
            "source_postmatch_event_id":
                factual["event_id"],
            "result": result,
            "active_interaction_observation":
                bool(
                    pp.get(
                        "active_interaction_observation"
                    )
                ),
            "market": market_score,
            "frozen_interaction_candidate":
                candidate_score,
            "candidate_minus_market_brier":
                candidate_score["brier"]
                - market_score["brier"],
            "candidate_minus_market_logloss":
                candidate_score["logloss"]
                - market_score["logloss"],
            "postmatch_factual":
                True,
            "prematch_evidence_mutated":
                False,
            "parameters_refit":
                False,
            "interaction_reselection":
                False,
            "research_only":
                True,
            "predictive_authority":
                "NOT_AUTHORIZED",
            "operational_betting_authority":
                False,
            "value_or_ev_authorized":
                False,
            "stake_changes":
                False,
            "automatic_promotion":
                False,
        }

        new_settlements.append({
            "event_id": event_id(
                "INTERACTION_SETTLEMENT",
                prematch["fixture_id"],
            ),
            "event_type":
                "MOTIVATION_INTERACTION_V1_FORWARD_SETTLEMENT",
            "version": VERSION,
            "fixture_id":
                prematch["fixture_id"],
            "frozen_at_utc":
                iso(observed_at),
            "immutable_fingerprint":
                fingerprint(payload),
            "payload": payload,
        })

    atomic_append(
        settlement_path,
        settlement_raw,
        new_settlements,
    )

    all_settlements = (
        settlement_rows
        + new_settlements
    )

    performance = performance_report(
        contract,
        all_prematch,
        all_settlements,
    )

    performance.update({
        "run_at_utc": iso(
            observed_at
        ),
        "research_id":
            EXPECTED_RESEARCH_ID,
        "model_version":
            EXPECTED_MODEL_VERSION,
        "selected_interactions":
            list(SELECTED),
        "frozen_beta":
            contract["beta"],
        "prematch_events_created":
            len(created),
        "settlements_created":
            len(new_settlements),
        "prematch_events_total":
            len(all_prematch),
        "settlements_total":
            len(all_settlements),
        "skipped_after_kickoff_no_backfill":
            skipped_after_kickoff,
        "skipped_missing_source":
            skipped_missing_source,
        "skipped_unknown_interaction":
            skipped_unknown_interaction,
        "historical_backfill":
            "FORBIDDEN",
        "old_holdout_reused":
            False,
        "parameters_may_change":
            False,
    })

    atomic_json(
        performance_path,
        performance,
    )

    return performance


def main() -> int:
    result = run()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
