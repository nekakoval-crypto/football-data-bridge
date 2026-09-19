# PBK Stage80 Archive Readiness

Обновлено UTC: 2026-09-19T18:28:53Z
Статус: **COLLECTING**

## Покрытие
- Fixtures в текущем inventory: 129 (finished: 44).
- Fixture history: 178 unique fixtures / 4763 observations / 37 observation runs (finished observed: 87).
- Historical fixture catalog: 178 fixtures (terminal 87, rescheduled 1), history coverage 100.00%; missing 0, orphan 0.
- Finished fixtures с player stats: 36 / 44 (81.82%).
- Stage77 durable backlog: pending 17; captured 66; total 83.
- Normalized lineup archive: 6 rows / 2 fixtures; injury archive: 53 rows / 3 fixtures.
- Match event archive: 445 rows / 26 fixtures; backlog pending 14 / total 40.
- Stage81 durable backlog: pending 4; captured 47; total 51.
- Team match statistics: 47 complete fixtures / 94 team rows; current finished coverage 90.91%.
- Team xG: 10 complete fixtures / 20 team rows; captured-team-stat coverage 21.28%.
- Player xG/xA source: RESEARCH_SOURCE_EXTERNAL_LOCAL_ATTESTED_MAPPED_TO_PBK.
- Player stat rows: 2812; уникальных игроков: 2428.
- Player Grade rows: 2812; уникальных игроков: 2428.
- Current roster: 104 команд / 3214 игроковых строк.
- Player profile evidence: 2989 rows (2898 team-source + 91 residual-ID) / 2910 players / 104 teams; current-roster coverage 85.33%; identity-ready 2712 players (80.07%).
- Roster history: 104 команд / 104 team-snapshots / 3212 строк.
- Membership intervals: 3212 (open 3212, closed-by-observed-absence 0).
- Verified PBK↔Transfermarkt identities: 1148 rows / 1148 PBK players; invalid 452.
- Verified historical transfers: 8250 rows / 1051 PBK players; dates 1998-07-01 → 2027-06-30; invalid 3700.
- EPL referee research: 47 referees / 897 referee×team pairs / 3420 source matches; scope EPL_ONLY; penalties unavailable.
- Top-5 API-Football referee backfill: 45 / 45 league-seasons; 16239 fixture rows; referee coverage 99.44%; profiles 453; referee×team pairs 7689.
- Top-5 pre-match research context: 16111 valid rows / 16111 unique matches / 45 of 45 league-seasons; no-lookahead True.
- Top-5 historical motivation context: 16111 valid rows / 16111 unique matches / 45 of 45 league-seasons; full-table rows 15631; boundary-tie rows 4434; Europe UNKNOWN_BY_DESIGN; no-lookahead True.
- Top-5 motivation × market research: 2719 profiles / 288 stability rows; closing 1X2 12459; closing O/U2.5 12459; promotes factor False.
- Pre-match factor research: 2247 profile rows / 237 stability rows; closing 1X2 matches 12459; closing O/U2.5 matches 12459.
- Pre-match walk-forward research: 7685 folds / 1145 summaries; sample-qualified folds 4455; promotes factor False.
- Match context: 6 fixtures; official XI 1; injury evidence 3.
- PBK14 historical market bridge: 37327 AUTO/HIGH of 37674 valid source rows; AUTO 18940, HIGH 18387, REVIEW 32, UNMAPPED 315; fuzzy matching False; source coverage 14 / 16 locked leagues.
- PBK14 international-window × market join: 37327 valid rows; closing 1X2 30879; closing O/U2.5 22738; <=72h before 3595; <=72h after 424; player-level UNVERIFIED.
- PBK14 international-window market research: join 37327 rows; descriptive profiles 2686; stability rows 313; closing 1X2 30879; closing O/U2.5 22738; player-level UNVERIFIED.
- PBK14 congestion × market research: join 37327 rows; descriptive profiles 4698; stability rows 494; closing 1X2 30879; closing O/U2.5 22738; promotes factor False.
- PBK14 congestion walk-forward: 16095 valid folds / 2445 summaries; qualified folds 5470; temporal invalid 0; promotes factor False.
- PBK16 all-competition history: catalog 39 valid rows; required unresolved 0; fixture archive 70375 valid rows; domestic anchors 16 / 16 leagues; captured cells 322, provider-unavailable cells 19, pending 0, errors 0.
- PBK16 cup/UEFA congestion: 40989 valid rows / 40989 domestic fixtures; no-lookahead True; future schedule used False; prior UEFA <=72h 3210, prior cup <=72h 1436.
- PBK16 domestic phase audit: 40989 valid rows; table-phase 40731; post-table playoffs 258; split/table rows needing season contract 1747.
- PBK16 format inventory: 144 / 144 cells; captured 143; provider unavailable 1; exact motivation contracts verified 0.
- PBK16 historical table context V2: 40989 valid rows; safe regular prematch 38744; full-table 37400; blocked split/table 1747; post-table 258; awarded-taint 240.
- PBK16 international windows: 40989 valid rows / 40989 domestic fixtures; calendar windows 39; <=72h before 3956, <=72h after 518; player-level UNVERIFIED; no-lookahead True.

## Raw provider archive
- Storage configured: True.
- Backend: S3.
- Status: OK.
- Durable readback verified: True; verified at 2026-09-18T13:04:32Z.
- Observations: —; unique payloads: —.

## Незакрытые пробелы
- TEAM_STATS_BACKLOG_PENDING
- PLAYER_STATS_BACKLOG_PENDING
- PLAYER_STATS_PARTIAL_FINISHED_FIXTURE_COVERAGE
- TEAM_STATS_PARTIAL_FINISHED_FIXTURE_COVERAGE
- MATCH_EVENT_BACKLOG_PENDING
- REFEREE_HISTORY_TOP5_PROVIDER_REFEREE_FIELD_PARTIAL
- PBK16_COMPETITION_PROVIDER_SEASONS_PARTIAL
- PBK14_HISTORICAL_MARKET_BRIDGE_PARTIAL_MAPPING
- PBK16_HISTORICAL_MARKET_SOURCE_LIMITED_TO_14_LEAGUES
- MATCH_CONTEXT_COVERAGE_IS_CANONICAL_SCOPE_ONLY
- PLAYER_PROFILE_PARTIAL_CURRENT_ROSTER_COVERAGE
- TRANSFER_IDENTITY_INVALID_ROWS
- TRANSFER_HISTORY_INVALID_IDENTITY_ROWS
- TEAM_XG_PARTIAL_CAPTURED_FIXTURE_COVERAGE

Readiness — telemetry only. Этот отчёт не создаёт ставки, не меняет probability/EV, eligibility, stake или Forward journal.
