#!/usr/bin/env python3
"""Stage80 — conservative PBK ↔ Transfermarkt player entity mapping.

This script is provider/network-free. It consumes:
- PBK historical_players.csv (API-Football identity namespace)
- optional PBK player_stats_snapshots.csv full-name evidence
- Transfermarkt players.csv(.gz)
- Transfermarkt transfers.csv(.gz)

AUTO/HIGH authority is intentionally narrow:
1. exact PBK catalog name + current club, or
2. exact non-abbreviated API-Football match-stat player name + same club,
   unique on both the PBK evidence side and Transfermarkt candidate side.

No fuzzy auto-join is allowed. Initial+surname matches remain REVIEW only.
"""
from __future__ import annotations

import csv
import gzip
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

VERSION = "PBK_STAGE80_TRANSFER_ENTITY_MAPPING_V3_PROFILE_NAME_DOB"
AUTO_METHOD_CATALOG = "EXACT_NAME_CURRENT_CLUB"
AUTO_METHOD_PROFILE = "EXACT_PROFILE_NAME_DOB_CURRENT_CLUB"
AUTO_METHOD_STATS = "EXACT_STATS_NAME_CURRENT_CLUB"
SAFE_AUTO_METHODS = {AUTO_METHOD_CATALOG, AUTO_METHOD_PROFILE, AUTO_METHOD_STATS}

MAPPING_FIELDS = [
    "pbk_player_id","pbk_player_name","pbk_latest_team_names",
    "pbk_evidence_name","pbk_evidence_team_name","pbk_evidence_birth_date","pbk_evidence_source",
    "transfermarkt_player_id","transfermarkt_player_name","transfermarkt_current_club_id",
    "transfermarkt_current_club_name","transfermarkt_date_of_birth","match_method","match_status","match_confidence",
    "name_key","team_key","candidate_count","mapping_version",
]
IDENTITY_FIELDS = [
    "pbk_player_id","pbk_player_name","transfermarkt_player_id","transfermarkt_player_name",
    "pbk_evidence_birth_date","transfermarkt_date_of_birth",
    "mapping_method","mapping_confidence","match_status","source","mapping_version",
]
TRANSFER_FIELDS = [
    "pbk_player_id","transfermarkt_player_id","player_name","transfer_date","transfer_season",
    "from_club_id","from_club_name","to_club_id","to_club_name","transfer_fee",
    "market_value_in_eur","mapping_method","mapping_confidence","source","projection_version",
]


def open_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def sval(row, key):
    return str((row or {}).get(key) or "").strip()


def normalize_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def team_alias_key(value):
    key = normalize_text(value)
    stop = {"fc","cf","afc","ac","sc","club","football","calcio"}
    parts = [p for p in key.split() if p not in stop]
    key = " ".join(parts)
    aliases = {
        "bayern munchen": "bayern munich",
        "inter milan": "inter",
        "internazionale": "inter",
        "atletico de madrid": "atletico madrid",
        "paris saint germain": "paris saint germain",
        "psg": "paris saint germain",
    }
    return aliases.get(key, key)


def initial_surname_key(name):
    key = normalize_text(name)
    parts = key.split()
    if len(parts) < 2:
        return ""
    first = parts[0][0] if parts[0] else ""
    surname = parts[-1]
    return f"{first} {surname}" if first and surname else ""


def is_non_abbreviated_name(name):
    raw = str(name or "").strip()
    if not raw:
        return False
    tokens = [token for token in re.split(r"\s+", raw) if token]
    if len(tokens) == 1:
        clean = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ0-9]", "", tokens[0])
        return len(clean) >= 3
    first = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ0-9]", "", tokens[0])
    return len(first) > 1


def pbk_team_names(row):
    raw = sval(row, "latest_roster_team_names")
    return [part.strip() for part in raw.split("|") if part.strip()]


def build_stats_aliases(player_stat_rows):
    aliases = defaultdict(dict)
    ownership = defaultdict(set)
    for row in player_stat_rows or []:
        pbk_id = sval(row, "player_id")
        name = sval(row, "player_name")
        team = sval(row, "team_name")
        if not pbk_id or not name or not team or not is_non_abbreviated_name(name):
            continue
        nk = normalize_text(name)
        tk = team_alias_key(team)
        if not nk or not tk:
            continue
        key = (nk, tk)
        ownership[key].add(pbk_id)
        aliases[pbk_id][key] = {
            "name": name,
            "team_name": team,
            "name_key": nk,
            "team_key": tk,
            "source": "API_FOOTBALL_FIXTURES_PLAYERS",
        }
    return {
        pbk_id: list(items.values())
        for pbk_id, items in aliases.items()
    }, ownership


def build_profile_aliases(player_profile_rows):
    aliases = defaultdict(dict)
    ownership = defaultdict(set)
    for row in player_profile_rows or []:
        pbk_id = sval(row, "player_id")
        first = sval(row, "firstname")
        last = sval(row, "lastname")
        display = sval(row, "player_name")
        name = " ".join(part for part in (first, last) if part).strip() or display
        team = sval(row, "team_name")
        birth_date = sval(row, "birth_date")
        if (
            not pbk_id or not name or not team or not birth_date
            or not is_non_abbreviated_name(name)
        ):
            continue
        nk = normalize_text(name)
        tk = team_alias_key(team)
        if not nk or not tk:
            continue
        key = (nk, tk, birth_date)
        ownership[key].add(pbk_id)
        aliases[pbk_id][key] = {
            "name": name,
            "team_name": team,
            "birth_date": birth_date,
            "name_key": nk,
            "team_key": tk,
            "source": "API_FOOTBALL_PLAYERS_TEAM_SEASON_PROFILE",
        }
    return {
        pbk_id: list(items.values())
        for pbk_id, items in aliases.items()
    }, ownership


def build_tm_indexes(tm_players):
    by_exact = defaultdict(list)
    by_initial_team = defaultdict(list)
    for tm in tm_players:
        pid = sval(tm, "player_id")
        name = sval(tm, "name") or " ".join(
            filter(None, [sval(tm, "first_name"), sval(tm, "last_name")])
        ).strip()
        club = sval(tm, "current_club_name")
        if not pid or not name:
            continue
        record = {
            "player_id": pid,
            "name": name,
            "current_club_id": sval(tm, "current_club_id"),
            "current_club_name": club,
            "date_of_birth": sval(tm, "date_of_birth"),
        }
        by_exact[normalize_text(name)].append(record)
        ik = initial_surname_key(name)
        tk = team_alias_key(club)
        if ik and tk:
            by_initial_team[(ik, tk)].append(record)
    return by_exact, by_initial_team


def build_mapping(pbk_rows, tm_players, player_stat_rows=None, player_profile_rows=None):
    by_exact, by_initial_team = build_tm_indexes(tm_players)
    profile_aliases, profile_ownership = build_profile_aliases(player_profile_rows or [])
    stats_aliases, stats_ownership = build_stats_aliases(player_stat_rows or [])

    rows = []
    provisional_auto_claims = defaultdict(set)

    for pbk in pbk_rows:
        pbk_id = sval(pbk, "player_id")
        pbk_name = sval(pbk, "latest_observed_name")
        teams = pbk_team_names(pbk)
        if not pbk_id or not pbk_name:
            continue

        nk = normalize_text(pbk_name)
        team_keys = [team_alias_key(x) for x in teams if team_alias_key(x)]
        exact = by_exact.get(nk, [])
        exact_team = [
            x for x in exact if team_alias_key(x["current_club_name"]) in team_keys
        ] if team_keys else []

        candidates = []
        method = status = confidence = ""
        evidence_name = pbk_name
        evidence_team = " | ".join(teams)
        evidence_birth_date = ""
        evidence_source = "historical_players.latest_observed_name"

        if len(exact_team) == 1:
            candidates = exact_team
            method = AUTO_METHOD_CATALOG
            status = "AUTO_MATCH"
            confidence = "HIGH"
        else:
            profile_matches = {}
            for alias in profile_aliases.get(pbk_id, []):
                key = (alias["name_key"], alias["team_key"], alias["birth_date"])
                if profile_ownership.get(key) != {pbk_id}:
                    continue
                tm_exact = by_exact.get(alias["name_key"], [])
                tm_team = [
                    x for x in tm_exact
                    if team_alias_key(x["current_club_name"]) == alias["team_key"]
                    and x.get("date_of_birth") == alias["birth_date"]
                ]
                if len(tm_team) == 1:
                    candidate = tm_team[0]
                    profile_matches[candidate["player_id"]] = (candidate, alias)

            if len(profile_matches) == 1:
                candidate, alias = next(iter(profile_matches.values()))
                candidates = [candidate]
                method = AUTO_METHOD_PROFILE
                status = "AUTO_MATCH"
                confidence = "HIGH"
                evidence_name = alias["name"]
                evidence_team = alias["team_name"]
                evidence_birth_date = alias["birth_date"]
                evidence_source = alias["source"]
            elif len(profile_matches) > 1:
                candidates = [item[0] for item in profile_matches.values()]
                method = "EXACT_PROFILE_NAME_DOB_CURRENT_CLUB_AMBIGUOUS"
                status = "REVIEW"
                confidence = "LOW"
                evidence_source = "API_FOOTBALL_PLAYERS_TEAM_SEASON_PROFILE"
            else:
                stats_matches = {}
                    for alias in stats_aliases.get(pbk_id, []):
                    key = (alias["name_key"], alias["team_key"])
                    if stats_ownership.get(key) != {pbk_id}:
                        continue
                    tm_exact = by_exact.get(alias["name_key"], [])
                    tm_team = [
                        x for x in tm_exact
                        if team_alias_key(x["current_club_name"]) == alias["team_key"]
                    ]
                    if len(tm_team) == 1:
                        candidate = tm_team[0]
                        stats_matches[candidate["player_id"]] = (candidate, alias)

                if len(stats_matches) == 1:
                    candidate, alias = next(iter(stats_matches.values()))
                    candidates = [candidate]
                    method = AUTO_METHOD_STATS
                    status = "AUTO_MATCH"
                    confidence = "HIGH"
                    evidence_name = alias["name"]
                    evidence_team = alias["team_name"]
                    evidence_source = alias["source"]
                elif len(stats_matches) > 1:
                    candidates = [item[0] for item in stats_matches.values()]
                    method = "EXACT_STATS_NAME_CURRENT_CLUB_AMBIGUOUS"
                    status = "REVIEW"
                    confidence = "LOW"
                    evidence_source = "API_FOOTBALL_FIXTURES_PLAYERS"
                elif len(exact) == 1:
                    candidates = exact
                    method = "EXACT_NAME_UNIQUE"
                    status = "REVIEW"
                    confidence = "MEDIUM"
                else:
                    ik = initial_surname_key(pbk_name)
                    initial_team = []
                    for tk in team_keys:
                        initial_team.extend(by_initial_team.get((ik, tk), []))
                    uniq = {x["player_id"]: x for x in initial_team}
                    initial_team = list(uniq.values())
                    if len(initial_team) == 1:
                        candidates = initial_team
                        method = "INITIAL_SURNAME_CURRENT_CLUB"
                        status = "REVIEW"
                        confidence = "MEDIUM"
                    elif exact:
                        candidates = exact
                        method = "EXACT_NAME_AMBIGUOUS"
                        status = "REVIEW"
                        confidence = "LOW"
                    else:
                        method = "NO_SAFE_CANDIDATE"
                        status = "UNMAPPED"
                        confidence = "NONE"

        if not candidates:
            rows.append({
                "pbk_player_id": pbk_id,
                "pbk_player_name": pbk_name,
                "pbk_latest_team_names": " | ".join(teams),
                "pbk_evidence_name": evidence_name,
                "pbk_evidence_team_name": evidence_team,
                "pbk_evidence_birth_date": evidence_birth_date,
                "pbk_evidence_source": evidence_source,
                "match_method": method,
                "match_status": status,
                "match_confidence": confidence,
                "name_key": normalize_text(evidence_name),
                "team_key": " | ".join(team_keys),
                "candidate_count": "0",
                "mapping_version": VERSION,
            })
            continue

        for candidate in sorted(candidates, key=lambda x: x["player_id"]):
            rows.append({
                "pbk_player_id": pbk_id,
                "pbk_player_name": pbk_name,
                "pbk_latest_team_names": " | ".join(teams),
                "pbk_evidence_name": evidence_name,
                "pbk_evidence_team_name": evidence_team,
                "pbk_evidence_birth_date": evidence_birth_date,
                "pbk_evidence_source": evidence_source,
                "transfermarkt_player_id": candidate["player_id"],
                "transfermarkt_player_name": candidate["name"],
                "transfermarkt_current_club_id": candidate["current_club_id"],
                "transfermarkt_current_club_name": candidate["current_club_name"],
                "transfermarkt_date_of_birth": candidate.get("date_of_birth", ""),
                "match_method": method,
                "match_status": status,
                "match_confidence": confidence,
                "name_key": normalize_text(evidence_name),
                "team_key": team_alias_key(evidence_team) if " | " not in evidence_team else " | ".join(team_keys),
                "candidate_count": str(len(candidates)),
                "mapping_version": VERSION,
            })
            if status == "AUTO_MATCH" and method in SAFE_AUTO_METHODS:
                provisional_auto_claims[candidate["player_id"]].add(pbk_id)

    collisions = {
        tm_id for tm_id, pbk_ids in provisional_auto_claims.items()
        if len(pbk_ids) != 1
    }
    if collisions:
        for row in rows:
            if (
                row.get("match_status") == "AUTO_MATCH"
                and row.get("transfermarkt_player_id") in collisions
            ):
                row["match_status"] = "REVIEW"
                row["match_method"] = row["match_method"] + "_PBK_COLLISION"
                row["match_confidence"] = "LOW"

    auto = {}
    for row in rows:
        if (
            row.get("match_status") == "AUTO_MATCH"
            and row.get("match_method") in SAFE_AUTO_METHODS
            and row.get("match_confidence") == "HIGH"
            and row.get("transfermarkt_player_id")
        ):
            auto[row["transfermarkt_player_id"]] = {
                "pbk_player_id": row["pbk_player_id"],
                "method": row["match_method"],
                "confidence": row["match_confidence"],
            }

    return rows, auto


def build_identity_map(mapping_rows):
    rows = []
    seen = set()
    for row in mapping_rows:
        pbk_id = sval(row, "pbk_player_id")
        tm_id = sval(row, "transfermarkt_player_id")
        method = sval(row, "match_method")
        if (
            sval(row, "match_status") != "AUTO_MATCH"
            or sval(row, "match_confidence") != "HIGH"
            or method not in SAFE_AUTO_METHODS
            or not pbk_id
            or not tm_id
        ):
            continue
        key = (pbk_id, tm_id)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "pbk_player_id": pbk_id,
            "pbk_player_name": sval(row, "pbk_player_name"),
            "transfermarkt_player_id": tm_id,
            "transfermarkt_player_name": sval(row, "transfermarkt_player_name"),
            "pbk_evidence_birth_date": sval(row, "pbk_evidence_birth_date"),
            "transfermarkt_date_of_birth": sval(row, "transfermarkt_date_of_birth"),
            "mapping_method": method,
            "mapping_confidence": "HIGH",
            "match_status": "AUTO_MATCH",
            "source": "stage80_transfer_entity_mapping",
            "mapping_version": VERSION,
        })
    rows.sort(key=lambda r: (r["pbk_player_id"], r["transfermarkt_player_id"]))
    return rows


def build_transfer_history(transfers, auto_mapping):
    output = []
    for row in transfers:
        tm_id = sval(row, "player_id")
        mapped = auto_mapping.get(tm_id)
        if not mapped:
            continue
        output.append({
            "pbk_player_id": mapped["pbk_player_id"],
            "transfermarkt_player_id": tm_id,
            "player_name": sval(row, "player_name"),
            "transfer_date": sval(row, "transfer_date"),
            "transfer_season": sval(row, "transfer_season"),
            "from_club_id": sval(row, "from_club_id"),
            "from_club_name": sval(row, "from_club_name"),
            "to_club_id": sval(row, "to_club_id"),
            "to_club_name": sval(row, "to_club_name"),
            "transfer_fee": sval(row, "transfer_fee"),
            "market_value_in_eur": sval(row, "market_value_in_eur"),
            "mapping_method": mapped["method"],
            "mapping_confidence": mapped["confidence"],
            "source": "dcaribou/transfermarkt-datasets:transfers",
            "projection_version": VERSION,
        })
    output.sort(
        key=lambda r: (
            r["pbk_player_id"],
            r["transfer_date"],
            r["transfermarkt_player_id"],
        )
    )
    return output


def run(
    pbk_path,
    players_path,
    transfers_path,
    mapping_out,
    transfers_out,
    meta_out,
    player_stats_path=None,
    player_profiles_path=None,
    identity_out=None,
):
    pbk = open_csv(pbk_path)
    players = open_csv(players_path)
    transfers = open_csv(transfers_path)
    player_stats = open_csv(player_stats_path) if player_stats_path else []
    player_profiles = open_csv(player_profiles_path) if player_profiles_path else []

    mapping, auto = build_mapping(pbk, players, player_stats, player_profiles)
    identities = build_identity_map(mapping)
    history = build_transfer_history(transfers, auto)
    write_csv(mapping_out, MAPPING_FIELDS, mapping)
    write_csv(transfers_out, TRANSFER_FIELDS, history)
    if identity_out:
        write_csv(identity_out, IDENTITY_FIELDS, identities)

    statuses = defaultdict(int)
    methods = defaultdict(int)
    for row in mapping:
        statuses[row["match_status"]] += 1
        methods[row["match_method"]] += 1

    auto_methods = defaultdict(int)
    for mapped in auto.values():
        auto_methods[mapped["method"]] += 1

    meta = {
        "version": VERSION,
        "pbk_players": len(pbk),
        "player_stat_rows": len(player_stats),
        "player_profile_rows": len(player_profiles),
        "transfermarkt_players": len(players),
        "transfer_source_rows": len(transfers),
        "mapping_candidate_rows": len(mapping),
        "auto_mapped_players": len(auto),
        "verified_identity_rows": len(identities),
        "auto_mapped_by_method": dict(sorted(auto_methods.items())),
        "normalized_transfer_rows": len(history),
        "mapping_status_rows": dict(sorted(statuses.items())),
        "mapping_method_rows": dict(sorted(methods.items())),
        "auto_match_policy": "EXACT_NAME_CURRENT_CLUB_OR_EXACT_PROFILE_NAME_DOB_CURRENT_CLUB_OR_EXACT_STATS_NAME_CURRENT_CLUB_UNIQUE_ONLY",
        "review_only_methods": [
            "EXACT_NAME_UNIQUE",
            "INITIAL_SURNAME_CURRENT_CLUB",
            "EXACT_NAME_AMBIGUOUS",
            "EXACT_PROFILE_NAME_DOB_CURRENT_CLUB_AMBIGUOUS",
            "EXACT_STATS_NAME_CURRENT_CLUB_AMBIGUOUS",
        ],
        "fuzzy_auto_match": False,
        "profile_name_requires_non_abbreviated": True,
        "profile_name_requires_exact_birth_date": True,
        "profile_name_requires_same_club": True,
        "profile_name_requires_unique_pbk_evidence_owner": True,
        "stats_name_requires_non_abbreviated": True,
        "stats_name_requires_same_club": True,
        "stats_name_requires_unique_pbk_evidence_owner": True,
        "current_operational_authority": False,
        "creates_signal": False,
        "probability_mutation": False,
        "eligibility_mutation": False,
        "stake_changes": False,
        "forward_journal_mutation": False,
    }
    Path(meta_out).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--pbk", required=True)
    p.add_argument("--players", required=True)
    p.add_argument("--transfers", required=True)
    p.add_argument("--player-stats", default="")
    p.add_argument("--player-profiles", default="")
    p.add_argument("--identity-out", default="")
    p.add_argument("--mapping-out", required=True)
    p.add_argument("--transfers-out", required=True)
    p.add_argument("--meta-out", required=True)
    a = p.parse_args()

    print(json.dumps(run(
        a.pbk,
        a.players,
        a.transfers,
        a.mapping_out,
        a.transfers_out,
        a.meta_out,
        player_stats_path=a.player_stats or None,
        player_profiles_path=a.player_profiles or None,
        identity_out=a.identity_out or None,
    ), ensure_ascii=False))


if __name__ == "__main__":
    main()
