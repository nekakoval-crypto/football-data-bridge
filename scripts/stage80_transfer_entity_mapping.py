#!/usr/bin/env python3
"""Stage80 — conservative PBK ↔ Transfermarkt player entity mapping.

This script is provider/network-free. It consumes:
- PBK historical_players.csv (API-Football identity namespace)
- Transfermarkt players.csv(.gz)
- Transfermarkt transfers.csv(.gz)

It emits auditable mapping candidates and a normalized transfer-history artifact
ONLY for high-confidence exact-name + current-club matches.

No fuzzy auto-join is allowed. Initial+surname matches are REVIEW candidates only.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

VERSION = "PBK_STAGE80_TRANSFER_ENTITY_MAPPING_V1"

MAPPING_FIELDS = [
    "pbk_player_id","pbk_player_name","pbk_latest_team_names",
    "transfermarkt_player_id","transfermarkt_player_name","transfermarkt_current_club_id",
    "transfermarkt_current_club_name","match_method","match_status","match_confidence",
    "name_key","team_key","candidate_count","mapping_version",
]
TRANSFER_FIELDS = [
    "pbk_player_id","transfermarkt_player_id","player_name","transfer_date","transfer_season",
    "from_club_id","from_club_name","to_club_id","to_club_name","transfer_fee",
    "market_value_in_eur","mapping_method","mapping_confidence","source","projection_version",
]


def open_csv(path):
    path = Path(path)
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
    return " ".join(parts)


def initial_surname_key(name):
    key = normalize_text(name)
    parts = key.split()
    if len(parts) < 2:
        return ""
    first = parts[0][0] if parts[0] else ""
    surname = parts[-1]
    return f"{first} {surname}" if first and surname else ""


def pbk_team_names(row):
    raw = sval(row, "latest_roster_team_names")
    return [part.strip() for part in raw.split("|") if part.strip()]


def build_mapping(pbk_rows, tm_players):
    by_exact = defaultdict(list)
    by_initial_team = defaultdict(list)
    for tm in tm_players:
        pid = sval(tm, "player_id")
        name = sval(tm, "name") or " ".join(filter(None, [sval(tm,"first_name"), sval(tm,"last_name")])).strip()
        club = sval(tm, "current_club_name")
        if not pid or not name:
            continue
        record = {
            "player_id": pid, "name": name,
            "current_club_id": sval(tm, "current_club_id"),
            "current_club_name": club,
        }
        by_exact[normalize_text(name)].append(record)
        ik = initial_surname_key(name)
        tk = team_alias_key(club)
        if ik and tk:
            by_initial_team[(ik, tk)].append(record)

    rows = []
    auto = {}
    for pbk in pbk_rows:
        pbk_id = sval(pbk, "player_id")
        pbk_name = sval(pbk, "latest_observed_name")
        teams = pbk_team_names(pbk)
        if not pbk_id or not pbk_name:
            continue
        nk = normalize_text(pbk_name)
        exact = by_exact.get(nk, [])
        team_keys = [team_alias_key(x) for x in teams if team_alias_key(x)]
        exact_team = [x for x in exact if team_alias_key(x["current_club_name"]) in team_keys] if team_keys else []
        candidates = []
        method = status = confidence = ""
        if len(exact_team) == 1:
            candidates = exact_team
            method = "EXACT_NAME_CURRENT_CLUB"
            status = "AUTO_MATCH"
            confidence = "HIGH"
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
                "pbk_player_id":pbk_id,"pbk_player_name":pbk_name,
                "pbk_latest_team_names":" | ".join(teams),
                "match_method":method,"match_status":status,"match_confidence":confidence,
                "name_key":nk,"team_key":" | ".join(team_keys),"candidate_count":"0",
                "mapping_version":VERSION,
            })
            continue

        for candidate in sorted(candidates, key=lambda x:x["player_id"]):
            rows.append({
                "pbk_player_id":pbk_id,"pbk_player_name":pbk_name,
                "pbk_latest_team_names":" | ".join(teams),
                "transfermarkt_player_id":candidate["player_id"],
                "transfermarkt_player_name":candidate["name"],
                "transfermarkt_current_club_id":candidate["current_club_id"],
                "transfermarkt_current_club_name":candidate["current_club_name"],
                "match_method":method,"match_status":status,"match_confidence":confidence,
                "name_key":nk,"team_key":" | ".join(team_keys),
                "candidate_count":str(len(candidates)),"mapping_version":VERSION,
            })
        if status == "AUTO_MATCH" and len(candidates) == 1:
            auto[candidates[0]["player_id"]] = {
                "pbk_player_id": pbk_id,
                "method": method,
                "confidence": confidence,
            }
    return rows, auto


def build_transfer_history(transfers, auto_mapping):
    output=[]
    for row in transfers:
        tm_id=sval(row,"player_id")
        mapped=auto_mapping.get(tm_id)
        if not mapped:
            continue
        output.append({
            "pbk_player_id":mapped["pbk_player_id"],
            "transfermarkt_player_id":tm_id,
            "player_name":sval(row,"player_name"),
            "transfer_date":sval(row,"transfer_date"),
            "transfer_season":sval(row,"transfer_season"),
            "from_club_id":sval(row,"from_club_id"),
            "from_club_name":sval(row,"from_club_name"),
            "to_club_id":sval(row,"to_club_id"),
            "to_club_name":sval(row,"to_club_name"),
            "transfer_fee":sval(row,"transfer_fee"),
            "market_value_in_eur":sval(row,"market_value_in_eur"),
            "mapping_method":mapped["method"],
            "mapping_confidence":mapped["confidence"],
            "source":"dcaribou/transfermarkt-datasets:transfers",
            "projection_version":VERSION,
        })
    output.sort(key=lambda r:(r["pbk_player_id"],r["transfer_date"],r["transfermarkt_player_id"]))
    return output


def run(pbk_path, players_path, transfers_path, mapping_out, transfers_out, meta_out):
    pbk=open_csv(pbk_path); players=open_csv(players_path); transfers=open_csv(transfers_path)
    mapping, auto=build_mapping(pbk,players)
    history=build_transfer_history(transfers,auto)
    write_csv(mapping_out,MAPPING_FIELDS,mapping)
    write_csv(transfers_out,TRANSFER_FIELDS,history)
    statuses=defaultdict(int)
    for row in mapping:
        statuses[row["match_status"]]+=1
    meta={
        "version":VERSION,
        "pbk_players":len(pbk),
        "transfermarkt_players":len(players),
        "transfer_source_rows":len(transfers),
        "mapping_candidate_rows":len(mapping),
        "auto_mapped_players":len(auto),
        "normalized_transfer_rows":len(history),
        "mapping_status_rows":dict(sorted(statuses.items())),
        "auto_match_policy":"EXACT_NAME_CURRENT_CLUB_UNIQUE_ONLY",
        "review_only_methods":["EXACT_NAME_UNIQUE","INITIAL_SURNAME_CURRENT_CLUB","EXACT_NAME_AMBIGUOUS"],
        "fuzzy_auto_match":False,
        "current_operational_authority":False,
        "creates_signal":False,
        "probability_mutation":False,
        "eligibility_mutation":False,
        "stake_changes":False,
        "forward_journal_mutation":False,
    }
    Path(meta_out).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    return meta


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--pbk",required=True); p.add_argument("--players",required=True); p.add_argument("--transfers",required=True)
    p.add_argument("--mapping-out",required=True); p.add_argument("--transfers-out",required=True); p.add_argument("--meta-out",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.pbk,a.players,a.transfers,a.mapping_out,a.transfers_out,a.meta_out),ensure_ascii=False))


if __name__=="__main__":
    main()
