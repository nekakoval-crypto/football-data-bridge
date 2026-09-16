#!/usr/bin/env python3
"""Forward-only monitor core for PBK Generic 1X2 Probability v1.

All 16 locked PBK leagues are captured prospectively. Formal forward validation
is league-specific: every league has its own sample readiness, proper scoring,
class calibration and PASS/FAIL status. The historical Big-5 PASS remains pooled
historical evidence only and is never treated as proof for any individual league.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFG = ROOT / "config" / "pbk_generic_1x2_probability_v1_forward.json"
CLASSES = ("H", "D", "A")
PREMATCH_EVENT = "GENERIC_1X2_V1_PREMATCH_FROZEN"
SETTLEMENT_EVENT = "GENERIC_1X2_V1_SETTLEMENT_FROZEN"
HISTORICAL_BIG5_POOL_MEMBER = "HISTORICAL_BIG5_POOL_MEMBER"
NO_HISTORICAL_LEAGUE_VALIDATION = "NO_HISTORICAL_LEAGUE_VALIDATION"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def fnum(value):
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_jsonl(path: Path):
    if not path.exists():
        return b"", []
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    ids = [row.get("event_id") for row in rows]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"invalid or duplicate event_id in {path}")
    return raw, rows


def atomic_append_jsonl(path: Path, original: bytes, events):
    if not events and path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    separator = b"\n" if original and not original.endswith(b"\n") else b""
    addition = b"".join(
        (json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        for event in events
    )
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(original + separator + addition)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def atomic_write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def event_id(kind: str, fixture_id: str) -> str:
    raw = f"PBK_GENERIC_1X2_PROBABILITY_V1|{kind}|{fixture_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def market_probabilities(home, draw, away):
    odds = [fnum(home), fnum(draw), fnum(away)]
    if any(value is None or value <= 1.0 for value in odds):
        raise ValueError("complete valid Bet365 H/D/A prices are required")
    inverse = [1.0 / value for value in odds]
    total = sum(inverse)
    return tuple(value / total for value in inverse)


def shifted_probabilities(p, alpha_h, alpha_a):
    scores = [math.log(p[0]) + alpha_h, math.log(p[1]), math.log(p[2]) + alpha_a]
    maximum = max(scores)
    exponentials = [math.exp(value - maximum) for value in scores]
    total = sum(exponentials)
    return tuple(value / total for value in exponentials)


def multiclass_brier(p, outcome):
    return sum(
        (p[index] - (1.0 if outcome == label else 0.0)) ** 2
        for index, label in enumerate(CLASSES)
    )


def multiclass_logloss(p, outcome):
    return -math.log(max(p[CLASSES.index(outcome)], 1e-15))


def normalize_league(value):
    return " ".join(str(value or "").strip().lower().replace("-", " ").split())


def _scope_sets(cfg):
    scope = cfg["scope"]
    historical_big5 = {normalize_league(x) for x in scope["historical_big5_pooled_leagues"]}
    unvalidated = {normalize_league(x) for x in scope["historically_unvalidated_leagues"]}
    tracked = {normalize_league(x) for x in scope["tracked_leagues"]}
    if historical_big5 & unvalidated:
        raise ValueError("historical scope groups must be disjoint")
    if historical_big5 | unvalidated != tracked:
        raise ValueError("tracked_leagues must equal historical Big-5 + historically unvalidated leagues")
    if len(tracked) != int(scope.get("locked_total_leagues", len(tracked))):
        raise ValueError("locked forward league count drifted")
    if len(historical_big5) != 5:
        raise ValueError("historical pooled Big-5 membership drifted")
    return historical_big5, unvalidated, tracked


def historical_evidence_status(cfg, league):
    historical_big5, unvalidated, _ = _scope_sets(cfg)
    key = normalize_league(league)
    if key in historical_big5:
        return HISTORICAL_BIG5_POOL_MEMBER
    if key in unvalidated:
        return NO_HISTORICAL_LEAGUE_VALIDATION
    return None


def load_contract(config_path=DEFAULT_CFG):
    config_path = Path(config_path)
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    _scope_sets(cfg)
    review = cfg["forward_review"]
    if review.get("review_unit") != "LEAGUE":
        raise ValueError("forward review unit must remain LEAGUE")
    if review.get("pooled_big5_diagnostic_only") is not True:
        raise ValueError("pooled Big-5 forward metrics must remain diagnostic only")
    if review.get("combined_16_league_verdict") is not False:
        raise ValueError("combined 16-league verdict must remain disabled")

    result_path = Path(cfg["historical_result_path"])
    if not result_path.is_absolute():
        result_path = ROOT / result_path
    historical = json.loads(result_path.read_text(encoding="utf-8"))
    required = cfg["historical_result_required_verdict"]
    if historical.get("final_verdict") != required:
        raise ValueError("historical Generic 1X2 v1 PASS result is required")
    if historical.get("execution", {}).get("no_posthoc_tuning") is not True:
        raise ValueError("historical result must confirm no_posthoc_tuning=true")
    if historical.get("authorization", {}).get("production_integration_authorized") is not False:
        raise ValueError("historical result must not authorize production integration")

    frozen = cfg["frozen_model"]
    fit = historical.get("fit", {})
    pairs = (
        ("alpha_h", frozen["alpha_h"], fit.get("alpha_h")),
        ("alpha_d", frozen["alpha_d"], fit.get("alpha_d")),
        ("alpha_a", frozen["alpha_a"], fit.get("alpha_a")),
    )
    for name, configured, historical_value in pairs:
        if historical_value is None or abs(float(configured) - float(historical_value)) > 1e-15:
            raise ValueError(f"frozen {name} differs from historical result")
    return cfg, historical


def observation_to_event(row, cfg, process_time=None):
    fixture_id = str(row.get("fixture_id") or row.get("api_fixture_id") or "").strip()
    if not fixture_id:
        raise ValueError("fixture_id is required")

    kickoff = parse_iso(row.get("kickoff_utc"))
    observed = parse_iso(row.get("observed_at_utc") or row.get("captured_at_utc"))
    processed = parse_iso(process_time or now_iso())
    if kickoff is None or observed is None or processed is None:
        raise ValueError("aware kickoff, observation, and process timestamps are required")
    if observed >= kickoff:
        raise ValueError("post-kickoff observation forbidden")
    if processed >= kickoff:
        raise ValueError("historical_backfill_forbidden")

    league = str(row.get("league") or "").strip()
    evidence = historical_evidence_status(cfg, league)
    if evidence is None:
        raise ValueError("outside_scope")

    p_market = market_probabilities(
        row.get("b365_home") or row.get("B365H"),
        row.get("b365_draw") or row.get("B365D"),
        row.get("b365_away") or row.get("B365A"),
    )
    frozen = cfg["frozen_model"]
    p_m1 = shifted_probabilities(p_market, float(frozen["alpha_h"]), float(frozen["alpha_a"]))
    tolerance = float(cfg["guards"]["probability_sum_tolerance"])
    if abs(sum(p_market) - 1.0) > tolerance or abs(sum(p_m1) - 1.0) > tolerance:
        raise ValueError("probability_sum_guard_failed")

    payload = {
        "research_id": cfg["research_id"],
        "model_version": cfg["model_version"],
        "fixture_id": fixture_id,
        "league": league,
        "historical_evidence_status": evidence,
        "league_forward_review_eligible": True,
        "home_team": str(row.get("home_team") or "").strip(),
        "away_team": str(row.get("away_team") or "").strip(),
        "kickoff_utc": kickoff.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "observed_at_utc": observed.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "monitor_processed_at_utc": processed.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": str(row.get("source") or "BET365_MATCH_WINNER_1X2").strip(),
        "bookmaker": "Bet365",
        "market": "MATCH_WINNER_1X2",
        "b365_home": fnum(row.get("b365_home") or row.get("B365H")),
        "b365_draw": fnum(row.get("b365_draw") or row.get("B365D")),
        "b365_away": fnum(row.get("b365_away") or row.get("B365A")),
        "p_market": dict(zip(CLASSES, p_market)),
        "p_m1": dict(zip(CLASSES, p_m1)),
        "alpha": {
            "H": float(frozen["alpha_h"]),
            "D": float(frozen["alpha_d"]),
            "A": float(frozen["alpha_a"]),
        },
        "authority": "RESEARCH",
        "forward_only": True,
        "creates_signal": False,
        "value_authorized": False,
        "stake_changes_authorized": False,
        "canonical_promotion_authorized": False,
    }
    return {
        "event_id": event_id(PREMATCH_EVENT, fixture_id),
        "event_type": PREMATCH_EVENT,
        "fixture_id": fixture_id,
        "frozen_at_utc": payload["monitor_processed_at_utc"],
        "payload": payload,
    }


def freeze_observations(rows, cfg, existing, process_time=None):
    known = {str(event.get("fixture_id")): event for event in existing}
    added, rejected = [], []
    for row in rows:
        fixture_id = str(row.get("fixture_id") or row.get("api_fixture_id") or "").strip()
        if fixture_id and fixture_id in known:
            rejected.append({"fixture_id": fixture_id, "reason": "already_frozen"})
            continue
        try:
            event = observation_to_event(row, cfg, process_time=process_time)
        except ValueError as exc:
            rejected.append({"fixture_id": fixture_id, "reason": str(exc)})
            continue
        known[event["fixture_id"]] = event
        added.append(event)
    return added, rejected


def settlement_to_event(row, prematch_by_fixture):
    fixture_id = str(row.get("fixture_id") or row.get("api_fixture_id") or "").strip()
    prematch = prematch_by_fixture.get(fixture_id)
    if prematch is None:
        raise ValueError("missing_frozen_prematch")

    outcome = str(row.get("result") or row.get("FTR") or "").strip().upper()
    if outcome not in CLASSES:
        raise ValueError("settlement result must be H, D, or A")
    kickoff = parse_iso(prematch["payload"]["kickoff_utc"])
    settled_at = parse_iso(row.get("settled_at_utc"))
    if kickoff is None or settled_at is None or settled_at <= kickoff:
        raise ValueError("settlement must occur after kickoff")

    p_market = tuple(float(prematch["payload"]["p_market"][label]) for label in CLASSES)
    p_m1 = tuple(float(prematch["payload"]["p_m1"][label]) for label in CLASSES)
    payload = {
        "research_id": prematch["payload"]["research_id"],
        "model_version": prematch["payload"]["model_version"],
        "fixture_id": fixture_id,
        "league": prematch["payload"]["league"],
        "historical_evidence_status": prematch["payload"]["historical_evidence_status"],
        "league_forward_review_eligible": True,
        "prematch_event_id": prematch["event_id"],
        "kickoff_utc": prematch["payload"]["kickoff_utc"],
        "settled_at_utc": settled_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "result": outcome,
        "p_market": dict(zip(CLASSES, p_market)),
        "p_m1": dict(zip(CLASSES, p_m1)),
        "brier_market": multiclass_brier(p_market, outcome),
        "brier_m1": multiclass_brier(p_m1, outcome),
        "logloss_market": multiclass_logloss(p_market, outcome),
        "logloss_m1": multiclass_logloss(p_m1, outcome),
        "profitability_tested": False,
        "value_authorized": False,
        "creates_signal": False,
        "stake_changes_authorized": False,
    }
    return {
        "event_id": event_id(SETTLEMENT_EVENT, fixture_id),
        "event_type": SETTLEMENT_EVENT,
        "fixture_id": fixture_id,
        "frozen_at_utc": payload["settled_at_utc"],
        "payload": payload,
    }


def settle_rows(rows, prematch_events, existing_settlements):
    prematch_by_fixture = {str(event["fixture_id"]): event for event in prematch_events}
    known = {str(event["fixture_id"]): event for event in existing_settlements}
    added, rejected = [], []
    for row in rows:
        fixture_id = str(row.get("fixture_id") or row.get("api_fixture_id") or "").strip()
        if fixture_id and fixture_id in known:
            rejected.append({"fixture_id": fixture_id, "reason": "already_settled"})
            continue
        try:
            event = settlement_to_event(row, prematch_by_fixture)
        except ValueError as exc:
            rejected.append({"fixture_id": fixture_id, "reason": str(exc)})
            continue
        known[event["fixture_id"]] = event
        added.append(event)
    return added, rejected


def calibration(settlements):
    result = {}
    count = len(settlements)
    for label in CLASSES:
        mean_probability = sum(float(event["payload"]["p_m1"][label]) for event in settlements) / count
        outcomes = sum(event["payload"]["result"] == label for event in settlements)
        observed = outcomes / count
        result[label] = {
            "mean_probability": mean_probability,
            "observed_rate": observed,
            "abs_error": abs(mean_probability - observed),
            "outcomes": outcomes,
        }
    return result


def prematch_forward_only(events):
    for event in events:
        payload = event.get("payload", {})
        kickoff = parse_iso(payload.get("kickoff_utc"))
        observed = parse_iso(payload.get("observed_at_utc"))
        processed = parse_iso(payload.get("monitor_processed_at_utc"))
        if not kickoff or not observed or not processed or observed >= kickoff or processed >= kickoff:
            return False
        if payload.get("forward_only") is not True or "result" in payload:
            return False
    return True


def _metrics(cfg, prematch_events, settlements, formal=True):
    review = cfg["forward_review"]
    guards = cfg["guards"]
    counts = Counter(event["payload"]["result"] for event in settlements)
    n = len(settlements)
    forward_guard = prematch_forward_only(prematch_events)
    probability_guard = bool(settlements) and all(
        abs(sum(float(event["payload"]["p_m1"][label]) for label in CLASSES) - 1.0)
        <= float(guards["probability_sum_tolerance"])
        for event in settlements
    )
    if settlements:
        m0_brier = sum(float(e["payload"]["brier_market"]) for e in settlements) / n
        m1_brier = sum(float(e["payload"]["brier_m1"]) for e in settlements) / n
        m0_logloss = sum(float(e["payload"]["logloss_market"]) for e in settlements) / n
        m1_logloss = sum(float(e["payload"]["logloss_m1"]) for e in settlements) / n
        cal = calibration(settlements)
    else:
        m0_brier = m1_brier = m0_logloss = m1_logloss = None
        cal = {}

    minimum_rows = int(review["minimum_settled_rows_per_league"])
    minimum_class = int(review["minimum_settled_outcomes_per_class_per_league"])
    sample_ready = (
        formal
        and n >= minimum_rows
        and all(counts[label] >= minimum_class for label in CLASSES)
    )
    checks = {
        "minimum_forward_rows": n >= minimum_rows,
        "minimum_forward_outcomes_per_class": all(counts[label] >= minimum_class for label in CLASSES),
        "brier_strict_improvement": bool(settlements) and m1_brier < m0_brier,
        "logloss_strict_improvement": bool(settlements) and m1_logloss < m0_logloss,
        "class_calibration": bool(settlements) and all(
            cal[label]["abs_error"] <= float(review["maximum_absolute_class_calibration_error"])
            for label in CLASSES
        ),
        "probability_sum": probability_guard,
        "forward_only_no_backfill": forward_guard,
    }
    quality_keys = (
        "brier_strict_improvement",
        "logloss_strict_improvement",
        "class_calibration",
        "probability_sum",
        "forward_only_no_backfill",
    )
    if not formal:
        status = "DIAGNOSTIC_ONLY"
    elif not sample_ready:
        status = "COLLECTING"
    elif all(checks[key] for key in quality_keys):
        status = "FORWARD_REVIEW_READY_PASS"
    else:
        status = "FORWARD_REVIEW_READY_FAIL"

    return {
        "status": status,
        "prematch_frozen": len(prematch_events),
        "settled_rows": n,
        "forward_outcomes": {label: counts[label] for label in CLASSES},
        "diagnostic_checkpoints_reached": {
            str(point): n >= int(point)
            for point in review.get("diagnostic_checkpoints_per_league", [])
        },
        "formal_review_sample_ready": sample_ready,
        "scores": {
            "m0_multiclass_brier": m0_brier,
            "m1_multiclass_brier": m1_brier,
            "brier_improvement_m0_minus_m1": None if not settlements else m0_brier - m1_brier,
            "m0_logloss": m0_logloss,
            "m1_logloss": m1_logloss,
            "logloss_improvement_m0_minus_m1": None if not settlements else m0_logloss - m1_logloss,
        },
        "m1_class_calibration": cal,
        "checks": checks,
    }


def performance_report(cfg, prematch_events, settlements):
    scope = cfg["scope"]
    historical_big5 = {normalize_league(x) for x in scope["historical_big5_pooled_leagues"]}
    reviews = {}
    for league in scope["tracked_leagues"]:
        key = normalize_league(league)
        league_prematch = [
            e for e in prematch_events
            if normalize_league(e["payload"].get("league")) == key
        ]
        league_settlements = [
            e for e in settlements
            if normalize_league(e["payload"].get("league")) == key
        ]
        metrics = _metrics(cfg, league_prematch, league_settlements, formal=True)
        metrics["league"] = league
        metrics["historical_evidence"] = (
            "POOLED_BIG5_HISTORICAL_PASS_ONLY_NOT_LEAGUE_SPECIFIC"
            if key in historical_big5
            else "NO_HISTORICAL_VALIDATION"
        )
        metrics["forward_validation_scope"] = "THIS_LEAGUE_ONLY"
        reviews[league] = metrics

    big5_prematch = [
        e for e in prematch_events
        if normalize_league(e["payload"].get("league")) in historical_big5
    ]
    big5_settlements = [
        e for e in settlements
        if normalize_league(e["payload"].get("league")) in historical_big5
    ]
    big5_diag = _metrics(cfg, big5_prematch, big5_settlements, formal=False)
    big5_diag["purpose"] = "POOLED_DIAGNOSTIC_ONLY_NOT_AN_OFFICIAL_FORWARD_VERDICT"

    all16_diag = _metrics(cfg, prematch_events, settlements, formal=False)
    all16_diag["purpose"] = "ALL_16_POOLED_DIAGNOSTIC_ONLY_NOT_AN_OFFICIAL_FORWARD_VERDICT"

    status_counts = Counter(review["status"] for review in reviews.values())
    return {
        "generated_at_utc": now_iso(),
        "research_id": cfg["research_id"],
        "model_version": cfg["model_version"],
        "status": "PER_LEAGUE_FORWARD_REVIEW",
        "authority": "RESEARCH",
        "tracked_leagues": len(scope["tracked_leagues"]),
        "league_reviews": reviews,
        "league_status_counts": dict(status_counts),
        "pooled_big5_diagnostic": big5_diag,
        "pooled_all16_diagnostic": all16_diag,
        "all_leagues_totals": {
            "prematch_frozen": len(prematch_events),
            "settled_rows": len(settlements),
        },
        "policy": {
            "snapshot": cfg["capture_policy"]["snapshot"],
            "official_verdict_scope": "PER_LEAGUE_ONLY",
            "pooled_big5_forward_verdict": False,
            "combined_16_league_verdict": False,
            "historical_big5_pass_is_not_league_specific_validation": True,
            "historical_backfill": "FORBIDDEN",
            "bookmaker_substitution": False,
            "profitability_or_roi_conclusion": False,
            "value_authorized": False,
            "stake_changes_authorized": False,
            "creates_signal": False,
            "r1_r2_r3_changes_authorized": False,
            "production_integration_authorized": False,
            "automatic_canonical_promotion": False,
            "manual_governance_review_required": True,
        },
    }


def output_paths(ops_dir: Path, cfg):
    outputs = cfg["outputs"]
    return (
        ops_dir / outputs["prematch_journal"],
        ops_dir / outputs["settlement_journal"],
        ops_dir / outputs["performance_report"],
    )


def run_capture(input_path: Path, ops_dir: Path, config_path=DEFAULT_CFG, process_time=None):
    cfg, _ = load_contract(config_path)
    prematch_path, settlement_path, report_path = output_paths(ops_dir, cfg)
    prematch_raw, prematch = read_jsonl(prematch_path)
    _, settlements = read_jsonl(settlement_path)
    processed_at = process_time or now_iso()
    added, rejected = freeze_observations(read_csv(input_path), cfg, prematch, process_time=processed_at)
    atomic_append_jsonl(prematch_path, prematch_raw, added)
    prematch = prematch + added
    report = performance_report(cfg, prematch, settlements)
    atomic_write_json(report_path, report)
    return {
        "status": report["status"],
        "observations_added": len(added),
        "observations_rejected": len(rejected),
        "prematch_frozen": len(prematch),
        "settled_rows": len(settlements),
        "league_status_counts": report["league_status_counts"],
        "rejections": rejected,
        "api_calls": 0,
    }


def run_settle(input_path: Path, ops_dir: Path, config_path=DEFAULT_CFG):
    cfg, _ = load_contract(config_path)
    prematch_path, settlement_path, report_path = output_paths(ops_dir, cfg)
    _, prematch = read_jsonl(prematch_path)
    settlement_raw, settlements = read_jsonl(settlement_path)
    added, rejected = settle_rows(read_csv(input_path), prematch, settlements)
    atomic_append_jsonl(settlement_path, settlement_raw, added)
    settlements = settlements + added
    report = performance_report(cfg, prematch, settlements)
    atomic_write_json(report_path, report)
    return {
        "status": report["status"],
        "settlements_added": len(added),
        "settlements_rejected": len(rejected),
        "prematch_frozen": len(prematch),
        "settled_rows": len(settlements),
        "league_status_counts": report["league_status_counts"],
        "rejections": rejected,
        "api_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CFG)
    parser.add_argument("--ops-dir", type=Path, default=Path(os.getenv("OPS_DIR", "ops")))
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture = subparsers.add_parser("capture")
    capture.add_argument("--input", type=Path, required=True)
    settle = subparsers.add_parser("settle")
    settle.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"DATA_REQUIRED: input not found: {args.input}")
    if args.command == "capture":
        result = run_capture(args.input, args.ops_dir, args.config)
    else:
        result = run_settle(args.input, args.ops_dir, args.config)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
