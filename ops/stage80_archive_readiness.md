# PBK Stage80 Archive Readiness

Обновлено UTC: 2026-09-26T18:47:09Z
Статус: **COLLECTING**

## Покрытие
- Fixtures в текущем inventory: 128 (finished: 2).
- Fixture history: 306 unique fixtures / 24633 observations / 192 observation runs (finished observed: 173).
- Historical fixture catalog: 306 fixtures (terminal 173, rescheduled 1), history coverage 100.00%; missing 0, orphan 0.
- Finished fixtures с player stats: 0 / 2 (0.00%).
- Stage77 durable backlog: pending 24; captured 149; total 173.
- Normalized lineup archive: 8 rows / 3 fixtures; injury archive: 54 rows / 3 fixtures.
- Match event archive: 2169 rows / 130 fixtures; backlog pending 0 / total 130.
- Stage81 durable backlog: pending 10641; captured 2836; total 13477.
- Team match statistics: 2836 complete fixtures / 5672 team rows; current finished coverage 0.00%.
- Team xG: 894 complete fixtures / 1788 team rows; captured-team-stat coverage 31.52%.
- Player xG/xA source: RESEARCH_SOURCE_EXTERNAL_LOCAL_ATTESTED_MAPPED_TO_PBK.
- Player stat rows: 357846; уникальных игроков: 13931.
- Player Grade rows: 357846; уникальных игроков: 13931.
- Current roster: 138 команд / 4266 игроковых строк.
- Player profile evidence: 3779 rows (3663 team-source + 116 residual-ID) / 3670 players / 129 teams; current-roster coverage 80.62%; identity-ready 3401 players (75.23%).
- Roster history: 138 команд / 154 team-snapshots / 4764 строк.
- Membership intervals: 4268 (open 4264, closed-by-observed-absence 4).
- Verified PBK↔Transfermarkt identities: 4907 rows / 4907 PBK players; invalid 480.
- Verified historical transfers: 32844 rows / 4002 PBK players; dates 1994-07-01 → 2030-06-30; invalid 6056.
- EPL referee research: 47 referees / 897 referee×team pairs / 3420 source matches; scope EPL_ONLY; penalties unavailable.
- Top-5 API-Football referee backfill: 45 / 45 league-seasons; 16239 fixture rows; referee coverage 99.44%; profiles 453; referee×team pairs 7689.
- Top-5 pre-match research context: 16111 valid rows / 16111 unique matches / 45 of 45 league-seasons; no-lookahead True.
- Top-5 historical motivation context: 16111 valid rows / 16111 unique matches / 45 of 45 league-seasons; full-table rows 15631; boundary-tie rows 4434; Europe UNKNOWN_BY_DESIGN; no-lookahead True.
- Top-5 motivation × market research: 2719 profiles / 288 stability rows; closing 1X2 12459; closing O/U2.5 12459; promotes factor False.
- Pre-match factor research: 2247 profile rows / 237 stability rows; closing 1X2 matches 12459; closing O/U2.5 matches 12459.
- Pre-match walk-forward research: 7685 folds / 1145 summaries; sample-qualified folds 4455; promotes factor False.
- Match context: 6 fixtures; official XI 1; injury evidence 3.
- PBK14 historical market bridge: 37327 AUTO/HIGH of 38483 valid source rows; AUTO 18940, HIGH 18387, REVIEW 391, UNMAPPED 765; fuzzy matching False; source coverage 14 / 16 locked leagues.
- PBK14 international-window × market join: 37327 valid rows; closing 1X2 30879; closing O/U2.5 22738; <=72h before 3595; <=72h after 424; player-level UNVERIFIED.
- PBK14 international-window market research: join 37327 rows; descriptive profiles 2686; stability rows 313; closing 1X2 30879; closing O/U2.5 22738; player-level UNVERIFIED.
- PBK14 congestion × market research: join 37327 rows; descriptive profiles 4698; stability rows 494; closing 1X2 30879; closing O/U2.5 22738; promotes factor False.
- PBK14 congestion walk-forward: 16095 valid folds / 2445 summaries; qualified folds 5470; temporal invalid 0; promotes factor False.
- PBK16 all-competition history: catalog 39 valid rows; required unresolved 0; fixture archive 70375 valid rows; domestic anchors 16 / 16 leagues; captured cells 322, provider-unavailable cells 19, pending 0, errors 0.
- PBK16 cup/UEFA congestion: 40989 valid rows / 40989 domestic fixtures; no-lookahead True; future schedule used False; prior UEFA <=72h 3210, prior cup <=72h 1436.
- PBK16 domestic phase audit: 40989 valid rows; table-phase 40731; post-table playoffs 258; split/table rows needing season contract 1747.
- PBK16 format inventory: 144 / 144 cells; captured 143; provider unavailable 1; exact motivation contracts verified 0.
- PBK16 historical table context V2: 39266 valid rows; safe regular prematch —; full-table —; blocked split/table —; post-table —; awarded-taint —.
- PBK16 international windows: 40989 valid rows / 40989 domestic fixtures; calendar windows 39; <=72h before 3956, <=72h after 518; player-level UNVERIFIED; no-lookahead True.

## Raw provider archive
- Storage configured: True.
- Backend: S3.
- Status: OK.
- Durable readback verified: True; verified at 2026-09-26T10:38:07Z.
- Observations: —; unique payloads: —.

## Незакрытые пробелы
- TEAM_STATS_BACKLOG_PENDING
- PLAYER_STATS_BACKLOG_PENDING
- PLAYER_STATS_PARTIAL_FINISHED_FIXTURE_COVERAGE
- TEAM_STATS_PARTIAL_FINISHED_FIXTURE_COVERAGE
- REFEREE_HISTORY_TOP5_PROVIDER_REFEREE_FIELD_PARTIAL
- PBK16_COMPETITION_PROVIDER_SEASONS_PARTIAL
- PBK16_HISTORICAL_TABLE_CONTEXT_INVALID
- PBK14_HISTORICAL_MARKET_BRIDGE_INVALID
- PBK14_HISTORICAL_MARKET_BRIDGE_PARTIAL_MAPPING
- PBK16_HISTORICAL_MARKET_SOURCE_LIMITED_TO_14_LEAGUES
- MATCH_CONTEXT_COVERAGE_IS_CANONICAL_SCOPE_ONLY
- PLAYER_PROFILE_PARTIAL_CURRENT_ROSTER_COVERAGE
- TRANSFER_IDENTITY_INVALID_ROWS
- TRANSFER_HISTORY_INVALID_IDENTITY_ROWS
- TEAM_XG_PARTIAL_CAPTURED_FIXTURE_COVERAGE
- PLAYER_XG_XA_MAPPED_RESEARCH_INVALID_ROWS

Readiness — telemetry only. Этот отчёт не создаёт ставки, не меняет probability/EV, eligibility, stake или Forward journal.
