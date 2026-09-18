# PBK Stage80 Archive Readiness

Обновлено UTC: 2026-09-18T22:27:37Z
Статус: **COLLECTING**

## Покрытие
- Fixtures в текущем inventory: 129 (finished: 14).
- Fixture history: 178 unique fixtures / 2183 observations / 17 observation runs (finished observed: 57).
- Historical fixture catalog: 178 fixtures (terminal 57, rescheduled 1), history coverage 100.00%; missing 0, orphan 0.
- Finished fixtures с player stats: 8 / 14 (57.14%).
- Stage77 durable backlog: pending 14; captured 38; total 52.
- Normalized lineup archive: 6 rows / 2 fixtures; injury archive: 51 rows / 2 fixtures.
- Match event archive: 160 rows / 9 fixtures; backlog pending 0 / total 9.
- Stage81 durable backlog: pending 1; captured 20; total 21.
- Team match statistics: 20 complete fixtures / 40 team rows; current finished coverage 92.86%.
- Team xG: 6 complete fixtures / 12 team rows; captured-team-stat coverage 30.00%.
- Player xG/xA source: RESEARCH_SOURCE_EXTERNAL_LOCAL_ATTESTED_MAPPED_TO_PBK.
- Player stat rows: 1634; уникальных игроков: 1546.
- Player Grade rows: 1634; уникальных игроков: 1546.
- Current roster: 96 команд / 2951 игроковых строк.
- Player profile evidence: 2745 rows (2667 team-source + 78 residual-ID) / 2670 players / 96 teams; current-roster coverage 85.15%; identity-ready 2489 players (79.82%).
- Roster history: 96 команд / 96 team-snapshots / 2949 строк.
- Membership intervals: 2949 (open 2949, closed-by-observed-absence 0).
- Verified PBK↔Transfermarkt identities: 1056 rows / 1056 PBK players; invalid 0.
- Verified historical transfers: 7714 rows / 983 PBK players; dates 1998-07-01 → 2027-06-30; invalid 0.
- EPL referee research: 47 referees / 897 referee×team pairs / 3420 source matches; scope EPL_ONLY; penalties unavailable.
- Top-5 API-Football referee backfill: 45 / 45 league-seasons; 16239 fixture rows; referee coverage 99.44%; profiles 453; referee×team pairs 7689.
- Top-5 pre-match research context: 16111 valid rows / 16111 unique matches / 45 of 45 league-seasons; no-lookahead True.
- Pre-match factor research: 2247 profile rows / 237 stability rows; closing 1X2 matches 12459; closing O/U2.5 matches 12459.
- Pre-match walk-forward research: 7685 folds / 1145 summaries; sample-qualified folds 4455; promotes factor False.
- Match context: 6 fixtures; official XI 1; injury evidence 2.

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
- REFEREE_HISTORY_TOP5_PROVIDER_REFEREE_FIELD_PARTIAL
- MATCH_CONTEXT_COVERAGE_IS_CANONICAL_SCOPE_ONLY
- PLAYER_PROFILE_PARTIAL_CURRENT_ROSTER_COVERAGE
- TEAM_XG_PARTIAL_CAPTURED_FIXTURE_COVERAGE

Readiness — telemetry only. Этот отчёт не создаёт ставки, не меняет probability/EV, eligibility, stake или Forward journal.
