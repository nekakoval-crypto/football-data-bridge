# PBK Stage80 Archive Readiness

Обновлено UTC: 2026-09-20T16:29:47Z
Статус: **COLLECTING**

## Покрытие
- Fixtures в текущем inventory: 129 (finished: 100).
- Fixture history: 178 unique fixtures / 7601 observations / 59 observation runs (finished observed: 143).
- Historical fixture catalog: 178 fixtures (terminal 143, rescheduled 1), history coverage 100.00%; missing 0, orphan 0.
- Finished fixtures с player stats: 68 / 100 (68.00%).
- Stage77 durable backlog: pending 39; captured 98; total 137.
- Normalized lineup archive: 8 rows / 3 fixtures; injury archive: 54 rows / 3 fixtures.
- Match event archive: 1362 rows / 81 fixtures; backlog pending 4 / total 85.
- Stage81 durable backlog: pending 8; captured 99; total 107.
- Team match statistics: 99 complete fixtures / 198 team rows; current finished coverage 92.00%.
- Team xG: 19 complete fixtures / 38 team rows; captured-team-stat coverage 19.19%.
- Player xG/xA source: RESEARCH_SOURCE_EXTERNAL_LOCAL_ATTESTED_MAPPED_TO_PBK.
- Player stat rows: 35499; уникальных игроков: 5101.
- Player Grade rows: 35499; уникальных игроков: 5101.
- Current roster: 112 команд / 3452 игроковых строк.
- Player profile evidence: 3178 rows (3079 team-source + 99 residual-ID) / 3093 players / 111 teams; current-roster coverage 84.2%; identity-ready 2877 players (78.81%).
- Roster history: 112 команд / 112 team-snapshots / 3450 строк.
- Membership intervals: 3450 (open 3450, closed-by-observed-absence 0).
- Verified PBK↔Transfermarkt identities: 2009 rows / 2009 PBK players; invalid 572.
- Verified historical transfers: 14526 rows / 1820 PBK players; dates 1995-07-01 → 2027-06-30; invalid 4944.
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
