#!/usr/bin/env python3
"""Immutable, provider-free PBK Forward journal.

The mutable operational CSVs remain useful read models, but they are not audit
ledgers. This module freezes pre-match evidence into append-only JSONL and puts
settlement into a separate append-only journal.

Hard invariants:
* no historical backfill: first observation must happen strictly before kickoff;
* no lookahead: screened/prediction/execution evidence must predate kickoff;
* old journal bytes are never reserialized or overwritten;
* immutable-source drift is reported, never repaired in place;
* settlement never mutates the pre-match journal;
* no network/provider calls.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

from pbk_calculation_contract import CONTRACT_VERSION, evaluate_value, match_winner_no_vig

JOURNAL_VERSION = "PBK_FORWARD_JOURNAL_V1"
OPS = Path(os.getenv("OPS_DIR", "ops"))
FORWARD = OPS / "forward_log.csv"
USER_VIEW = OPS / "user_forward_view.csv"
PREDICTIONS = OPS / "stage75_probability_predictions.csv"
PREMATCH_JOURNAL = OPS / "forward_prematch_journal.jsonl"
SETTLEMENT_JOURNAL = OPS / "forward_settlement_journal.jsonl"
META = OPS / "pbk_forward_journal_last_run.json"

SIGNAL_FIELDS = (
    "forward_id", "rule", "screened_at_utc", "league", "div", "api_fixture_id",
    "match_date", "kickoff_time", "home_team", "away_team", "bet_market",
    "bet_selection", "stake_u", "trigger_source", "trigger_b365_home",
    "trigger_b365_draw", "trigger_b365_away", "execution_source",
    "execution_bookmaker", "execution_odds", "execution_last_update_utc",
    "execution_verified",
)


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def kickoff_from_forward(row):
    date = str(row.get("match_date") or "").strip()
    clock = str(row.get("kickoff_time") or "").strip()
    if not date or not clock:
        return None
    if len(clock) == 5:
        clock += ":00"
    return parse_iso(f"{date}T{clock}Z")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _event_id(kind, *parts):
    material = "|".join([JOURNAL_VERSION, kind, *[str(part or "") for part in parts]])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _fingerprint(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_jsonl(path):
    if not path.exists():
        return b"", []
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    event_ids = [row.get("event_id") for row in rows]
    if any(not value for value in event_ids) or len(event_ids) != len(set(event_ids)):
        raise ValueError(f"Invalid or duplicate event_id in {path.name}; journal requires review")
    return raw, rows


def atomic_append(path, original, events):
    if not events and path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    separator = b"\n" if original and not original.endswith(b"\n") else b""
    addition = b"".join(
        (json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        for event in events
    )
    raw = original + separator + addition
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _signal_payload(row, kickoff):
    payload = {field: str(row.get(field) or "") for field in SIGNAL_FIELDS}
    payload["kickoff_utc"] = kickoff.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    selected_market = match_winner_no_vig(
        row.get("trigger_b365_home"), row.get("trigger_b365_draw"), row.get("trigger_b365_away"),
        row.get("bet_selection"),
    )
    payload["trigger_selected_no_vig_probability"] = (
        float(selected_market) if selected_market is not None else None
    )
    return payload


def _signal_event(row, kickoff):
    payload = _signal_payload(row, kickoff)
    forward_id = payload["forward_id"]
    event_id = _event_id("SIGNAL_FROZEN", forward_id)
    return {
        "event_id": event_id,
        "event_type": "SIGNAL_FROZEN",
        "journal_version": JOURNAL_VERSION,
        "calculation_contract_version": CONTRACT_VERSION,
        "forward_id": forward_id,
        "frozen_at_utc": payload["screened_at_utc"],
        "source": "STAGE53_FORWARD_LOG",
        "immutable_fingerprint": _fingerprint(payload),
        "payload": payload,
    }


def _calculation_payload(signal_event, view, prediction):
    kickoff = parse_iso(signal_event["payload"].get("kickoff_utc"))
    if kickoff is None:
        return None
    created = parse_iso(prediction.get("created_at_utc"))
    trigger = parse_iso(prediction.get("trigger_captured_at_utc"))
    execution = parse_iso(view.get("paper_user_execution_at_utc"))
    if not created or not trigger or created >= kickoff or trigger >= kickoff:
        return None
    if prediction.get("status") != "FROZEN_PREMATCH":
        return None
    if str(prediction.get("kickoff_utc") or "") != signal_event["payload"].get("kickoff_utc"):
        return None

    executable = (
        view.get("user_execution_status") == "FROZEN"
        and execution is not None
        and execution < kickoff
        and bool(view.get("paper_user_execution_odds"))
    )
    value = evaluate_value(
        prediction.get("p_pbk"), prediction.get("p_market_no_vig"),
        view.get("paper_user_execution_odds"), executable=executable,
    )
    if value is None:
        return None
    return {
        "forward_id": signal_event["forward_id"],
        "signal_event_id": signal_event["event_id"],
        "prediction_id": str(prediction.get("prediction_id") or ""),
        "model_version": str(prediction.get("model_version") or ""),
        "rule": str(prediction.get("rule") or ""),
        "api_fixture_id": str(prediction.get("api_fixture_id") or ""),
        "selection": str(prediction.get("selection") or ""),
        "kickoff_utc": signal_event["payload"].get("kickoff_utc"),
        "prediction_created_at_utc": str(prediction.get("created_at_utc") or ""),
        "prediction_trigger_captured_at_utc": str(prediction.get("trigger_captured_at_utc") or ""),
        "paper_user_execution_at_utc": str(view.get("paper_user_execution_at_utc") or "") if executable else "",
        "paper_user_execution_bookmaker": str(view.get("paper_user_execution_bookmaker") or "") if executable else "",
        "paper_user_execution_odds": str(view.get("paper_user_execution_odds") or "") if executable else "",
        "p_market_no_vig": value["p_market_no_vig"],
        "p_pbk": value["p_model"],
        "edge": value["edge"],
        "edge_pp": value["edge_pp"],
        "ev": value["ev"],
        "ev_pct": value["ev_pct"],
        "value_rating": value["rating"],
        "value_tags": value["tags"],
        "creates_signal": False,
        "stake_changes": False,
        "eligibility_mutation": False,
    }


def _calculation_event(signal_event, view, prediction):
    payload = _calculation_payload(signal_event, view, prediction)
    if payload is None or not payload["prediction_id"]:
        return None
    event_id = _event_id("CALCULATION_FROZEN", signal_event["event_id"], payload["prediction_id"])
    return {
        "event_id": event_id,
        "event_type": "CALCULATION_FROZEN",
        "journal_version": JOURNAL_VERSION,
        "calculation_contract_version": CONTRACT_VERSION,
        "forward_id": signal_event["forward_id"],
        "frozen_at_utc": payload["prediction_created_at_utc"],
        "source": "STAGE75_FROZEN_PREMATCH+STAGE59_EXECUTION",
        "immutable_fingerprint": _fingerprint(payload),
        "payload": payload,
    }


def _settlement_event(signal_event, row, view):
    status = str(row.get("status") or "")
    if status not in {"SETTLED", "VOID"}:
        return None
    payload = {
        "forward_id": signal_event["forward_id"],
        "signal_event_id": signal_event["event_id"],
        "rule": str(row.get("rule") or ""),
        "api_fixture_id": str(row.get("api_fixture_id") or ""),
        "status": status,
        "result": str(row.get("result") or ""),
        "settled_at_utc": str(row.get("settled_at_utc") or ""),
        "market_profit_u": str(row.get("profit_u") or ""),
        "user_profit_u": str(view.get("user_profit_u") or "") if view else "",
        "paper_user_execution_status": str(view.get("user_execution_status") or "") if view else "",
    }
    event_id = _event_id("SETTLEMENT_FROZEN", signal_event["event_id"])
    return {
        "event_id": event_id,
        "event_type": "SETTLEMENT_FROZEN",
        "journal_version": JOURNAL_VERSION,
        "forward_id": signal_event["forward_id"],
        "frozen_at_utc": payload["settled_at_utc"],
        "source": "STAGE54_FORWARD_SETTLEMENT+STAGE59_USER_VIEW",
        "immutable_fingerprint": _fingerprint(payload),
        "payload": payload,
    }


def _compatible(existing, candidate):
    return existing.get("immutable_fingerprint") == candidate.get("immutable_fingerprint")


def materialize(ops=OPS, observed_at_utc=None):
    ops = Path(ops)
    observed = parse_iso(observed_at_utc or now_iso())
    if observed is None:
        raise ValueError("Forward journal observation requires an aware UTC timestamp")

    forward_path = ops / FORWARD.name
    user_path = ops / USER_VIEW.name
    prediction_path = ops / PREDICTIONS.name
    prematch_path = ops / PREMATCH_JOURNAL.name
    settlement_path = ops / SETTLEMENT_JOURNAL.name
    meta_path = ops / META.name
    lock_path = ops / ".pbk_forward_journal.lock"
    ops.mkdir(parents=True, exist_ok=True)

    lock = lock_path.open("x")
    try:
        with lock:
            forward = read_csv(forward_path)
            views = read_csv(user_path)
            predictions = read_csv(prediction_path)
            prematch_raw, prematch = read_jsonl(prematch_path)
            settlement_raw, settlements = read_jsonl(settlement_path)

            existing_prematch = {event["event_id"]: event for event in prematch}
            existing_settlements = {event["event_id"]: event for event in settlements}
            signals_by_forward = {
                event.get("forward_id"): event for event in prematch
                if event.get("event_type") == "SIGNAL_FROZEN" and event.get("forward_id")
            }
            views_by_forward = {row.get("forward_id"): row for row in views if row.get("forward_id")}
            predictions_by_key = {}
            for row in predictions:
                key = (str(row.get("rule") or ""), str(row.get("api_fixture_id") or ""), str(row.get("selection") or ""))
                predictions_by_key.setdefault(key, []).append(row)

            new_prematch = []
            new_settlements = []
            drift = 0
            skipped_after_kickoff = 0
            skipped_lookahead = 0

            # First pass: freeze new canonical signals only when first observed pre-match.
            for row in forward:
                forward_id = str(row.get("forward_id") or "").strip()
                kickoff = kickoff_from_forward(row)
                screened = parse_iso(row.get("screened_at_utc"))
                if not forward_id or kickoff is None or screened is None:
                    skipped_lookahead += 1
                    continue
                candidate = _signal_event(row, kickoff)
                existing = signals_by_forward.get(forward_id)
                if existing is not None:
                    if not _compatible(existing, candidate):
                        drift += 1
                    continue
                if observed >= kickoff:
                    skipped_after_kickoff += 1
                    continue
                if screened >= kickoff or screened > observed:
                    skipped_lookahead += 1
                    continue
                if candidate["event_id"] in existing_prematch:
                    raise ValueError("Signal event identity collision; journal requires review")
                new_prematch.append(candidate)
                existing_prematch[candidate["event_id"]] = candidate
                signals_by_forward[forward_id] = candidate

            # Second pass: freeze calculation evidence; never fabricate it after kickoff.
            all_signals = list(signals_by_forward.values())
            for signal in all_signals:
                payload = signal["payload"]
                kickoff = parse_iso(payload.get("kickoff_utc"))
                if kickoff is None:
                    continue
                view = views_by_forward.get(signal["forward_id"]) or {}
                key = (payload.get("rule", ""), payload.get("api_fixture_id", ""), payload.get("bet_selection", ""))
                for prediction in predictions_by_key.get(key, []):
                    candidate = _calculation_event(signal, view, prediction)
                    if candidate is None:
                        skipped_lookahead += 1
                        continue
                    existing = existing_prematch.get(candidate["event_id"])
                    if existing is not None:
                        if not _compatible(existing, candidate):
                            drift += 1
                        continue
                    if observed >= kickoff:
                        skipped_after_kickoff += 1
                        continue
                    frozen_at = parse_iso(candidate.get("frozen_at_utc"))
                    if frozen_at is None or frozen_at > observed:
                        skipped_lookahead += 1
                        continue
                    new_prematch.append(candidate)
                    existing_prematch[candidate["event_id"]] = candidate

            # Settlement is intentionally separate and is allowed only for a frozen signal.
            for row in forward:
                forward_id = str(row.get("forward_id") or "").strip()
                signal = signals_by_forward.get(forward_id)
                if signal is None:
                    continue
                candidate = _settlement_event(signal, row, views_by_forward.get(forward_id) or {})
                if candidate is None:
                    continue
                existing = existing_settlements.get(candidate["event_id"])
                if existing is not None:
                    if not _compatible(existing, candidate):
                        drift += 1
                    continue
                settled_at = parse_iso(candidate["payload"].get("settled_at_utc"))
                if settled_at is None or settled_at > observed:
                    skipped_lookahead += 1
                    continue
                new_settlements.append(candidate)
                existing_settlements[candidate["event_id"]] = candidate

            atomic_append(prematch_path, prematch_raw, new_prematch)
            atomic_append(settlement_path, settlement_raw, new_settlements)

            status = "ATTENTION" if drift else "OK"
            meta = {
                "run_at_utc": observed.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "status": status,
                "journal_version": JOURNAL_VERSION,
                "calculation_contract_version": CONTRACT_VERSION,
                "prematch_events_total": len(existing_prematch),
                "prematch_events_created": len(new_prematch),
                "settlement_events_total": len(existing_settlements),
                "settlement_events_created": len(new_settlements),
                "immutable_drift_detected": drift,
                "skipped_first_seen_at_or_after_kickoff": skipped_after_kickoff,
                "skipped_lookahead_or_invalid_time": skipped_lookahead,
                "historical_backfill": "FORBIDDEN",
                "api_calls": 0,
                "policy": {
                    "prematch_journal": "append-only; old bytes preserved exactly",
                    "settlement_journal": "separate append-only ledger; never mutates prematch evidence",
                    "source_drift": "fail visible; never overwrite frozen evidence",
                    "creates_signal": False,
                    "stake_changes": False,
                },
            }
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            return meta
    finally:
        lock_path.unlink(missing_ok=True)


def main():
    print(json.dumps(materialize(), ensure_ascii=False))


if __name__ == "__main__":
    main()
