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
    direct_relegation_start_rank,
    relegation_playoff_rank=None,
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
        "provider_league_id": str(provider_league_id),
        "season": str(season),
        "team_count": int(team_count),
        "total_games": int(total_games),
        "safe_rank": safe_rank,
        "direct_relegation_start_rank": int(
            direct_relegation_start_rank
        ),
        "relegation_playoff_rank": (
            None
            if relegation_playoff_rank is None
            else int(relegation_playoff_rank)
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
