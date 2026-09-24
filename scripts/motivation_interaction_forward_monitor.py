#!/usr/bin/env python3
"""PBK Item 13 — frozen Motivation Interaction Specialist V1 forward monitor.

Prospective research only.

Consumes already-frozen PBK evidence:
- motivation_forward_prematch.jsonl
- generic_1x2_v1_forward_prematch.jsonl
- motivation_forward_labels.jsonl
- motivation_interaction_specialist_v1.json

It NEVER:
- refits beta;
- reselects interactions;
- reuses the old historical holdout;
- historical-backfills missed forward observations;
- mutates source prematch evidence;
- grants predictive, betting, value, eligibility or stake authority.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "PBK_MOTIVATION_INTERACTION_FORWARD_MONITOR_V1"

ROOT = Path(__file__).resolve().parents[1]
OPS = Path(os.getenv("OPS_DIR", str(ROOT / "ops")))

SPEC = OPS / "motivation_interaction_specialist_v1.json"
MOTIVATION = OPS / "motivation_forward_prematch.jsonl"
MARKET = OPS / "generic_1x2_v1_forward_prematch.jsonl"
MOTIVATION_LABELS = OPS / "motivation_forward_labels.jsonl"

PREMATCH = OPS / "motivation_interaction_v1_forward_prematch.jsonl"
LABELS = OPS / "motivation_interaction_v1_forward_labels.jsonl"
LAST_RUN = OPS / "motivation_interaction_v1_forward_last_run.json"

SELECTED = (
    "HIGH_PRESSURE_X_FORM_ALIGNMENT",
    "HIGH_PRESSURE_X_LARGE_RANK_DISADVANTAGE",
)

EXPECTED_BETA = {
    "HIGH_PRESSURE_X_FORM_ALIGNMENT": -0.08139028122268811,
    "HIGH_PRESSURE_X_LARGE_RANK_DISADVANTAGE": -0.04354603042978898,
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
        result = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )
    except ValueError:
        return None

    if result.tzinfo is None:
        return None

    return result.astimezone(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    value = json.loads(
        path.read_text(encoding="utf-8")
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
        raw.decode("utf-8").splitlines(),
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


def event_id(kind: str, fixture_id: str) -> str:
    material = (
        f"{VERSION}|{kind}|{fixture_id}"
    )

    return hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()[:32]


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


def validate_spec(
    spec: dict[str, Any],
) -> dict[str, float]:
    selected = tuple(
        spec.get("selected_interactions")
        or []
    )

    frozen = (
        spec.get("frozen_candidate")
        or {}
    )

    auth = (
        spec.get("authorization")
        or {}
    )

    beta = frozen.get("beta") or {}

    if selected != SELECTED:
        raise ValueError(
            "frozen selected interactions drift"
        )

    if tuple(
        frozen.get("interactions") or []
    ) != SELECTED:
        raise ValueError(
            "frozen candidate interactions drift"
        )

    if (
        frozen.get(
            "parameters_may_change_after_freeze"
        )
        is not False
    ):
        raise ValueError(
            "frozen beta mutation guard missing"
        )

    if (
        auth.get("forward_review_allowed")
        is not True
    ):
        raise ValueError(
            "forward review not authorized"
        )

    if (
        auth.get("predictive_authority")
        != "NOT_AUTHORIZED"
    ):
        raise ValueError(
            "predictive authority drift"
        )

    result = {}

    for name in SELECTED:
        value = float(beta[name])

        if not math.isclose(
            value,
            EXPECTED_BETA[name],
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise ValueError(
                f"frozen beta drift: {name}"
            )

        result[name] = value

    return result


def pressure_side(
    payload: dict[str, Any],
) -> float | None:
    comparison = (
        payload.get("comparison")
        or {}
    )

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

    if diff >= 0.25:
        return 1.0

    if diff <= -0.25:
        return -1.0

    return 0.0


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

    if motivation == context:
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
        SELECTED[0]: first,
        SELECTED[1]: second,
    }


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

    brier = sum(
        (
            probability[key]
            - target[key]
        ) ** 2
        for key in ("H", "D", "A")
    ) / 3.0

    logloss = -math.log(
        max(
            probability[result],
            1e-15,
        )
    )

    return {
        "brier": brier,
        "logloss": logloss,
    }


def run(
    *,
    observed_at: datetime | None = None,
    ops: Path = OPS,
) -> dict[str, Any]:
    observed_at = (
        observed_at or utc_now()
    ).astimezone(timezone.utc)

    beta = validate_spec(
        read_json(
            ops / SPEC.name
        )
    )

    mot_raw, mot_rows = read_jsonl(
        ops / MOTIVATION.name
    )

    market_raw, market_rows = read_jsonl(
        ops / MARKET.name
    )

    label_raw, motivation_labels = read_jsonl(
        ops / MOTIVATION_LABELS.name
    )

    del mot_raw, market_raw, label_raw

    out_raw, out_rows = read_jsonl(
        ops / PREMATCH.name
    )

    comparison_raw, comparison_rows = read_jsonl(
        ops / LABELS.name
    )

    mot_by_fixture = {
        str(row.get("fixture_id") or ""):
        row
        for row in mot_rows
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

    existing = {
        str(row.get("fixture_id") or "")
        for row in out_rows
    }

    created = []
    skipped_after_kickoff = 0
    skipped_missing_source = 0
    skipped_unknown_interaction = 0

    fixture_ids = sorted(
        set(mot_by_fixture)
        & set(market_by_fixture)
    )

    for fid in fixture_ids:
        if fid in existing:
            continue

        mot = mot_by_fixture[fid]
        market = market_by_fixture[fid]

        mp = mot.get("payload") or {}
        kp = market.get("payload") or {}

        kickoff = parse_iso(
            mp.get("kickoff_utc")
        )

        if kickoff is None:
            skipped_missing_source += 1
            continue

        # Missed observations are NEVER reconstructed.
        if observed_at >= kickoff:
            skipped_after_kickoff += 1
            continue

        mot_frozen = parse_iso(
            mot.get("frozen_at_utc")
        )

        market_observed = parse_iso(
            kp.get("observed_at_utc")
        )

        if (
            mot_frozen is None
            or market_observed is None
            or mot_frozen >= kickoff
            or market_observed >= kickoff
        ):
            skipped_missing_source += 1
            continue

        features = interactions(mp)

        if features is None:
            skipped_unknown_interaction += 1
            continue

        p_market = kp.get("p_market")

        if not isinstance(
            p_market,
            dict,
        ):
            skipped_missing_source += 1
            continue

        candidate, z = (
            candidate_probability(
                p_market,
                features,
                beta,
            )
        )

        payload = {
            "fixture_id": fid,
            "kickoff_utc": mp.get(
                "kickoff_utc"
            ),
            "home_team": mp.get(
                "home_team"
            ),
            "away_team": mp.get(
                "away_team"
            ),
            "captured_at_utc": iso(
                observed_at
            ),
            "motivation_source_event_id":
                mot["event_id"],
            "market_source_event_id":
                market["event_id"],
            "market_observed_at_utc":
                kp.get("observed_at_utc"),
            "interactions": features,
            "beta": beta,
            "z": z,
            "p_market": {
                key: float(
                    p_market[key]
                )
                for key in (
                    "H",
                    "D",
                    "A",
                )
            },
            "p_frozen_interaction_candidate":
                candidate,
            "formula": (
                "softmax(log(p_market_H)+z,"
                "log(p_market_D),"
                "log(p_market_A)-z)"
            ),
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
            "automatic_promotion":
                False,
        }

        created.append({
            "event_id": event_id(
                "INTERACTION_PREMATCH",
                fid,
            ),
            "event_type":
                "MOTIVATION_INTERACTION_V1_PREMATCH_FROZEN",
            "version": VERSION,
            "fixture_id": fid,
            "frozen_at_utc": iso(
                observed_at
            ),
            "immutable_fingerprint":
                fingerprint(payload),
            "payload": payload,
        })

    atomic_append(
        ops / PREMATCH.name,
        out_raw,
        created,
    )

    all_prematch = out_rows + created

    labels_by_fixture = {
        str(row.get("fixture_id") or ""):
        row
        for row in motivation_labels
        if row.get("event_type")
        == "MOTIVATION_POSTMATCH_LABEL"
    }

    already_labeled = {
        str(
            (
                row.get("payload")
                or {}
            ).get(
                "prematch_event_id"
            )
            or ""
        )
        for row in comparison_rows
    }

    new_comparisons = []

    for prematch in all_prematch:
        if (
            prematch["event_id"]
            in already_labeled
        ):
            continue

        factual = labels_by_fixture.get(
            str(
                prematch.get(
                    "fixture_id"
                )
                or ""
            )
        )

        if factual is None:
            continue

        result_name = str(
            (
                factual.get("payload")
                or {}
            ).get("match_result")
            or ""
        ).upper()

        mapping = {
            "HOME_WIN": "H",
            "DRAW": "D",
            "AWAY_WIN": "A",
        }

        result = mapping.get(
            result_name
        )

        if result is None:
            continue

        pp = prematch["payload"]

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
            "market": market_score,
            "frozen_interaction_candidate":
                candidate_score,
            "candidate_minus_market_brier":
                candidate_score["brier"]
                - market_score["brier"],
            "candidate_minus_market_logloss":
                candidate_score["logloss"]
                - market_score["logloss"],
            "postmatch_factual": True,
            "prematch_evidence_mutated":
                False,
            "parameters_refit":
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

        new_comparisons.append({
            "event_id": event_id(
                "INTERACTION_POSTMATCH",
                prematch["fixture_id"],
            ),
            "event_type":
                "MOTIVATION_INTERACTION_V1_POSTMATCH_REVIEW",
            "version": VERSION,
            "fixture_id":
                prematch["fixture_id"],
            "frozen_at_utc": iso(
                observed_at
            ),
            "immutable_fingerprint":
                fingerprint(payload),
            "payload": payload,
        })

    atomic_append(
        ops / LABELS.name,
        comparison_raw,
        new_comparisons,
    )

    report = {
        "version": VERSION,
        "run_at_utc": iso(
            observed_at
        ),
        "status":
            "PROSPECTIVE_FORWARD_MONITOR_ACTIVE",
        "selected_interactions":
            list(SELECTED),
        "frozen_beta": beta,
        "prospective_only": True,
        "historical_backfill":
            "FORBIDDEN",
        "old_holdout_reused":
            False,
        "parameters_may_change":
            False,
        "prematch_events_created":
            len(created),
        "postmatch_reviews_created":
            len(new_comparisons),
        "prematch_events_total":
            len(all_prematch),
        "postmatch_reviews_total":
            len(comparison_rows)
            + len(new_comparisons),
        "skipped_after_kickoff_no_backfill":
            skipped_after_kickoff,
        "skipped_missing_source":
            skipped_missing_source,
        "skipped_unknown_interaction":
            skipped_unknown_interaction,
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
        "automatic_promotion":
            False,
    }

    atomic_json(
        ops / LAST_RUN.name,
        report,
    )

    return report


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
