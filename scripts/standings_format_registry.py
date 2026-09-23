#!/usr/bin/env python3
"""Season-scoped verified competition-format facts for standings motivation.

This registry is deliberately conservative. Only formats verified from official
competition/federation sources are marked VERIFIED. Split/phase competitions
must carry an explicit phase-aware contract; PBK never invents point transforms
or assumes that a historical split format is identical to the current season.
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
    # Austria — 12 clubs, 22-round base phase, then two six-team groups.
    # From 2026/27 the point-halving transform is explicitly suspended.
    ("218", "2026"): {
        "status": "VERIFIED", "total_games": 32,
        "format_type": "SPLIT_TOP6_BOTTOM6",
        "regular_phase_games": 22,
        "post_split_games": 10,
        "points_transform": "NONE",
        "phase_aware": True,
        "reason": (
            "Official Austria Bundesliga 2026/27 format: 22-round base phase, "
            "then championship/qualification groups; point halving is suspended."
        ),
        "source": "https://www.bundesliga.at/de/news/artikel/alles-wissenswerte-zur-saison-2026-27",
    },
    # Belgium — format changed materially in 2026/27: 18 clubs, 34 rounds,
    # no championship/relegation play-offs in the top division.
    ("144", "2026"): {
        "status": "VERIFIED", "total_games": 34,
        "format_type": "CLASSIC_SINGLE_TABLE",
        "regular_phase_games": 34,
        "post_split_games": 0,
        "points_transform": "NONE",
        "phase_aware": True,
        "reason": (
            "Official Pro League 2026/27 reform: 18 clubs, 34 matchdays, "
            "no play-offs; bottom two are directly relegated."
        ),
        "source": "https://www.proleague.be/nieuws/vanaf-seizoen-26-27-met-18-clubs-in-de-jupiler-pro-league",
    },
    # Denmark — 22-round base phase followed by ten rounds in the top-six or
    # bottom-six phase, for 32 league matches per club.
    ("119", "2026"): {
        "status": "VERIFIED", "total_games": 32,
        "format_type": "SPLIT_TOP6_BOTTOM6",
        "regular_phase_games": 22,
        "post_split_games": 10,
        "points_transform": "NONE",
        "phase_aware": True,
        "reason": (
            "Official 3F Superliga 2026/27 schedule covers a 22-round base phase; "
            "the final phase is played over ten rounds."
        ),
        "source": "https://superliga.dk/nyheder/kamptidspunkter/2026-2027/kampprogrammet-for-grundspillet-2026-27-er-fastlagt",
    },
    # Latvia — LFF official 2026 competition calendar runs through round 36.
    ("365", "2026"): {
        "status": "VERIFIED", "total_games": 36,
        "format_type": "CLASSIC_MULTI_ROUND_ROBIN",
        "regular_phase_games": 36,
        "post_split_games": 0,
        "points_transform": "NONE",
        "phase_aware": True,
        "reason": "LFF official Virsliga 2026 calendar runs through round 36.",
        "source": "https://lff.lv/sacensibas/viriesi/virsliga/?p=2026",
    },
    # Turkey — TFF official 2026/27 fixture list has 18 clubs and 34 rounds.
    ("203", "2026"): {
        "status": "VERIFIED", "total_games": 34,
        "format_type": "CLASSIC_SINGLE_TABLE",
        "regular_phase_games": 34,
        "post_split_games": 0,
        "points_transform": "NONE",
        "phase_aware": True,
        "reason": "TFF official 2026/27 Super Lig fixture list runs through week 34.",
        "source": "https://www.tff.org/?pageID=198",
    },
    # Scotland — 12 clubs, split after round 33, final round 38.
    ("179", "2026"): {
        "status": "VERIFIED", "total_games": 38,
        "format_type": "SPLIT_TOP6_BOTTOM6",
        "regular_phase_games": 33,
        "post_split_games": 5,
        "points_transform": "NONE",
        "phase_aware": True,
        "reason": (
            "SPFL 2026/27 key dates explicitly identify fixture rounds 33 and 38; "
            "the Premiership split therefore contributes five post-split matches."
        ),
        "source": "https://spfl.co.uk/news/key-dates-for-202627",
    },
}


EXPLICIT_UNKNOWN = {}


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



# Historical PBK16 exact objective contracts beyond the Top-5.
#
# These entries are deliberately sparse and season-scoped. A contract is added
# only when the title/relegation structure is verified from an official
# competition or federation source. Missing seasons remain UNKNOWN.
HISTORICAL_PBK16_FORMATS = {}


def _pbk16_historical_contract(
    provider_league_id,
    season,
    *,
    team_count,
    total_games,
    direct_relegation_start_rank=None,
    relegation_playoff_rank=None,
    relegation_playoff_start_rank=None,
    relegation_playoff_end_rank=None,
    format_type="CLASSIC_SINGLE_TABLE",
    regular_phase_games=None,
    post_split_games=0,
    points_transform="NONE",
    title_total_games=None,
    relegation_total_games=None,
    season_completion_status="COMPLETED",
    title_status="AWARDED",
    relegation_status="APPLIES",
    phase_aware=False,
    reason,
    source,
):
    if relegation_playoff_start_rank is not None:
        safe_rank = int(relegation_playoff_start_rank) - 1
    elif relegation_playoff_rank is not None:
        safe_rank = int(relegation_playoff_rank) - 1
    elif direct_relegation_start_rank is not None:
        safe_rank = int(direct_relegation_start_rank) - 1
    else:
        # Verified no-relegation season: every table position is safe.
        safe_rank = int(team_count)

    if regular_phase_games is None:
        regular_phase_games = int(total_games)

    if title_total_games is None:
        title_total_games = int(total_games)

    if relegation_total_games is None:
        relegation_total_games = int(total_games)

    return {
        "status": "VERIFIED_RULE_CONTRACT",
        "provider_league_id": str(provider_league_id),
        "season": str(season),
        "team_count": int(team_count),
        "total_games": int(total_games),
        "format_type": str(format_type),
        "regular_phase_games": int(regular_phase_games),
        "post_split_games": int(post_split_games),
        "points_transform": str(points_transform),
        "phase_aware": bool(phase_aware),
        "title_total_games": int(title_total_games),
        "relegation_total_games": int(relegation_total_games),
        "season_completion_status": str(season_completion_status),
        "title_status": str(title_status),
        "relegation_status": str(relegation_status),
        "safe_rank": safe_rank,
        "direct_relegation_start_rank": (
            None
            if direct_relegation_start_rank is None
            else int(direct_relegation_start_rank)
        ),
        "relegation_playoff_rank": (
            None
            if relegation_playoff_rank is None
            else int(relegation_playoff_rank)
        ),
        "relegation_playoff_start_rank": (
            None
            if relegation_playoff_start_rank is None
            else int(relegation_playoff_start_rank)
        ),
        "relegation_playoff_end_rank": (
            None
            if relegation_playoff_end_rank is None
            else int(relegation_playoff_end_rank)
        ),
        "europe_status": "UNKNOWN_BY_DESIGN",
        "reason": reason,
        "source": source,
    }


# Norway - Eliteserien 2019.
# 16 clubs, 30 matches per club. Places 15-16 were directly relegated;
# place 14 entered the relegation qualification.
HISTORICAL_PBK16_FORMATS[("103", "2019")] = _pbk16_historical_contract(
    "103",
    "2019",
    team_count=16,
    total_games=30,
    direct_relegation_start_rank=15,
    relegation_playoff_rank=14,
    reason=(
        "NFF Eliteserien 2019: 16 clubs; positions 15-16 directly "
        "relegated and position 14 entered relegation qualification."
    ),
    source=(
        "https://www.fotball.no/globalassets/krets/hordaland/"
        "sesongen-2019/opp-og-nedrykk-senior-2019.pdf"
    ),
)


# Poland - Ekstraklasa 2020/21.
# 16 clubs, 30 rounds. The 16th-placed club alone was relegated as the
# league transitioned to 18 clubs for 2021/22.
HISTORICAL_PBK16_FORMATS[("106", "2020")] = _pbk16_historical_contract(
    "106",
    "2020",
    team_count=16,
    total_games=30,
    direct_relegation_start_rank=16,
    relegation_playoff_rank=None,
    reason=(
        "PZPN Ekstraklasa 2020/21 transition contract: 16 clubs, "
        "30 rounds, only position 16 relegated before expansion "
        "to 18 clubs."
    ),
    source=(
        "https://www.pzpn.pl/public/system/files/site_content/635/"
        "3514-44.KOMUNIKAT%20ZARZ%C4%84DU%2024.07.2020.pdf"
    ),
)


# Turkey - Super Lig 2020/21.
# 21 clubs. Double round-robin means 40 matches per club; positions
# 18-21 were relegated.
HISTORICAL_PBK16_FORMATS[("203", "2020")] = _pbk16_historical_contract(
    "203",
    "2020",
    team_count=21,
    total_games=40,
    direct_relegation_start_rank=18,
    relegation_playoff_rank=None,
    reason=(
        "TFF Super Lig 2020/21: 21 clubs in a double round-robin; "
        "positions 18-21 relegated."
    ),
    source=(
        "https://www.tff.org/Resources/TFF/Documents/STATULER/"
        "2020-2021/2020-2021-SL-STATU.pdf"
    ),
)



# Poland - Ekstraklasa 2022/23.
# 18 clubs, 34 matches per club; ranks 16-18 directly relegated.
HISTORICAL_PBK16_FORMATS[("106", "2022")] = _pbk16_historical_contract(
    "106",
    "2022",
    team_count=18,
    total_games=34,
    direct_relegation_start_rank=16,
    relegation_playoff_rank=None,
    reason=(
        "PZPN Ekstraklasa 2022/23: ranks 16, 17 and 18 were "
        "direct relegation positions."
    ),
    source=(
        "https://www.pzpn.pl/public/system/files/site_content/635/"
        "4682-11.KOMUNIKAT%20ZARZ%C4%84DU%2023%2005%202022.pdf"
    ),
)


# Turkey - Super Lig 2021/22.
# 20 clubs, 38 matches per club; ranks 17-20 directly relegated.
HISTORICAL_PBK16_FORMATS[("203", "2021")] = _pbk16_historical_contract(
    "203",
    "2021",
    team_count=20,
    total_games=38,
    direct_relegation_start_rank=17,
    relegation_playoff_rank=None,
    reason=(
        "TFF Super Lig 2021/22: 20 clubs; four clubs were designated "
        "for relegation to TFF 1. Lig."
    ),
    source=(
        "https://www.tff.org/default.aspx?"
        "ftxtID=35367&pageID=687"
    ),
)


# Turkey - Super Lig 2023/24.
# Official preseason statute: 20 clubs, double round-robin,
# ranks 17-20 directly relegated.
HISTORICAL_PBK16_FORMATS[("203", "2023")] = _pbk16_historical_contract(
    "203",
    "2023",
    team_count=20,
    total_games=38,
    direct_relegation_start_rank=17,
    relegation_playoff_rank=None,
    reason=(
        "TFF Super Lig 2023/24 preseason statute: 20 clubs in a "
        "double round-robin; ranks 17-20 relegated."
    ),
    source=(
        "https://www.tff.org/Resources/TFF/Documents/STATULER/"
        "2023-2024/Trendyol-Super-Lig-Musabakalari-Statusu.pdf"
    ),
)


# Turkey - Super Lig 2024/25.
# Official preseason statute: 19 clubs, each club plays 36 matches,
# ranks 16-19 directly relegated.
HISTORICAL_PBK16_FORMATS[("203", "2024")] = _pbk16_historical_contract(
    "203",
    "2024",
    team_count=19,
    total_games=36,
    direct_relegation_start_rank=16,
    relegation_playoff_rank=None,
    reason=(
        "TFF Super Lig 2024/25 preseason statute: 19 clubs in a "
        "double round-robin; ranks 16-19 relegated."
    ),
    source=(
        "https://www.tff.org/Resources/TFF/Documents/STATULER/"
        "2024-2025/2024-2025-Sezonu-Trendyol-Super-Lig-"
        "Musabakalari-Statusu.pdf"
    ),
)


# Turkey - Super Lig 2025/26.
# Official preseason statute: 18 clubs, 34 matches per club,
# ranks 16-18 directly relegated.
HISTORICAL_PBK16_FORMATS[("203", "2025")] = _pbk16_historical_contract(
    "203",
    "2025",
    team_count=18,
    total_games=34,
    direct_relegation_start_rank=16,
    relegation_playoff_rank=None,
    reason=(
        "TFF Super Lig 2025/26 preseason statute: 18 clubs in a "
        "double round-robin; ranks 16-18 relegated."
    ),
    source=(
        "https://www.tff.org/Resources/TFF/Auto/"
        "0817868058e745499efca46044b32e57.pdf"
    ),
)



# Norway - Eliteserien 2017.
# Official NFF historical table: 16 clubs, 30 matches.
# Rank 14 entered relegation qualification; ranks 15-16 were direct relegation.
HISTORICAL_PBK16_FORMATS[("103", "2017")] = _pbk16_historical_contract(
    "103",
    "2017",
    team_count=16,
    total_games=30,
    direct_relegation_start_rank=15,
    relegation_playoff_rank=14,
    reason=(
        "NFF Eliteserien 2017 historical competition contract: "
        "16 clubs and 30 league matches; rank 14 relegation "
        "qualification, ranks 15-16 direct relegation."
    ),
    source=(
        "https://www.fotball.no/fotballdata/turnering/hjem/"
        "?fiksId=153173&underside=tabellen"
    ),
)


# Norway - Eliteserien 2018.
# Official NFF historical table: 16 clubs, 30 matches.
# Rank 14 entered relegation qualification; ranks 15-16 were direct relegation.
HISTORICAL_PBK16_FORMATS[("103", "2018")] = _pbk16_historical_contract(
    "103",
    "2018",
    team_count=16,
    total_games=30,
    direct_relegation_start_rank=15,
    relegation_playoff_rank=14,
    reason=(
        "NFF Eliteserien 2018 historical competition contract: "
        "16 clubs and 30 league matches; rank 14 relegation "
        "qualification, ranks 15-16 direct relegation."
    ),
    source=(
        "https://www.fotball.no/fotballdata/turnering/hjem/"
        "?fiksId=158475&underside=tabellen"
    ),
)


# Norway - Eliteserien 2021.
# NFF explicitly states that 14th place gave qualification.
# The official table has 16 clubs and 30 matches; ranks 15-16 were relegated.
HISTORICAL_PBK16_FORMATS[("103", "2021")] = _pbk16_historical_contract(
    "103",
    "2021",
    team_count=16,
    total_games=30,
    direct_relegation_start_rank=15,
    relegation_playoff_rank=14,
    reason=(
        "NFF Eliteserien 2021: 16 clubs, 30 matches; NFF explicitly "
        "states that rank 14 entered qualification, with ranks 15-16 "
        "as direct relegation positions."
    ),
    source=(
        "https://www.fotball.no/turneringer/eliteserien/2021/"
        "slik-endte-eliteserien-2021/"
    ),
)


# Norway - Eliteserien 2023.
# Official NFF historical table: 16 clubs, 30 matches.
# Rank 14 relegation qualification; ranks 15-16 direct relegation.
HISTORICAL_PBK16_FORMATS[("103", "2023")] = _pbk16_historical_contract(
    "103",
    "2023",
    team_count=16,
    total_games=30,
    direct_relegation_start_rank=15,
    relegation_playoff_rank=14,
    reason=(
        "NFF Eliteserien 2023 historical competition contract: "
        "16 clubs and 30 league matches; rank 14 relegation "
        "qualification, ranks 15-16 direct relegation."
    ),
    source=(
        "https://www.fotball.no/fotballdata/turnering/hjem/"
        "?fiksId=186850"
    ),
)


# Portugal - Primeira Liga 2021/22.
# Official Liga Portugal regulation: 18 clubs.
# Bottom two directly relegated; the club immediately above them
# enters the maintenance/promotion playoff.
HISTORICAL_PBK16_FORMATS[("94", "2021")] = _pbk16_historical_contract(
    "94",
    "2021",
    team_count=18,
    total_games=34,
    direct_relegation_start_rank=17,
    relegation_playoff_rank=16,
    reason=(
        "Liga Portugal 2021/22 regulation: 18 clubs; the bottom two "
        "are directly relegated and rank 16 enters the maintenance "
        "playoff."
    ),
    source=(
        "https://www.ligaportugal.pt/media/36226/"
        "regulamento-das-competicoes-21-22.pdf"
    ),
)



# Norway - Eliteserien 2020.
# 16 clubs, 30 matches. NFF explicitly states that rank 14 entered
# the promotion/relegation qualification; ranks 15-16 were direct relegation.
HISTORICAL_PBK16_FORMATS[("103", "2020")] = _pbk16_historical_contract(
    "103",
    "2020",
    team_count=16,
    total_games=30,
    direct_relegation_start_rank=15,
    relegation_playoff_rank=14,
    reason=(
        "NFF Eliteserien 2020: 16 clubs and 30 matches; rank 14 "
        "entered relegation qualification, ranks 15-16 were direct "
        "relegation positions."
    ),
    source=(
        "https://www.fotball.no/turneringer/obosligaen/2020/"
        "slik-spilles-kvalifiseringen-i-obos-ligaen/"
    ),
)


# Norway - Eliteserien 2022.
# The official NFF table has 16 clubs and 30 matches.
# Sandefjord finished 14th and entered the relegation qualification;
# Kristiansund and Jerv were directly relegated.
HISTORICAL_PBK16_FORMATS[("103", "2022")] = _pbk16_historical_contract(
    "103",
    "2022",
    team_count=16,
    total_games=30,
    direct_relegation_start_rank=15,
    relegation_playoff_rank=14,
    reason=(
        "NFF Eliteserien 2022: 16 clubs and 30 matches; Sandefjord "
        "finished rank 14 and entered relegation qualification, while "
        "ranks 15-16 were directly relegated."
    ),
    source=(
        "https://www.fotball.no/turneringer/eliteserien/2022/"
        "dramatisk-avslutningsrunde-i-eliteserien/"
    ),
)


# Norway - Eliteserien 2024.
# Official NFF table: 16 clubs and 30 matches.
# NFF explicitly scheduled rank 14 in the Eliteserien qualification.
HISTORICAL_PBK16_FORMATS[("103", "2024")] = _pbk16_historical_contract(
    "103",
    "2024",
    team_count=16,
    total_games=30,
    direct_relegation_start_rank=15,
    relegation_playoff_rank=14,
    reason=(
        "NFF Eliteserien 2024: 16 clubs and 30 matches; rank 14 "
        "entered the Eliteserien qualification and ranks 15-16 were "
        "direct relegation positions."
    ),
    source=(
        "https://www.fotball.no/turneringer/eliteserien/2024/"
        "tidspunkt-for-kvalifseringskamper/"
    ),
)


# Norway - Eliteserien 2025.
# Official NFF table: 16 clubs and 30 matches.
# NFF qualification rules explicitly match rank 14 in Eliteserien
# against the OBOS qualification winner.
HISTORICAL_PBK16_FORMATS[("103", "2025")] = _pbk16_historical_contract(
    "103",
    "2025",
    team_count=16,
    total_games=30,
    direct_relegation_start_rank=15,
    relegation_playoff_rank=14,
    reason=(
        "NFF Eliteserien 2025: 16 clubs and 30 matches; rank 14 "
        "entered relegation qualification, ranks 15-16 were direct "
        "relegation positions."
    ),
    source=(
        "https://www.fotball.no/turneringer/obosligaen/2025/"
        "slik-spilles-kvalifiseringskampene-til-eliteserien-"
        "obos-ligaen-toppserien-og-1.-divisjon-2026"
    ),
)




# ============================================================
# SUPER MEGA MAXI BATCH E
# ============================================================


# Poland - Ekstraklasa.
# From 2021/22 onward: 18 clubs, 34 matches; ranks 16-18 relegated.
for _season in ("2021", "2023", "2024", "2025"):
    HISTORICAL_PBK16_FORMATS[("106", _season)] = _pbk16_historical_contract(
        "106",
        _season,
        team_count=18,
        total_games=34,
        direct_relegation_start_rank=16,
        relegation_playoff_rank=None,
        reason=(
            "PZPN Ekstraklasa post-expansion contract: 18 clubs, "
            "34 rounds; ranks 16-18 directly relegated."
        ),
        source=(
            "https://pzpn.pl/public/system/files/site_content/635/"
            "3379-40.KOMUNIKAT%20ZARZ%C4%84DU%2021.02.2020.pdf"
        ),
    )


# Portugal - Primeira Liga.
# 18 clubs, 34 matches; bottom two direct, rank 16 playoff.
for _season in ("2020", "2022", "2023", "2024", "2025"):
    HISTORICAL_PBK16_FORMATS[("94", _season)] = _pbk16_historical_contract(
        "94",
        _season,
        team_count=18,
        total_games=34,
        direct_relegation_start_rank=17,
        relegation_playoff_rank=16,
        reason=(
            "Liga Portugal contract: 18 clubs; ranks 17-18 direct "
            "relegation and rank 16 enters maintenance playoff."
        ),
        source=(
            "https://www.ligaportugal.pt/media/26797/"
            "regulamento-das-competicoes-2020-21.pdf"
        ),
    )


# Turkey - Super Lig 2017/18 and 2018/19.
# 18 clubs, 34 matches; ranks 16-18 directly relegated.
for _season in ("2017", "2018"):
    HISTORICAL_PBK16_FORMATS[("203", _season)] = _pbk16_historical_contract(
        "203",
        _season,
        team_count=18,
        total_games=34,
        direct_relegation_start_rank=16,
        relegation_playoff_rank=None,
        reason=(
            "TFF Super Lig historical contract: 18 clubs and "
            "34 matches; ranks 16-18 directly relegated."
        ),
        source=(
            "https://www.tff.org/default.aspx?pageID=1440"
            if _season == "2017"
            else
            "https://www.tff.org/default.aspx?"
            "2707pg=4&ftxtID=31439&pageID=204"
        ),
    )


# Netherlands - Eredivisie modern relegation structure.
# 18 clubs, 34 matches; ranks 17-18 direct, rank 16 playoff.
for _season in ("2020", "2021", "2022", "2023", "2024", "2025"):
    HISTORICAL_PBK16_FORMATS[("88", _season)] = _pbk16_historical_contract(
        "88",
        _season,
        team_count=18,
        total_games=34,
        direct_relegation_start_rank=17,
        relegation_playoff_rank=16,
        reason=(
            "KNVB Eredivisie modern contract: 18 clubs; ranks 17-18 "
            "directly relegated and rank 16 enters promotion/"
            "relegation playoff."
        ),
        source=(
            "https://www.knvb.nl/nieuws/betaald-voetbal/"
            "eredivisie/66189/virtuele-schemas-europees-ticket-"
            "en-play-offs"
        ),
    )



# ============================================================
# SUPER MEGA MAXI BATCH F
# Optional direct relegation semantics + 14 verified cells.
# ============================================================


# Austria - Bundesliga 2017/18.
# 10 clubs, 36 matches.
# Last place entered the relegation playoff; there was no direct
# table-position relegation.
HISTORICAL_PBK16_FORMATS[("218", "2017")] = _pbk16_historical_contract(
    "218",
    "2017",
    team_count=10,
    total_games=36,
    direct_relegation_start_rank=None,
    relegation_playoff_rank=10,
    reason=(
        "Austrian Bundesliga 2017/18: 10 clubs and 36 rounds; "
        "rank 10 entered the relegation playoff rather than being "
        "directly relegated."
    ),
    source=(
        "https://www.bundesliga.at/de/news/artikel/"
        "die-details-der-ligareform-so-wird-ab-2018-19-gespielt"
    ),
)


# Latvia - Virsliga 2018.
# Rank 8 direct relegation; rank 7 playoff.
HISTORICAL_PBK16_FORMATS[("365", "2018")] = _pbk16_historical_contract(
    "365",
    "2018",
    team_count=8,
    total_games=28,
    direct_relegation_start_rank=8,
    relegation_playoff_rank=7,
    reason=(
        "LFF Virsliga 2018 regulation: last place directly loses "
        "top-flight status and the penultimate club enters the playoff."
    ),
    source=(
        "https://lff.lv/files/documents/105/"
        "2018_Virsligas_reglaments__.pdf"
    ),
)


# Latvia - Virsliga 2019.
# 9 clubs, 32 matches.
# Last place entered a playoff; no direct table-position relegation.
HISTORICAL_PBK16_FORMATS[("365", "2019")] = _pbk16_historical_contract(
    "365",
    "2019",
    team_count=9,
    total_games=32,
    direct_relegation_start_rank=None,
    relegation_playoff_rank=9,
    reason=(
        "LFF Virsliga 2019 regulation: rank 9 entered a two-leg "
        "promotion/relegation playoff; no direct table-position "
        "relegation was specified."
    ),
    source=(
        "https://lff.lv/files/documents/339/"
        "2019_Virsligas_reglaments_lff.pdf"
    ),
)


# Latvia - Virsliga 2020.
# 10 clubs, three rounds = 27 matches.
# Rank 10 direct; rank 9 playoff.
HISTORICAL_PBK16_FORMATS[("365", "2020")] = _pbk16_historical_contract(
    "365",
    "2020",
    team_count=10,
    total_games=27,
    direct_relegation_start_rank=10,
    relegation_playoff_rank=9,
    reason=(
        "LFF Virsliga 2020 regulation: three-round competition; "
        "rank 10 directly relegated and rank 9 entered the playoff."
    ),
    source=(
        "https://lff.lv/files/documents/556/"
        "_2020_gada_Virsligas_reglaments_apstiprinats_ar_labojumiem_.pdf"
    ),
)


# Latvia - Virsliga 2022.
HISTORICAL_PBK16_FORMATS[("365", "2022")] = _pbk16_historical_contract(
    "365",
    "2022",
    team_count=10,
    total_games=36,
    direct_relegation_start_rank=10,
    relegation_playoff_rank=9,
    reason=(
        "LFF Virsliga 2022 regulation: rank 10 directly relegated "
        "and rank 9 entered the promotion/relegation playoff."
    ),
    source=(
        "https://lff.lv/files/documents/855/"
        "2022_gada_Virsligas_reglaments.pdf"
    ),
)


# Latvia - Virsliga 2023.
HISTORICAL_PBK16_FORMATS[("365", "2023")] = _pbk16_historical_contract(
    "365",
    "2023",
    team_count=10,
    total_games=36,
    direct_relegation_start_rank=10,
    relegation_playoff_rank=9,
    reason=(
        "LFF Virsliga 2023 regulation: four-round competition; "
        "rank 10 directly relegated and rank 9 entered the playoff."
    ),
    source=(
        "https://lff.lv/files/documents/1966/"
        "2023_gada_Virsligas_reglaments.pdf"
    ),
)


# Latvia - Virsliga 2024.
HISTORICAL_PBK16_FORMATS[("365", "2024")] = _pbk16_historical_contract(
    "365",
    "2024",
    team_count=10,
    total_games=36,
    direct_relegation_start_rank=10,
    relegation_playoff_rank=9,
    reason=(
        "LFF Virsliga 2024 regulation: rank 10 directly relegated "
        "and rank 9 entered the promotion/relegation playoff."
    ),
    source=(
        "https://lff.lv/files/documents/2076/"
        "2024_gada_Virsligas_cempionata_reglaments.pdf"
    ),
)


# Latvia - Virsliga 2025.
HISTORICAL_PBK16_FORMATS[("365", "2025")] = _pbk16_historical_contract(
    "365",
    "2025",
    team_count=10,
    total_games=36,
    direct_relegation_start_rank=10,
    relegation_playoff_rank=9,
    reason=(
        "LFF Virsliga 2025 regulation: rank 10 directly relegated "
        "and rank 9 entered the promotion/relegation playoff."
    ),
    source=(
        "https://lff.lv/files/documents/2202/"
        "Latvijas_virsligas_cempionata_reglaments_2025.pdf"
    ),
)


# Lithuania - A Lyga 2020.
# Special six-team format: 20 matches and no relegation.
HISTORICAL_PBK16_FORMATS[("362", "2020")] = _pbk16_historical_contract(
    "362",
    "2020",
    team_count=6,
    total_games=20,
    direct_relegation_start_rank=None,
    relegation_playoff_rank=None,
    reason=(
        "LFF 2020 competition regulation: with six A Lyga clubs, "
        "the league was played over six rounds and no club was relegated."
    ),
    source=(
        "https://lff.lt/files/documents/661/"
        "2020%20m.%20LFF%20Nuostatai%20VK.pdf"
    ),
)


# Lithuania - A Lyga 2021.
# 10 clubs / 36 matches; ranks 9-10 direct relegation.
HISTORICAL_PBK16_FORMATS[("362", "2021")] = _pbk16_historical_contract(
    "362",
    "2021",
    team_count=10,
    total_games=36,
    direct_relegation_start_rank=9,
    relegation_playoff_rank=None,
    reason=(
        "LFF 2021 regulation: 10 clubs and 36 matches; ranks 9-10 "
        "were direct relegation positions."
    ),
    source=(
        "https://www.lff.lt/files/documents/824/"
        "2021%20M.%20LFF%20NUOSTATAI.pdf"
    ),
)


# Lithuania - A Lyga 2022.
# Last direct; penultimate playoff.
HISTORICAL_PBK16_FORMATS[("362", "2022")] = _pbk16_historical_contract(
    "362",
    "2022",
    team_count=10,
    total_games=36,
    direct_relegation_start_rank=10,
    relegation_playoff_rank=9,
    reason=(
        "LFF A Lyga 2022 regulation: rank 10 directly relegated "
        "and rank 9 entered the promotion/relegation playoff."
    ),
    source=(
        "https://lff.lt/files/documents/946/"
        "2022%20m.%20Optibet%20A%20lygos%20var%C5%BEyb%C5%B3%"
        "20patvirtinti%20nuostatai.pdf"
    ),
)


# Lithuania - A Lyga 2024.
# Last direct; penultimate playoff.
HISTORICAL_PBK16_FORMATS[("362", "2024")] = _pbk16_historical_contract(
    "362",
    "2024",
    team_count=10,
    total_games=36,
    direct_relegation_start_rank=10,
    relegation_playoff_rank=9,
    reason=(
        "LFF A Lyga 2024 regulation: last place directly relegated "
        "and the penultimate team entered a two-leg playoff."
    ),
    source=(
        "https://www.lff.lt/wp-content/uploads/2023/12/"
        "2024-metu-A-lyga-varz%CC%8Cybu%CC%A8-nuostatai-.pdf"
    ),
)


# Portugal - Liga NOS 2017/18.
# 18 clubs; bottom two directly relegated.
HISTORICAL_PBK16_FORMATS[("94", "2017")] = _pbk16_historical_contract(
    "94",
    "2017",
    team_count=18,
    total_games=34,
    direct_relegation_start_rank=17,
    relegation_playoff_rank=None,
    reason=(
        "Liga Portugal 2017/18 regulation: 18 clubs; the bottom two "
        "places were direct relegation positions."
    ),
    source=(
        "https://www.ligaportugal.pt/media/12329/"
        "regulamento-das-competicoes-1718.pdf"
    ),
)


# Portugal - Liga NOS 2018/19.
# 18 clubs; bottom two directly relegated.
HISTORICAL_PBK16_FORMATS[("94", "2018")] = _pbk16_historical_contract(
    "94",
    "2018",
    team_count=18,
    total_games=34,
    direct_relegation_start_rank=17,
    relegation_playoff_rank=None,
    reason=(
        "Liga Portugal 2018/19 regulation: 18 clubs; the bottom two "
        "places were direct relegation positions."
    ),
    source=(
        "https://www.ligaportugal.pt/media/15102/"
        "regulamento-competicoes-2018-19.pdf"
    ),
)




# ============================================================
# SUPER MEGA MAXI BATCH G
# Phase-aware exact objective contracts.
# Austria 2018-2025, Denmark 2020-2025, Scotland 2020-2025.
# ============================================================


# Austria - Bundesliga.
#
# From 2018/19:
# - 12 clubs
# - 22-match regular phase
# - split into Championship and Qualification groups
# - 10 post-split matches
# - points from the regular phase are halved and rounded down
# - last club in Qualification Group is directly relegated
for _season in (
    "2018",
    "2019",
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
    "2025",
):
    HISTORICAL_PBK16_FORMATS[
        ("218", _season)
    ] = _pbk16_historical_contract(
        "218",
        _season,
        team_count=12,
        total_games=32,
        direct_relegation_start_rank=12,
        relegation_playoff_rank=None,
        format_type="SPLIT_TOP6_BOTTOM6",
        regular_phase_games=22,
        post_split_games=10,
        points_transform="HALVE_FLOOR",
        phase_aware=True,
        reason=(
            "Austrian Bundesliga post-2018 reform: 12 clubs; "
            "22-match regular phase followed by two six-team groups "
            "for another 10 matches. Regular-phase points are halved "
            "before the final phase; the last club in the "
            "Qualification Group is directly relegated."
        ),
        source=(
            "https://www.bundesliga.at/de/news/artikel/"
            "die-details-der-ligareform-so-wird-ab-2018-19-gespielt"
        ),
    )


# Denmark - Superliga.
#
# From 2020/21:
# - 12 clubs
# - 22-match regular phase
# - Championship / Qualification split
# - 10 post-split matches
# - points and goals carry forward unchanged
# - positions 11 and 12 are directly relegated
for _season in (
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
    "2025",
):
    HISTORICAL_PBK16_FORMATS[
        ("119", _season)
    ] = _pbk16_historical_contract(
        "119",
        _season,
        team_count=12,
        total_games=32,
        direct_relegation_start_rank=11,
        relegation_playoff_rank=None,
        format_type="SPLIT_TOP6_BOTTOM6",
        regular_phase_games=22,
        post_split_games=10,
        points_transform="NONE",
        phase_aware=True,
        reason=(
            "Danish Superliga 12-club structure: 22-match regular "
            "phase followed by 10 Championship/Qualification matches; "
            "points and goals carry forward and positions 11-12 are "
            "directly relegated."
        ),
        source=(
            "https://cms.superliga.dk/media/wyjngaie/"
            "struktur_superliga-pdf.pdf"
        ),
    )


# Scotland - Premiership.
#
# - 12 clubs
# - first 33 league matches
# - split into top six / bottom six
# - five additional matches
# - total 38
# - position 12 directly relegated
# - position 11 enters Premiership/Championship playoff
for _season in (
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
    "2025",
):
    HISTORICAL_PBK16_FORMATS[
        ("179", _season)
    ] = _pbk16_historical_contract(
        "179",
        _season,
        team_count=12,
        total_games=38,
        direct_relegation_start_rank=12,
        relegation_playoff_rank=11,
        format_type="SPLIT_TOP6_BOTTOM6",
        regular_phase_games=33,
        post_split_games=5,
        points_transform="NONE",
        phase_aware=True,
        reason=(
            "SPFL Premiership rules: 12 clubs, split after each "
            "club's 33rd match and five post-split matches; position "
            "12 is directly relegated and position 11 enters the "
            "Premiership/Championship playoff."
        ),
        source=(
            "https://spfl.co.uk/admin/filemanager/files/shares/"
            "SPFL%20Rules%20and%20Regulations%2024-Jun-20%20"
            "%28MASTER%20COPY%29%20CLEAN.pdf"
            if _season != "2025"
            else
            "https://spfl.co.uk/admin/filemanager/images/shares/"
            "August%202025/MASTER%20-%20Rules%20and%20Regulations%"
            "20%28CLEAN%20-%2025%20August%202025%29.pdf"
        ),
    )




# ============================================================
# BATCH H
# Relegation-playoff range semantics.
# ============================================================


# Netherlands - Eredivisie 2017/18 and 2018/19.
# 18 clubs / 34 matches.
# Rank 18 direct relegation; ranks 16-17 promotion/relegation playoffs.
for _season in ("2017", "2018"):
    HISTORICAL_PBK16_FORMATS[
        ("88", _season)
    ] = _pbk16_historical_contract(
        "88",
        _season,
        team_count=18,
        total_games=34,
        direct_relegation_start_rank=18,
        relegation_playoff_start_rank=16,
        relegation_playoff_end_rank=17,
        format_type="CLASSIC_SINGLE_TABLE",
        regular_phase_games=34,
        post_split_games=0,
        points_transform="NONE",
        phase_aware=False,
        reason=(
            "Historical Eredivisie relegation structure before "
            "the 2019/20 change: rank 18 directly relegated; "
            "ranks 16-17 entered promotion/relegation playoffs."
        ),
        source=(
            "https://www.knvb.nl/node/54909"
            if _season == "2018"
            else
            "https://www.knvb.nl/node/81"
        ),
    )


# Latvia - Virsliga 2021.
# Nine participating clubs, four rounds => 32 matches per club.
# Rank 9 entered the promotion/relegation playoff.
HISTORICAL_PBK16_FORMATS[
    ("365", "2021")
] = _pbk16_historical_contract(
    "365",
    "2021",
    team_count=9,
    total_games=32,
    direct_relegation_start_rank=None,
    relegation_playoff_rank=9,
    format_type="CLASSIC_MULTI_ROUND_ROBIN",
    regular_phase_games=32,
    post_split_games=0,
    points_transform="NONE",
    phase_aware=False,
    reason=(
        "LFF Virsliga 2021 regulation: four-round championship; "
        "with nine clubs remaining, rank 9 entered a two-leg "
        "promotion/relegation playoff."
    ),
    source=(
        "https://lff.lv/files/documents/690/"
        "2021_gada_Virsligas_reglaments_ar_labojumiem_15062021.pdf"
    ),
)


# Scotland - Premiership 2018/19.
# 12 clubs; split after 33 matches; total 38.
# Rank 12 direct relegation; rank 11 Premiership playoff.
HISTORICAL_PBK16_FORMATS[
    ("179", "2018")
] = _pbk16_historical_contract(
    "179",
    "2018",
    team_count=12,
    total_games=38,
    direct_relegation_start_rank=12,
    relegation_playoff_rank=11,
    format_type="SPLIT_TOP6_BOTTOM6",
    regular_phase_games=33,
    post_split_games=5,
    points_transform="NONE",
    phase_aware=True,
    reason=(
        "SPFL Premiership 2018/19: 12th place directly relegated; "
        "11th place entered the Premiership playoff."
    ),
    source=(
        "https://spfl.co.uk/news/play-offs-continue-this-weekend-45700"
    ),
)




# ============================================================
# BATCH I
# Objective-specific game horizons + six verified cells.
# ============================================================


# Lithuania 2017-2019:
# 8 clubs.
# Four-round base phase = 28 matches.
# Top six then play one additional round among themselves = 33 title matches.
# Rank 7 enters relegation playoff; rank 8 directly relegated.
#
# This is intentionally NOT flattened to one season length:
# title horizon = 33; relegation horizon = 28.
_lithuania_old_sources = {
    "2017": (
        "https://www.lff.lt/files/documents/163/"
        "2017.02.13-LFF%20var%C5%BEyb%C5%B3%20nuostatai.pdf"
    ),
    "2018": (
        "https://lff.lt/files/documents/345/"
        "2018%20LFF%20var%C5%BEyb%C5%B3%20nuostatai.pdf"
    ),
    "2019": (
        "https://www.lff.lt/"
        "pasirinkta-lietuvos-jaunimo-futbolo-ugdymo-kryptis/"
    ),
}

for _season in ("2017", "2018", "2019"):
    HISTORICAL_PBK16_FORMATS[
        ("362", _season)
    ] = _pbk16_historical_contract(
        "362",
        _season,
        team_count=8,
        total_games=33,
        direct_relegation_start_rank=8,
        relegation_playoff_rank=7,
        format_type="ASYMMETRIC_TOP6_FINAL_ROUND",
        regular_phase_games=28,
        post_split_games=5,
        points_transform="NONE",
        title_total_games=33,
        relegation_total_games=28,
        phase_aware=True,
        reason=(
            "LFF A Lyga historical format: eight clubs play four "
            "rounds (28 matches); the top six then play a fifth "
            "round among themselves. Rank 7 enters the relegation "
            "playoff and rank 8 is directly relegated. Therefore "
            "title and relegation objectives have different horizons."
        ),
        source=_lithuania_old_sources[_season],
    )


# Lithuania 2023.
# 10 clubs / 36 matches.
# Last place direct relegation; penultimate club enters playoff.
HISTORICAL_PBK16_FORMATS[
    ("362", "2023")
] = _pbk16_historical_contract(
    "362",
    "2023",
    team_count=10,
    total_games=36,
    direct_relegation_start_rank=10,
    relegation_playoff_rank=9,
    format_type="CLASSIC_MULTI_ROUND_ROBIN",
    regular_phase_games=36,
    post_split_games=0,
    points_transform="NONE",
    title_total_games=36,
    relegation_total_games=36,
    phase_aware=False,
    reason=(
        "LFF A Lyga 2023 regulations: 10 clubs play four rounds "
        "for 36 matches; last place is directly relegated and the "
        "penultimate club enters the promotion/relegation playoff."
    ),
    source=(
        "https://www.lff.lt/wp-content/uploads/2023/01/"
        "2023-Optibet-A-lyga-varz%CC%8Cybu%CC%A8-nuostatai-2023-01-09.pdf"
    ),
)


# Lithuania 2025.
# 10 clubs / 36 matches.
# Last place direct relegation; penultimate club enters playoff.
HISTORICAL_PBK16_FORMATS[
    ("362", "2025")
] = _pbk16_historical_contract(
    "362",
    "2025",
    team_count=10,
    total_games=36,
    direct_relegation_start_rank=10,
    relegation_playoff_rank=9,
    format_type="CLASSIC_MULTI_ROUND_ROBIN",
    regular_phase_games=36,
    post_split_games=0,
    points_transform="NONE",
    title_total_games=36,
    relegation_total_games=36,
    phase_aware=False,
    reason=(
        "LFF TOPsport A Lyga 2025 regulations: last place is "
        "directly relegated and the penultimate club enters the "
        "promotion/relegation playoff."
    ),
    source=(
        "https://www.lff.lt/wp-content/uploads/2025/01/"
        "2025-m.-TOPsport-A-lygos-c%CC%8Cempionato-nuostatai.pdf"
    ),
)


# Scotland 2017/18.
# 12 clubs; 33-match initial phase + five post-split matches.
# Rank 12 direct relegation; rank 11 Premiership playoff.
HISTORICAL_PBK16_FORMATS[
    ("179", "2017")
] = _pbk16_historical_contract(
    "179",
    "2017",
    team_count=12,
    total_games=38,
    direct_relegation_start_rank=12,
    relegation_playoff_rank=11,
    format_type="SPLIT_TOP6_BOTTOM6",
    regular_phase_games=33,
    post_split_games=5,
    points_transform="NONE",
    title_total_games=38,
    relegation_total_games=38,
    phase_aware=True,
    reason=(
        "SPFL Premiership 2017/18: 12-club split format; rank 12 "
        "was directly relegated and rank 11 entered the Premiership "
        "playoff."
    ),
    source=(
        "https://spfl.co.uk/news/previous-play-off-finals"
    ),
)




# ============================================================
# BATCH J
# Verified exceptional objective availability.
# ============================================================


# Netherlands - Eredivisie 2019/20.
#
# Competition was curtailed because of the COVID-19 pandemic.
# KNVB explicitly decided:
# - no champion;
# - no promotion;
# - no relegation.
#
# 34 is the scheduled league horizon, NOT a claim that the season
# was completed.
HISTORICAL_PBK16_FORMATS[
    ("88", "2019")
] = _pbk16_historical_contract(
    "88",
    "2019",
    team_count=18,
    total_games=34,
    direct_relegation_start_rank=None,
    relegation_playoff_rank=None,
    format_type="CURTAILED_NO_CHAMPION_NO_RELEGATION",
    regular_phase_games=34,
    post_split_games=0,
    points_transform="NONE",
    title_total_games=34,
    relegation_total_games=34,
    season_completion_status="CURTAILED",
    title_status="NO_CHAMPION",
    relegation_status="NO_RELEGATION",
    phase_aware=False,
    reason=(
        "KNVB terminated the 2019/20 professional season because "
        "of COVID-19 and explicitly awarded no champion and applied "
        "no promotion or relegation."
    ),
    source=(
        "https://www.knvb.nl/node/59905"
    ),
)


# Turkey - Super Lig 2019/20.
#
# The league itself was completed over 34 matches and Basaksehir
# was registered as champion. After the season, TFF Board decision
# no. 44 of 29 July 2020 removed relegation for 2019/20.
HISTORICAL_PBK16_FORMATS[
    ("203", "2019")
] = _pbk16_historical_contract(
    "203",
    "2019",
    team_count=18,
    total_games=34,
    direct_relegation_start_rank=None,
    relegation_playoff_rank=None,
    format_type="CLASSIC_SINGLE_TABLE_NO_RELEGATION",
    regular_phase_games=34,
    post_split_games=0,
    points_transform="NONE",
    title_total_games=34,
    relegation_total_games=34,
    season_completion_status="COMPLETED",
    title_status="AWARDED",
    relegation_status="NO_RELEGATION",
    phase_aware=False,
    reason=(
        "TFF registered Basaksehir as 2019/20 Super Lig champion "
        "and, under the Board decision of 29 July 2020, applied no "
        "relegation from the professional leagues for that season."
    ),
    source=(
        "https://www.tff.org/default.aspx?"
        "ftxtID=33593&pageID=204"
    ),
)




# ============================================================
# BATCH K
# Scotland 2019/20 curtailed-PpG + Poland 2019/20 split.
# ============================================================


# Scotland - Premiership 2019/20.
#
# SPFL concluded the season early.
# Final placings were determined by points per game.
# Celtic were crowned champions and Hearts were relegated.
#
# 38 is the scheduled full-season horizon. The season itself
# was curtailed before the normal post-split completion.
HISTORICAL_PBK16_FORMATS[
    ("179", "2019")
] = _pbk16_historical_contract(
    "179",
    "2019",
    team_count=12,
    total_games=38,
    direct_relegation_start_rank=12,
    relegation_playoff_rank=None,
    format_type="CURTAILED_PPG_FINAL_TABLE",
    regular_phase_games=33,
    post_split_games=5,
    points_transform="PPG_FINALIZATION",
    title_total_games=38,
    relegation_total_games=38,
    season_completion_status="CURTAILED",
    title_status="AWARDED",
    relegation_status="APPLIES",
    phase_aware=True,
    reason=(
        "SPFL concluded the 2019/20 Premiership early and "
        "determined final placings by points per game. Celtic "
        "were crowned champions and Hearts were relegated."
    ),
    source=(
        "https://spfl.co.uk/news/"
        "ladbrokes-premiership-and-spfl-season-201920-cur"
    ),
)


# Poland - Ekstraklasa 2019/20.
#
# 16 clubs.
# 30-match regular phase followed by championship/relegation
# groups of eight clubs.
# Each club plays seven further matches => 37 total.
# Regular-phase points carry into the final phase.
# Final ranks 14-16 are relegated.
HISTORICAL_PBK16_FORMATS[
    ("106", "2019")
] = _pbk16_historical_contract(
    "106",
    "2019",
    team_count=16,
    total_games=37,
    direct_relegation_start_rank=14,
    relegation_playoff_rank=None,
    format_type="SPLIT_TOP8_BOTTOM8",
    regular_phase_games=30,
    post_split_games=7,
    points_transform="NONE",
    title_total_games=37,
    relegation_total_games=37,
    season_completion_status="COMPLETED",
    title_status="AWARDED",
    relegation_status="APPLIES",
    phase_aware=True,
    reason=(
        "PZPN Ekstraklasa 2019/20 regulation: after the regular "
        "phase clubs split into places 1-8 and 9-16; each group "
        "plays seven additional rounds, with regular-phase points "
        "retained. Final positions 14-16 are relegated."
    ),
    source=(
        "https://www.pzpn.pl/public/system/files/site_content/635/"
        "2988-31.KOMUNIKAT%20ZARZ%C4%84DU%2023.05.2019.pdf"
    ),
)


def get_historical_pbk16_format(provider_league_id, season):
    key = (
        str(provider_league_id or "").strip(),
        str(season or "").strip(),
    )

    item = HISTORICAL_PBK16_FORMATS.get(key)

    if item:
        return dict(item)

    return {
        "status": "UNKNOWN",
        "provider_league_id": key[0],
        "season": key[1],
        "team_count": None,
        "total_games": None,
        "safe_rank": None,
        "direct_relegation_start_rank": None,
        "relegation_playoff_rank": None,
        "europe_status": "UNKNOWN_BY_DESIGN",
        "reason": (
            "No season-scoped verified historical PBK16 objective "
            "contract in registry."
        ),
        "source": None,
    }


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
