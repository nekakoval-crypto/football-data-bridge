#!/usr/bin/env python3
"""Stage80 — conservative Transfermarkt club -> PBK16 API-Football team identity.

Consumes only bounded temporal-club rows. PBK16 scope is derived from the
saved Stage71 league catalog plus saved current-round fixtures. No provider
calls, no player-current-club inference, no fuzzy similarity.

A club is mapped only when a deterministic normalized/exact alias key resolves
to exactly one API-Football team inside PBK16. Everything else fails closed.
"""
from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

OPS = Path(os.getenv("OPS_DIR", "ops"))
TEMPORAL = OPS / "international_duty_player_temporal_club.csv"
LEAGUES = OPS / "stage71_league_catalog.csv"
FIXTURES = OPS / "current_round_fixtures.csv"
TEAM_STATS = OPS / "team_match_statistics.csv"
OUTPUT = OPS / "international_duty_player_pbk16_club_identity.csv"
META = OPS / "stage80_international_duty_pbk16_club_identity_last_run.json"

VERSION = "PBK_STAGE80_INTERNATIONAL_DUTY_PBK16_CLUB_IDENTITY_V1_EXACT_ALIAS_UNIQUE"

FIELDS = [
    "fixture_id","kickoff_utc","player_id","player_name",
    "transfermarkt_club_id","transfermarkt_club_name",
    "pbk16_club_identity_status","pbk16_team_id","pbk16_team_name",
    "pbk16_provider_league_id","identity_method","identity_key",
    "candidate_count","provider_calls","research_only",
    "operational_betting_authority","creates_signal","probability_mutation",
    "eligibility_mutation","stake_changes","forward_journal_mutation",
]

ALIASES = {
    "atletico": "atletico madrid",
    "bayern munich": "bayern munchen",
    "birmingham": "birmingham city",
    "brondby if": "brondby",
    "copenhagen": "fc copenhagen",
    "leipzig": "rb leipzig",
    "man city": "manchester city",
    "psv": "psv eindhoven",
    "r strasbourg": "strasbourg",
    "roma": "as roma",
    "rosenborg bk": "rosenborg",
    "salzburg": "red bull salzburg",
    "sevilla fc": "sevilla",
    "spezia calcio": "spezia",
    "stuttgart": "vfb stuttgart",
    "wolfsburg": "vfl wolfsburg",
    "wolves": "wolverhampton",
}

LEGAL_TOKENS = {"fc", "cf", "afc", "ac", "sc", "club", "football", "calcio"}


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def normalize_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def identity_key(value):
    key = normalize_text(value)
    parts = [p for p in key.split() if p not in LEGAL_TOKENS]
    key = " ".join(parts)
    return ALIASES.get(key, key)


def team_id_from_logo(url):
    match = re.search(r"/teams/(\d+)\.png(?:\?.*)?$", str(url or ""))
    return match.group(1) if match else ""


def build_pbk16_catalog(league_rows, fixture_rows, team_stat_rows=None):
    pbk_leagues = {
        sval(row, "api_league_id")
        for row in league_rows
        if sval(row, "resolved") == "YES" and sval(row, "api_league_id")
    }
    by_key = defaultdict(dict)
    for row in fixture_rows:
        league_id = sval(row, "provider_league_id")
        if league_id not in pbk_leagues:
            continue
        for side in ("home", "away"):
            name = sval(row, f"{side}_team")
            team_id = team_id_from_logo(sval(row, f"{side}_team_logo_url"))
            key = identity_key(name)
            if not name or not team_id or not key:
                continue
            by_key[key][team_id] = {
                "team_id": team_id,
                "team_name": name,
                "provider_league_id": league_id,
            }
    for row in team_stat_rows or []:
        league_id = sval(row, "provider_league_id")
        if league_id not in pbk_leagues:
            continue
        name = sval(row, "team_name")
        team_id = sval(row, "team_id")
        key = identity_key(name)
        if not name or not team_id or not key:
            continue
        by_key[key][team_id] = {
            "team_id": team_id,
            "team_name": name,
            "provider_league_id": league_id,
        }
    return by_key


def build(temporal_rows, league_rows, fixture_rows, team_stat_rows=None):
    catalog = build_pbk16_catalog(league_rows, fixture_rows, team_stat_rows or [])
    output = []
    for row in temporal_rows:
        if sval(row, "temporal_club_status") != "BOUNDED_CHAIN_CONFIRMED":
            continue
        tm_name = sval(row, "transfermarkt_club_name")
        key = identity_key(tm_name)
        candidates = list(catalog.get(key, {}).values())
        if len(candidates) == 1:
            candidate = candidates[0]
            status = "PBK16_EXACT_ALIAS_UNIQUE"
            method = "EXACT_NORMALIZED_OR_EXPLICIT_ALIAS_UNIQUE"
        elif len(candidates) > 1:
            candidate = {}
            status = "AMBIGUOUS_PBK16_TEAM"
            method = "FAIL_CLOSED_AMBIGUOUS"
        else:
            candidate = {}
            status = "OUTSIDE_PBK16_OR_UNMAPPED"
            method = "NO_PBK16_CANDIDATE"
        output.append({
            "fixture_id": sval(row, "fixture_id"),
            "kickoff_utc": sval(row, "kickoff_utc"),
            "player_id": sval(row, "player_id"),
            "player_name": sval(row, "player_name"),
            "transfermarkt_club_id": sval(row, "transfermarkt_club_id"),
            "transfermarkt_club_name": tm_name,
            "pbk16_club_identity_status": status,
            "pbk16_team_id": candidate.get("team_id", ""),
            "pbk16_team_name": candidate.get("team_name", ""),
            "pbk16_provider_league_id": candidate.get("provider_league_id", ""),
            "identity_method": method,
            "identity_key": key,
            "candidate_count": str(len(candidates)),
            "provider_calls": "0",
            "research_only": "true",
            "operational_betting_authority": "false",
            "creates_signal": "false",
            "probability_mutation": "false",
            "eligibility_mutation": "false",
            "stake_changes": "false",
            "forward_journal_mutation": "false",
        })
    output.sort(key=lambda r: (r["kickoff_utc"], r["fixture_id"], r["player_id"]))
    return output


def run(temporal_path=TEMPORAL, league_path=LEAGUES, fixture_path=FIXTURES,
        team_stats_path=TEAM_STATS, output_path=OUTPUT, meta_path=META):
    temporal = read_csv(temporal_path)
    leagues = read_csv(league_path)
    fixtures = read_csv(fixture_path)
    team_stats = read_csv(team_stats_path)
    rows = build(temporal, leagues, fixtures, team_stats)
    keys = [(sval(r, "fixture_id"), sval(r, "player_id")) for r in rows]
    duplicate_rows = len(keys) - len(set(keys))
    counts = Counter(sval(r, "pbk16_club_identity_status") for r in rows)
    mapped = sum(sval(r, "pbk16_club_identity_status") == "PBK16_EXACT_ALIAS_UNIQUE" for r in rows)
    invalid = sum(
        not (
            sval(r, "fixture_id")
            and sval(r, "player_id")
            and sval(r, "transfermarkt_club_name")
            and sval(r, "pbk16_club_identity_status")
            and sval(r, "provider_calls") == "0"
            and sval(r, "research_only") == "true"
            and sval(r, "operational_betting_authority") == "false"
        )
        for r in rows
    )
    meta = {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "OK" if rows and not duplicate_rows and not invalid else "ATTENTION",
        "bounded_input_rows": len(rows),
        "pbk16_catalog_fixture_rows": len(fixtures),
        "pbk16_catalog_team_stat_rows": len(team_stats),
        "output_rows": len(rows),
        "mapped_pbk16_rows": mapped,
        "mapped_pbk16_players": len({
            sval(r, "player_id") for r in rows
            if sval(r, "pbk16_club_identity_status") == "PBK16_EXACT_ALIAS_UNIQUE"
        }),
        "mapped_pbk16_coverage_pct": round(mapped / len(rows) * 100, 4) if rows else 0.0,
        "status_counts": dict(sorted(counts.items())),
        "duplicate_fixture_player_rows": duplicate_rows,
        "invalid_output_rows": invalid,
        "exact_or_explicit_alias_only": True,
        "fuzzy_matching_used": False,
        "current_player_club_used_for_identity": False,
        "provider_calls": 0,
        "research_only": True,
        "operational_betting_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
        "next_stage": "Derive international-duty club return/load features for PBK16-mapped bounded rows only.",
    }
    write_csv(output_path, rows)
    write_json(meta_path, meta)
    return meta


def main():
    print(json.dumps(run(), ensure_ascii=False))


if __name__ == "__main__":
    main()
