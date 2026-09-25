#!/usr/bin/env python3
"""PBK #276 — environmental market expectation deviation research join.

Builds a compact durable research projection from:
- normalized Football-Data historical closing markets;
- conservative AUTO/HIGH API fixture identity bridge;
- Stage273 postmatch environmental mechanism dataset.

Primary total baseline is the no-vig closing O/U 2.5 market.
No expected-goals number is reverse-engineered from the line.

Research only. Historical backfill only. No predictive/betting/value authority.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "PBK_ENVIRONMENTAL_EXPECTATION_DEVIATION_V1"
ELIGIBLE_MAPPING = {"AUTO", "HIGH"}

FIELDS = [
    "api_fixture_id",
    "historical_match_id",
    "provider_league_id",
    "league_code",
    "league_name",
    "season_label",
    "date_iso",
    "api_kickoff_utc",
    "home_team",
    "away_team",

    "market_total_source",
    "close_over_25_odds",
    "close_under_25_odds",
    "p_over25_no_vig",
    "p_under25_no_vig",
    "total_market_expectation_band",

    "market_1x2_source",
    "close_home_odds",
    "close_draw_odds",
    "close_away_odds",
    "p_home_no_vig",
    "p_draw_no_vig",
    "p_away_no_vig",
    "market_favorite_side",
    "market_favorite_probability",

    "home_goals",
    "away_goals",
    "goals_total",
    "actual_over25",
    "actual_result",

    "over25_residual",
    "total_expectation_deviation_class",
    "favorite_result_alignment",

    "environment_source_class",
    "environment_geocode_quality_status",
    "environment_geocode_resolver_version",
    "temperature_mean_c",
    "apparent_temperature_mean_c",
    "relative_humidity_mean_pct",
    "dew_point_mean_c",
    "surface_pressure_mean_hpa",
    "precipitation_sum_mm",
    "rain_sum_mm",
    "showers_sum_mm",
    "snowfall_sum_cm",
    "visibility_min_m",
    "wind_speed_mean_kmh",
    "wind_speed_max_kmh",
    "wind_gust_mean_kmh",
    "wind_gust_max_kmh",
    "weather_code_mode",

    "shots_total",
    "shots_on_goal_total",
    "shots_outsidebox_total",
    "goalkeeper_saves_total",
    "corners_total",
    "passes_accuracy_mean",
    "expected_goals_total",
    "normal_goals",
    "penalty_goals",
    "own_goals",
    "red_card_events",
    "var_events",

    "expectation_source_is_prematch_market",
    "environment_source_is_postmatch_proxy",
    "causal_claim_authorized",
    "research_only",
    "historical_backfill_only",
    "predictive_authority",
    "betting_authority",
    "probability_mutation",
    "eligibility_mutation",
    "stake_changes",
    "forward_journal_mutation",
    "projection_version",
]


def iso_now():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def fnum(value):
    try:
        x = float(str(value).strip())
        return x
    except (TypeError, ValueError):
        return None


def fmt(value, digits=6):
    if value is None:
        return ""
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
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


def no_vig_pair(a, b):
    a = fnum(a)
    b = fnum(b)
    if a is None or b is None or a <= 1 or b <= 1:
        return None
    ra, rb = 1.0 / a, 1.0 / b
    total = ra + rb
    return (ra / total, rb / total)


def no_vig_triplet(h, d, a):
    vals = [fnum(h), fnum(d), fnum(a)]
    if any(v is None or v <= 1 for v in vals):
        return None
    raw = [1.0 / v for v in vals]
    total = sum(raw)
    return tuple(x / total for x in raw)


def pick_total_market(row):
    avg = no_vig_pair(row.get("avg_close_over_25"), row.get("avg_close_under_25"))
    if avg:
        return {
            "source": "FOOTBALL_DATA_AVG_CLOSING_OU25",
            "over_odds": sval(row, "avg_close_over_25"),
            "under_odds": sval(row, "avg_close_under_25"),
            "p_over": avg[0],
            "p_under": avg[1],
        }

    b365 = no_vig_pair(row.get("b365_close_over_25"), row.get("b365_close_under_25"))
    if b365:
        return {
            "source": "FOOTBALL_DATA_B365_CLOSING_OU25",
            "over_odds": sval(row, "b365_close_over_25"),
            "under_odds": sval(row, "b365_close_under_25"),
            "p_over": b365[0],
            "p_under": b365[1],
        }
    return None


def pick_1x2_market(row):
    avg = no_vig_triplet(
        row.get("avg_close_home"),
        row.get("avg_close_draw"),
        row.get("avg_close_away"),
    )
    if avg:
        odds = (
            sval(row, "avg_close_home"),
            sval(row, "avg_close_draw"),
            sval(row, "avg_close_away"),
        )
        source = "FOOTBALL_DATA_AVG_CLOSING_1X2"
        probs = avg
    else:
        b365 = no_vig_triplet(
            row.get("b365_close_home"),
            row.get("b365_close_draw"),
            row.get("b365_close_away"),
        )
        if not b365:
            return None
        odds = (
            sval(row, "b365_close_home"),
            sval(row, "b365_close_draw"),
            sval(row, "b365_close_away"),
        )
        source = "FOOTBALL_DATA_B365_CLOSING_1X2"
        probs = b365

    labels = ("H", "D", "A")
    idx = max(range(3), key=lambda i: probs[i])

    return {
        "source": source,
        "odds": odds,
        "probs": probs,
        "favorite_side": labels[idx],
        "favorite_probability": probs[idx],
    }


def expectation_band(p_over):
    if p_over is None:
        return "UNKNOWN"
    if p_over >= 0.55:
        return "OVER_LEAN"
    if p_over <= 0.45:
        return "UNDER_LEAN"
    return "BALANCED"


def actual_result(home_goals, away_goals):
    h = int(home_goals)
    a = int(away_goals)
    if h > a:
        return "H"
    if h < a:
        return "A"
    return "D"


def deviation_class(band, actual_over):
    if band == "OVER_LEAN":
        return "EXPECTED_OVER_ACTUAL_OVER" if actual_over else "EXPECTED_OVER_ACTUAL_UNDER"
    if band == "UNDER_LEAN":
        return "EXPECTED_UNDER_ACTUAL_OVER" if actual_over else "EXPECTED_UNDER_ACTUAL_UNDER"
    if band == "BALANCED":
        return "BALANCED_ACTUAL_OVER" if actual_over else "BALANCED_ACTUAL_UNDER"
    return "UNKNOWN"


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


def valid_bridge(row):
    return (
        sval(row, "api_fixture_id")
        and sval(row, "historical_match_id")
        and sval(row, "mapping_status") in ELIGIBLE_MAPPING
        and sval(row, "one_to_one_verified").lower() == "true"
        and sval(row, "fuzzy_string_matching_used").lower() == "false"
    )


def build_rows(markets, bridge, mechanisms):
    market_by_mid, market_dupes = unique_index(markets, "historical_match_id")
    mech_by_fixture, mech_dupes = unique_index(mechanisms, "fixture_id")

    bridge_rows = [r for r in bridge if valid_bridge(r)]

    rows = []
    diag = Counter()

    for b in bridge_rows:
        fixture_id = sval(b, "api_fixture_id")
        mid = sval(b, "historical_match_id")

        env = mech_by_fixture.get(fixture_id)
        if env is None:
            diag["bridge_without_stage273_mechanism"] += 1
            continue

        if (
            sval(env, "environment_geocode_quality_status")
            != "VERIFIED_LOCALITY_V4"
            or sval(env, "environment_geocode_resolver_version")
            != "PBK_GEOCODE_V4"
        ):
            diag["unverified_environment_geocode"] += 1
            continue

        market = market_by_mid.get(mid)
        if market is None:
            diag["stage273_without_market_row"] += 1
            continue

        total = pick_total_market(market)
        one = pick_1x2_market(market)

        if total is None:
            diag["missing_closing_ou25"] += 1
            continue

        try:
            hg = int(float(sval(env, "home_goals")))
            ag = int(float(sval(env, "away_goals")))
        except ValueError:
            diag["invalid_final_score"] += 1
            continue

        goals = hg + ag
        actual_over = goals >= 3
        band = expectation_band(total["p_over"])
        result = actual_result(hg, ag)

        if one:
            favorite_alignment = (
                "FAVORITE_RESULT_MATCH"
                if one["favorite_side"] == result
                else "FAVORITE_RESULT_MISS"
            )
        else:
            favorite_alignment = "UNKNOWN"

        row = {
            "api_fixture_id": fixture_id,
            "historical_match_id": mid,
            "provider_league_id": sval(b, "provider_league_id"),
            "league_code": sval(market, "league_code"),
            "league_name": sval(market, "league_name"),
            "season_label": sval(market, "season_label"),
            "date_iso": sval(market, "date_iso"),
            "api_kickoff_utc": sval(b, "api_kickoff_utc"),
            "home_team": sval(env, "home_team"),
            "away_team": sval(env, "away_team"),

            "market_total_source": total["source"],
            "close_over_25_odds": total["over_odds"],
            "close_under_25_odds": total["under_odds"],
            "p_over25_no_vig": fmt(total["p_over"]),
            "p_under25_no_vig": fmt(total["p_under"]),
            "total_market_expectation_band": band,

            "market_1x2_source": one["source"] if one else "",
            "close_home_odds": one["odds"][0] if one else "",
            "close_draw_odds": one["odds"][1] if one else "",
            "close_away_odds": one["odds"][2] if one else "",
            "p_home_no_vig": fmt(one["probs"][0]) if one else "",
            "p_draw_no_vig": fmt(one["probs"][1]) if one else "",
            "p_away_no_vig": fmt(one["probs"][2]) if one else "",
            "market_favorite_side": one["favorite_side"] if one else "",
            "market_favorite_probability": fmt(one["favorite_probability"]) if one else "",

            "home_goals": str(hg),
            "away_goals": str(ag),
            "goals_total": str(goals),
            "actual_over25": "true" if actual_over else "false",
            "actual_result": result,

            "over25_residual": fmt((1.0 if actual_over else 0.0) - total["p_over"]),
            "total_expectation_deviation_class": deviation_class(band, actual_over),
            "favorite_result_alignment": favorite_alignment,

            "environment_source_class": sval(env, "environment_source_class"),
            "environment_geocode_quality_status": sval(env, "environment_geocode_quality_status"),
            "environment_geocode_resolver_version": sval(env, "environment_geocode_resolver_version"),
            "temperature_mean_c": sval(env, "temperature_mean_c"),
            "apparent_temperature_mean_c": sval(env, "apparent_temperature_mean_c"),
            "relative_humidity_mean_pct": sval(env, "relative_humidity_mean_pct"),
            "dew_point_mean_c": sval(env, "dew_point_mean_c"),
            "surface_pressure_mean_hpa": sval(env, "surface_pressure_mean_hpa"),
            "precipitation_sum_mm": sval(env, "precipitation_sum_mm"),
            "rain_sum_mm": sval(env, "rain_sum_mm"),
            "showers_sum_mm": sval(env, "showers_sum_mm"),
            "snowfall_sum_cm": sval(env, "snowfall_sum_cm"),
            "visibility_min_m": sval(env, "visibility_min_m"),
            "wind_speed_mean_kmh": sval(env, "wind_speed_mean_kmh"),
            "wind_speed_max_kmh": sval(env, "wind_speed_max_kmh"),
            "wind_gust_mean_kmh": sval(env, "wind_gust_mean_kmh"),
            "wind_gust_max_kmh": sval(env, "wind_gust_max_kmh"),
            "weather_code_mode": sval(env, "weather_code_mode"),

            "shots_total": sval(env, "shots_total"),
            "shots_on_goal_total": sval(env, "shots_on_goal_total"),
            "shots_outsidebox_total": sval(env, "shots_outsidebox_total"),
            "goalkeeper_saves_total": sval(env, "goalkeeper_saves_total"),
            "corners_total": sval(env, "corners_total"),
            "passes_accuracy_mean": sval(env, "passes_accuracy_mean"),
            "expected_goals_total": sval(env, "expected_goals_total"),
            "normal_goals": sval(env, "normal_goals"),
            "penalty_goals": sval(env, "penalty_goals"),
            "own_goals": sval(env, "own_goals"),
            "red_card_events": sval(env, "red_card_events"),
            "var_events": sval(env, "var_events"),

            "expectation_source_is_prematch_market": "true",
            "environment_source_is_postmatch_proxy": "true",
            "causal_claim_authorized": "false",
            "research_only": "true",
            "historical_backfill_only": "true",
            "predictive_authority": "NOT_AUTHORIZED",
            "betting_authority": "NOT_AUTHORIZED",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
            "projection_version": VERSION,
        }

        rows.append(row)
        diag["joined_expectation_environment_rows"] += 1

    rows.sort(key=lambda r: (r["date_iso"], r["api_fixture_id"]))

    diagnostics = {
        **dict(diag),
        "market_rows": len(markets),
        "market_duplicate_historical_ids": len(market_dupes),
        "bridge_rows": len(bridge),
        "bridge_eligible_rows": len(bridge_rows),
        "mechanism_rows": len(mechanisms),
        "mechanism_duplicate_fixture_ids": len(mech_dupes),
    }
    return rows, diagnostics


def build_meta(rows, diagnostics):
    bands = Counter(r["total_market_expectation_band"] for r in rows)
    deviations = Counter(r["total_expectation_deviation_class"] for r in rows)
    sources = Counter(r["market_total_source"] for r in rows)

    return {
        "version": VERSION,
        "generated_at_utc": iso_now(),
        "status": "OK",
        **diagnostics,
        "expectation_band_counts": dict(sorted(bands.items())),
        "deviation_class_counts": dict(sorted(deviations.items())),
        "market_total_source_counts": dict(sorted(sources.items())),
        "primary_expectation_baseline": "CLOSING_OU25_NO_VIG_PROBABILITY",
        "expected_goals_reverse_engineered": False,
        "expectation_bands": {
            "UNDER_LEAN": "p_over25_no_vig <= 0.45",
            "BALANCED": "0.45 < p_over25_no_vig < 0.55",
            "OVER_LEAN": "p_over25_no_vig >= 0.55",
        },
        "primary_deviation_measure": "actual_over25_binary - p_over25_no_vig",
        "causal_claim_authorized": False,
        "research_only": True,
        "historical_backfill_only": True,
        "predictive_authority": "NOT_AUTHORIZED",
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "next_stage": (
            "Pre-register environment-conditioned comparisons of market expectation residuals "
            "and match mechanisms; any operational use must still validate prospectively via Stage272."
        ),
    }


def run(markets_path, bridge_path, mechanisms_path, out_csv, meta_out):
    rows, diagnostics = build_rows(
        read_csv(markets_path),
        read_csv(bridge_path),
        read_csv(mechanisms_path),
    )
    write_csv(out_csv, rows)
    meta = build_meta(rows, diagnostics)
    Path(meta_out).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return meta


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--markets", required=True)
    p.add_argument("--bridge", required=True)
    p.add_argument(
        "--mechanisms",
        default="ops/environmental_postmatch_mechanism_dataset.csv",
    )
    p.add_argument(
        "--out-csv",
        default="ops/environmental_expectation_deviation_research.csv",
    )
    p.add_argument(
        "--meta-out",
        default="ops/stage276_environmental_expectation_deviation_last_run.json",
    )
    a = p.parse_args()

    print(
        json.dumps(
            run(
                a.markets,
                a.bridge,
                a.mechanisms,
                a.out_csv,
                a.meta_out,
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
