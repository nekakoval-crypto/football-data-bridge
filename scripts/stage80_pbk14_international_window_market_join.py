#!/usr/bin/env python3
"""Stage80 — PBK14 historical market × PBK16 international-window context join.

Only conservative AUTO/HIGH fixture identities are admitted.

The join is deterministic:
- Football-Data normalized historical market row by historical_match_id;
- PBK14 identity bridge AUTO/HIGH row by historical_match_id;
- PBK16 calendar-level international-window row by API-Football domestic fixture_id.

REVIEW/UNMAPPED bridge rows are excluded by construction. Calendar proximity is
not evidence that any player was called up, travelled, appeared for a national
team, played minutes, or returned at a particular time. Player-level
international participation must remain UNVERIFIED in this contour.

Final scores used by identity resolution never become international-window
features. The context is calendar-level, match-result independent and
no-lookahead.

This is research-only and cannot create probability, EV/value, R1/R2/R3
eligibility, WATCH/promotion state, stake or Forward journal entries.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

VERSION = "PBK_STAGE80_PBK14_INTERNATIONAL_WINDOW_MARKET_JOIN_V2"
ELIGIBLE = {"AUTO", "HIGH"}

MARKET_FIELDS = [
    "historical_match_id", "league_code", "league_name", "country", "season_label",
    "date_iso", "time_local", "home_team", "away_team",
    "ft_home_goals", "ft_away_goals", "ft_result",
    "b365_close_home", "b365_close_draw", "b365_close_away",
    "avg_close_home", "avg_close_draw", "avg_close_away",
    "b365_close_over_25", "b365_close_under_25",
    "avg_close_over_25", "avg_close_under_25",
]

INTERNATIONAL_FIELDS = [
    "nearest_window_id", "window_start_utc", "window_end_utc",
    "window_max_matches", "window_notes", "window_relation",
    "window_reference_contract",
    "hours_to_window_start", "hours_since_window_end",
    "within_72h_before_window", "within_96h_before_window",
    "within_7d_before_window", "within_72h_after_window",
    "within_96h_after_window", "within_7d_after_window",
    "home_domestic_matches_since_window_end_before_fixture",
    "away_domestic_matches_since_window_end_before_fixture",
    "home_first_domestic_league_match_after_window",
    "away_first_domestic_league_match_after_window",
    "both_first_domestic_league_match_after_window",
    "either_first_domestic_league_match_after_window",
    "player_level_international_status", "player_level_reason",
    "final_tournaments_included", "non_uefa_only_windows_included",
    "calendar_reference_version", "calendar_source_count",
]

FIELDS = [
    "historical_match_id", "api_fixture_id", "mapping_status", "mapping_reason",
    "provider_league_id", "season_start", "api_kickoff_utc",
    *[x for x in MARKET_FIELDS if x != "historical_match_id"],
    *INTERNATIONAL_FIELDS,
    "calendar_level_only", "as_known_calendar_reference",
    "no_match_result_dependency", "no_lookahead", "context_provider_calls",
    "identity_final_score_evidence_only", "fuzzy_string_matching_used",
    "one_to_one_verified", "historical_backfill_only", "research_only",
    "operational_betting_authority", "creates_signal", "probability_mutation",
    "eligibility_mutation", "stake_changes", "forward_journal_mutation",
]


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def is_true(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def is_false(value):
    return str(value or "").strip().lower() in {"0", "false", "no", "n"}


def is_zero(value):
    try:
        return int(str(value or "0").strip()) == 0
    except ValueError:
        return False


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def unique_index(rows, key):
    out = {}
    duplicates = set()
    for row in rows:
        value = sval(row, key)
        if not value:
            continue
        if value in out:
            duplicates.add(value)
        else:
            out[value] = row
    return out, duplicates


def valid_bridge_row(row):
    return (
        sval(row, "historical_match_id")
        and sval(row, "api_fixture_id")
        and sval(row, "mapping_status") in ELIGIBLE
        and sval(row, "fuzzy_string_matching_used") == "false"
        and is_true(row.get("one_to_one_verified"))
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    )


def valid_context_row(row):
    return (
        sval(row, "domestic_fixture_id")
        and sval(row, "window_reference_contract") == "NEAREST_WINDOW_RELATION_GATED_V2"
        and sval(row, "player_level_international_status") == "UNVERIFIED"
        and is_false(row.get("final_tournaments_included"))
        and is_false(row.get("non_uefa_only_windows_included"))
        and is_true(row.get("calendar_level_only"))
        and is_true(row.get("as_known_calendar_reference"))
        and is_true(row.get("no_match_result_dependency"))
        and is_true(row.get("no_lookahead"))
        and is_zero(row.get("provider_calls"))
        and is_true(row.get("historical_backfill_only"))
        and is_true(row.get("research_only"))
        and not is_true(row.get("operational_betting_authority"))
        and not is_true(row.get("creates_signal"))
        and not is_true(row.get("probability_mutation"))
        and not is_true(row.get("eligibility_mutation"))
        and not is_true(row.get("stake_changes"))
        and not is_true(row.get("forward_journal_mutation"))
    )


def project(markets, bridge, context):
    market_by_id, market_dupes = unique_index(markets, "historical_match_id")
    valid_context = [r for r in context if valid_context_row(r)]
    context_by_id, context_dupes = unique_index(valid_context, "domestic_fixture_id")
    invalid_context_rows = len(context) - len(valid_context)

    bridge_eligible = [r for r in bridge if valid_bridge_row(r)]
    bridge_by_mid, bridge_mid_dupes = unique_index(bridge_eligible, "historical_match_id")
    bridge_fixture_counts = Counter(sval(r, "api_fixture_id") for r in bridge_eligible)
    bridge_fixture_dupes = {k for k, v in bridge_fixture_counts.items() if k and v > 1}

    rows = []
    missing_market = []
    missing_context = []
    for mid, b in sorted(bridge_by_mid.items()):
        fixture_id = sval(b, "api_fixture_id")
        m = market_by_id.get(mid)
        ctx = context_by_id.get(fixture_id)
        if m is None:
            missing_market.append(mid)
            continue
        if ctx is None:
            missing_context.append(fixture_id)
            continue

        out = {
            "historical_match_id": mid,
            "api_fixture_id": fixture_id,
            "mapping_status": sval(b, "mapping_status"),
            "mapping_reason": sval(b, "mapping_reason"),
            "provider_league_id": sval(b, "provider_league_id"),
            "season_start": sval(b, "season_start"),
            "api_kickoff_utc": sval(b, "api_kickoff_utc"),
        }
        for field in MARKET_FIELDS:
            if field != "historical_match_id":
                out[field] = sval(m, field)
        for field in INTERNATIONAL_FIELDS:
            out[field] = sval(ctx, field)

        out.update({
            "calendar_level_only": "true",
            "as_known_calendar_reference": "true",
            "no_match_result_dependency": "true",
            "no_lookahead": "true",
            "context_provider_calls": "0",
            "identity_final_score_evidence_only": "true",
            "fuzzy_string_matching_used": "false",
            "one_to_one_verified": "true",
            "historical_backfill_only": "true",
            "research_only": "true",
            "operational_betting_authority": "false",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        })
        rows.append(out)

    rows.sort(key=lambda r: (r["date_iso"], r["league_code"], r["home_team"], r["away_team"]))
    diagnostics = {
        "market_rows": len(markets),
        "market_duplicate_ids": len(market_dupes),
        "bridge_rows": len(bridge),
        "bridge_eligible_rows": len(bridge_eligible),
        "bridge_eligible_unique_historical_ids": len(bridge_by_mid),
        "bridge_eligible_duplicate_historical_ids": len(bridge_mid_dupes),
        "bridge_eligible_duplicate_api_fixture_ids": len(bridge_fixture_dupes),
        "context_rows": len(context),
        "context_valid_rows": len(valid_context),
        "context_invalid_rows": invalid_context_rows,
        "context_duplicate_fixture_ids": len(context_dupes),
        "joined_rows": len(rows),
        "missing_market_rows": len(missing_market),
        "missing_context_rows": len(missing_context),
        "missing_market_sample": missing_market[:20],
        "missing_context_sample": missing_context[:20],
    }
    return rows, diagnostics


def complete_triplet(row, keys):
    vals = []
    for key in keys:
        raw = sval(row, key)
        try:
            val = float(raw)
        except ValueError:
            return False
        if val <= 1.0:
            return False
        vals.append(val)
    return len(vals) == len(keys)


def has_close_1x2(row):
    return complete_triplet(row, ["avg_close_home", "avg_close_draw", "avg_close_away"]) or complete_triplet(
        row, ["b365_close_home", "b365_close_draw", "b365_close_away"]
    )


def has_close_total25(row):
    return complete_triplet(row, ["avg_close_over_25", "avg_close_under_25"]) or complete_triplet(
        row, ["b365_close_over_25", "b365_close_under_25"]
    )


def build_meta(rows, diag):
    by_league = defaultdict(int)
    by_season = defaultdict(int)
    by_mapping = Counter()
    by_relation = Counter()
    for row in rows:
        by_league[row["league_code"]] += 1
        by_season[row["season_start"]] += 1
        by_mapping[row["mapping_status"]] += 1
        by_relation[row["window_relation"] or "NONE"] += 1

    return {
        "version": VERSION,
        "generated_at_utc": iso_now(),
        **diag,
        "join_coverage_pct": round(100.0 * len(rows) / diag["bridge_eligible_rows"], 3)
        if diag["bridge_eligible_rows"] else 0.0,
        "rows_by_league": dict(sorted(by_league.items())),
        "rows_by_season_start": dict(sorted(by_season.items())),
        "rows_by_mapping_status": dict(sorted(by_mapping.items())),
        "rows_by_window_relation": dict(sorted(by_relation.items())),
        "closing_1x2_matches": sum(has_close_1x2(r) for r in rows),
        "closing_total25_matches": sum(has_close_total25(r) for r in rows),
        "inside_window_rows": sum(sval(r, "window_relation") == "INSIDE" for r in rows),
        "within_72h_before_rows": sum(is_true(r.get("within_72h_before_window")) for r in rows),
        "within_96h_before_rows": sum(is_true(r.get("within_96h_before_window")) for r in rows),
        "within_7d_before_rows": sum(is_true(r.get("within_7d_before_window")) for r in rows),
        "within_72h_after_rows": sum(is_true(r.get("within_72h_after_window")) for r in rows),
        "within_96h_after_rows": sum(is_true(r.get("within_96h_after_window")) for r in rows),
        "within_7d_after_rows": sum(is_true(r.get("within_7d_after_window")) for r in rows),
        "home_first_domestic_after_window_rows": sum(
            is_true(r.get("home_first_domestic_league_match_after_window")) for r in rows
        ),
        "away_first_domestic_after_window_rows": sum(
            is_true(r.get("away_first_domestic_league_match_after_window")) for r in rows
        ),
        "both_first_domestic_after_window_rows": sum(
            is_true(r.get("both_first_domestic_league_match_after_window")) for r in rows
        ),
        "either_first_domestic_after_window_rows": sum(
            is_true(r.get("either_first_domestic_league_match_after_window")) for r in rows
        ),
        "window_reference_contract": "NEAREST_WINDOW_RELATION_GATED_V2",
        "player_level_international_status": "UNVERIFIED",
        "player_callup_inferred": False,
        "player_travel_inferred": False,
        "player_appearance_inferred": False,
        "review_unmapped_excluded": True,
        "fuzzy_string_matching_used": False,
        "calendar_level_only": True,
        "as_known_calendar_reference": True,
        "no_match_result_dependency": True,
        "no_lookahead": True,
        "provider_calls": 0,
        "historical_backfill_only": True,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }


def run(markets_path, bridge_path, context_path, out_csv, meta_out):
    markets = read_csv(markets_path)
    bridge = read_csv(bridge_path)
    context = read_csv(context_path)
    rows, diag = project(markets, bridge, context)
    write_csv(out_csv, rows)
    meta = build_meta(rows, diag)
    Path(meta_out).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--markets", required=True)
    p.add_argument("--bridge", default="ops/pbk14_football_data_fixture_bridge.csv")
    p.add_argument("--context", default="ops/pbk16_international_window_context_research.csv")
    p.add_argument("--out-csv", required=True)
    p.add_argument("--meta-out", required=True)
    a = p.parse_args()
    print(json.dumps(run(a.markets, a.bridge, a.context, a.out_csv, a.meta_out), ensure_ascii=False))


if __name__ == "__main__":
    main()
