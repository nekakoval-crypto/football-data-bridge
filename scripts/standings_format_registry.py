#!/usr/bin/env python3
"""Season-scoped verified competition-format facts for standings motivation.

This registry is deliberately conservative.  Only formats verified from official
competition/federation sources are marked VERIFIED.  Split/phase competitions
remain UNKNOWN until PBK has a phase-aware format contract.
"""
from __future__ import annotations


VERIFIED_FORMATS = {
    # England — Premier League: 20 clubs, each club plays 38 league matches.
    ("39", "2026"): {
        "status": "VERIFIED", "total_games": 38,
        "reason": "Official 2026/27 Premier League format: each club plays 38 matches.",
        "source": "https://www.premierleague.com/en/news/58905",
    },
    # Spain — LALIGA EA SPORTS official 2026/27 calendar ends at Matchday 38.
    ("140", "2026"): {
        "status": "VERIFIED", "total_games": 38,
        "reason": "Official LALIGA 2026/27 calendar has 38 matchdays.",
        "source": "https://www.laliga.com/calendar-2026-2027/laliga-easports",
    },
    # Italy — Lega Serie A explicitly states 20 teams / 38 matchdays.
    ("135", "2026"): {
        "status": "VERIFIED", "total_games": 38,
        "reason": "Official Serie A 2026/27 format: 20 teams and 38 matchdays.",
        "source": "https://en.legaseriea.it/serie-a/news/looking-forward-to-the-2026-27-serie-a-fixture-list",
    },
    # Germany — Bundesliga official 2026/27 schedule ends at Matchday 34.
    ("78", "2026"): {
        "status": "VERIFIED", "total_games": 34,
        "reason": "Official Bundesliga 2026/27 schedule has 34 matchdays.",
        "source": "https://www.bundesliga.com/en/bundesliga/news/2026-27-season-fixture-schedules-37671/",
    },
    # France — LFP explicitly identifies Matchday 34 as the final matchday.
    ("61", "2026"): {
        "status": "VERIFIED", "total_games": 34,
        "reason": "Official Ligue 1 2026/27 calendar has 34 matchdays.",
        "source": "https://ligue1.com/en/articles/l1_article_3812-",
    },
    # Netherlands — official Eredivisie fixture list covers 34 matchweeks.
    ("88", "2026"): {
        "status": "VERIFIED", "total_games": 34,
        "reason": "Official Eredivisie 2026/27 fixture list covers 34 matchweeks.",
        "source": "https://eredivisie.com/news/full-provisional-fixture-list-for-the-2026-27-eredivisie-season-announced/",
    },
    # Norway — NFF official 2026 competition schedule runs through round 30.
    ("103", "2026"): {
        "status": "VERIFIED", "total_games": 30,
        "reason": "NFF official Eliteserien 2026 schedule runs through round 30.",
        "source": "https://www.fotball.no/eliteserien/",
    },
    # Poland — Ekstraklasa official framework schedule lists rounds 1-34.
    ("106", "2026"): {
        "status": "VERIFIED", "total_games": 34,
        "reason": "Official Ekstraklasa 2026/27 framework schedule has 34 rounds.",
        "source": "https://ekstraklasa.org/aktualnosci/ramowy-terminarz-pko-bank-polski-ekstraklasy-na-sezon-2026-27/",
    },
    # Portugal — Liga Portugal states the top division has 18 teams / 34 rounds.
    ("94", "2026"): {
        "status": "VERIFIED", "total_games": 34,
        "reason": "Liga Portugal official competition description: 18 teams, 34 rounds.",
        "source": "https://www.ligaportugal.pt/pages/sobre-a-liga",
    },
    # Lithuania — federation competition page exposes rounds through round 36.
    ("362", "2026"): {
        "status": "VERIFIED", "total_games": 36,
        "reason": "Lithuanian federation A Lyga 2026 schedule runs through round 36.",
        "source": "https://lietuvosfutbolas.lt/varzybos/vyru/a-lyga/",
    },
}


EXPLICIT_UNKNOWN = {
    ("218", "2026"): "Austria Bundesliga uses a split/phase format; phase-aware total is not yet verified in PBK.",
    ("144", "2026"): "Belgian Pro League uses post-regular-season phases; a single safe total is not configured.",
    ("119", "2026"): "Danish Superliga uses a split/phase format; phase-aware total is not yet verified in PBK.",
    ("365", "2026"): "Virsliga 2026 total-games fact is not yet verified in the PBK registry.",
    ("203", "2026"): "Süper Lig 2026/27 exact per-team total is not yet verified in the PBK registry.",
    ("179", "2026"): "Scottish Premiership uses a split format; phase-aware total is not yet verified in PBK.",
}


def get_format(provider_league_id, season):
    key = (str(provider_league_id or "").strip(), str(season or "").strip())
    verified = VERIFIED_FORMATS.get(key)
    if verified:
        return dict(verified)
    return {
        "status": "UNKNOWN",
        "total_games": None,
        "reason": EXPLICIT_UNKNOWN.get(key, "No season-scoped verified competition format in PBK registry."),
        "source": None,
    }
