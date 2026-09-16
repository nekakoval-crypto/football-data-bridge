#!/usr/bin/env python3
"""Validate PBK multi-market probability readiness governance."""
from __future__ import annotations
import json
from pathlib import Path

CFG = Path("config/pbk_market_probability_readiness.json")
CORE = Path("config/pbk_core_market_registry.json")
ALLOWED = {"VALIDATED", "PARTIAL_VALIDATED", "VALIDATION_PENDING", "DATA_ONLY", "NO_VALIDATED_MODEL"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(cfg, core):
    errors = []
    markets = cfg.get("markets") or []
    core_ids = {row.get("id") for row in (core.get("markets") or [])}
    rows = {row.get("id"): row for row in markets}
    if set(rows) != core_ids:
        errors.append(f"market ids must exactly match PBK_CORE_8: expected={sorted(core_ids)} actual={sorted(rows)}")
    if len(markets) != 8:
        errors.append(f"expected exactly 8 core market rows, got {len(markets)}")
    for mid, row in rows.items():
        status = row.get("pbk_probability_status")
        if status not in ALLOWED:
            errors.append(f"{mid}: invalid pbk_probability_status={status}")
        validated = row.get("validated_contexts") or []
        value_allowed = row.get("value_allowed")
        if status == "NO_VALIDATED_MODEL" and validated:
            errors.append(f"{mid}: NO_VALIDATED_MODEL cannot have validated_contexts")
        if status == "NO_VALIDATED_MODEL" and value_allowed != "NO":
            errors.append(f"{mid}: value must be forbidden without a validated PBK probability")
        if status in {"VALIDATED", "PARTIAL_VALIDATED"} and not validated:
            errors.append(f"{mid}: validated status requires explicit validated_contexts")
    one_x_two = rows.get("MATCH_RESULT_1X2") or {}
    required = {"R1_AWAY_WIN", "R2_AWAY_WIN", "R3_DRAW"}
    if one_x_two.get("pbk_probability_status") != "PARTIAL_VALIDATED":
        errors.append("MATCH_RESULT_1X2 must remain PARTIAL_VALIDATED until generic 1X2 models pass")
    if not required.issubset(set(one_x_two.get("validated_contexts") or [])):
        errors.append("MATCH_RESULT_1X2 must retain locked R1/R2/R3 validated contexts")
    for mid in core_ids - {"MATCH_RESULT_1X2"}:
        if (rows.get(mid) or {}).get("pbk_probability_status") == "VALIDATED":
            errors.append(f"{mid}: cannot be marked VALIDATED without a separate approved evidence update")
    guard = cfg.get("guardrails") or {}
    for key in ("no_probability_from_odds_only", "no_value_without_pbk_probability", "market_no_vig_is_not_pbk_probability", "no_auto_promotion", "canonical_rules_unchanged"):
        if guard.get(key) is not True:
            errors.append(f"guardrail must be true: {key}")
    if guard.get("missing_model_label") != "NO_VALIDATED_MODEL":
        errors.append("missing model label must be NO_VALIDATED_MODEL")
    return errors


def main():
    errors = validate(load(CFG), load(CORE))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("PBK market probability readiness: OK")


if __name__ == "__main__":
    main()
