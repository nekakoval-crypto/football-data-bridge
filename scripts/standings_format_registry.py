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


HISTORICAL_TOP5_SEASONS = (
    "2017/2018","2018/2019","2019/2020","2020/2021","2021/2022",
    "2022/2023","2023/2024","2024/2025","2025/2026",
)


def _historical_contract(
    league_code,
    season_label,
    *,
    team_count,
    total_games,
    direct_relegation_start_rank,
    relegation_playoff_rank=None,
    conditional_safety_playoff_if_tied=False,
    reason,
    source,
):
    safe_rank = (
        int(relegation_playoff_rank) - 1
        if relegation_playoff_rank is not None
        else int(direct_relegation_start_rank) - 1
    )
    return {
        "status": "VERIFIED_RULE_CONTRACT",
        "league_code": str(league_code),
        "season_label": str(season_label),
        "team_count": int(team_count),
        "total_games": int(total_games),
        "safe_rank": safe_rank,
        "direct_relegation_start_rank": int(direct_relegation_start_rank),
        "relegation_playoff_rank": (
            None if relegation_playoff_rank is None else int(relegation_playoff_rank)
        ),
        "conditional_safety_playoff_if_tied": bool(conditional_safety_playoff_if_tied),
        "europe_status": "UNKNOWN_BY_DESIGN",
        "reason": reason,
        "source": source,
    }


HISTORICAL_TOP5_FORMATS = {}

# England, Spain and Italy stayed at 20 clubs / 38 league matches in this PBK window.
# Europe slots are deliberately not encoded here because cup-winner and UEFA access
# interactions can change the effective boundary during a season.
for _season in HISTORICAL_TOP5_SEASONS:
    HISTORICAL_TOP5_FORMATS[("E0", _season)] = _historical_contract(
        "E0", _season,
        team_count=20, total_games=38, direct_relegation_start_rank=18,
        reason="Premier League historical format contract: 20 clubs, 38 matches, bottom three relegated.",
        source="https://www.premierleague.com/en/news/58905",
    )
    HISTORICAL_TOP5_FORMATS[("SP1", _season)] = _historical_contract(
        "SP1", _season,
        team_count=20, total_games=38, direct_relegation_start_rank=18,
        reason="LALIGA historical format contract used by PBK: 20 clubs, 38 league matches, bottom three relegation places.",
        source="https://www.laliga.com/en-GB/laliga-easports/standing",
    )
    HISTORICAL_TOP5_FORMATS[("I1", _season)] = _historical_contract(
        "I1", _season,
        team_count=20, total_games=38, direct_relegation_start_rank=18,
        conditional_safety_playoff_if_tied=(_season >= "2022/2023"),
        reason="Serie A historical format contract: 20 clubs, 38 matchdays, three relegation places; a safety tie playoff can apply in recent seasons.",
        source="https://en.legaseriea.it/serie-a/news/looking-forward-to-the-2026-27-serie-a-fixture-list",
    )

# Germany: 18 clubs / 34 matches; 16th enters the promotion/relegation playoff,
# 17th and 18th are direct-relegation positions.
for _season in HISTORICAL_TOP5_SEASONS:
    HISTORICAL_TOP5_FORMATS[("D1", _season)] = _historical_contract(
        "D1", _season,
        team_count=18, total_games=34,
        direct_relegation_start_rank=17, relegation_playoff_rank=16,
        reason="Bundesliga format contract: 18 clubs, 34 matchdays; rank 16 playoff, ranks 17-18 direct relegation.",
        source="https://www.bundesliga.com/de/bundesliga/news/relegation-alle-infos-termine-modus-abstieg-aufstieg-3008",
    )

# France requires explicit season-scoped handling.
# Through 2021/22: 20 clubs, rank 18 playoff, ranks 19-20 direct relegation.
for _season in ("2017/2018","2018/2019","2019/2020","2020/2021","2021/2022"):
    HISTORICAL_TOP5_FORMATS[("F1", _season)] = _historical_contract(
        "F1", _season,
        team_count=20, total_games=38,
        direct_relegation_start_rank=19, relegation_playoff_rank=18,
        reason=(
            "Ligue 1 pre-transition format contract. 2019/20 was later curtailed, "
            "but PBK keeps the 38-match pre-season contract because all historical "
            "features must reflect information known before each played fixture."
        ),
        source="https://www.lfp.fr/article/l-assemblee-generale-adopte-a-97-28-le-passage-a-18-clubs",
    )

# 2022/23 was the transition year to 18 clubs: four direct relegations.
HISTORICAL_TOP5_FORMATS[("F1", "2022/2023")] = _historical_contract(
    "F1", "2022/2023",
    team_count=20, total_games=38,
    direct_relegation_start_rank=17, relegation_playoff_rank=None,
    reason="Ligue 1 2022/23 transition: four relegations before reduction to 18 clubs.",
    source="https://www.lfp.fr/article/l-assemblee-generale-adopte-a-97-28-le-passage-a-18-clubs",
)

# From 2023/24: 18 clubs / 34 matches; 16th playoff, 17th-18th direct relegation.
for _season in ("2023/2024","2024/2025","2025/2026"):
    HISTORICAL_TOP5_FORMATS[("F1", _season)] = _historical_contract(
        "F1", _season,
        team_count=18, total_games=34,
        direct_relegation_start_rank=17, relegation_playoff_rank=16,
        reason="Ligue 1 post-transition format: 18 clubs, 34 matchdays; rank 16 playoff, ranks 17-18 direct relegation.",
        source="https://ligue1.com/en/articles/l1_article_2059-",
    )


def get_historical_top5_format(league_code, season_label):
    key = (str(league_code or "").strip(), str(season_label or "").strip())
    item = HISTORICAL_TOP5_FORMATS.get(key)
    if item:
        return dict(item)
    return {
        "status": "UNKNOWN",
        "league_code": key[0],
        "season_label": key[1],
        "team_count": None,
        "total_games": None,
        "safe_rank": None,
        "direct_relegation_start_rank": None,
        "relegation_playoff_rank": None,
        "conditional_safety_playoff_if_tied": False,
        "europe_status": "UNKNOWN_BY_DESIGN",
        "reason": "No season-scoped Top-5 historical motivation format in PBK registry.",
        "source": None,
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
