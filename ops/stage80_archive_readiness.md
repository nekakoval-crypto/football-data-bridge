# PBK Stage80 Archive Readiness

Обновлено UTC: 2026-09-18T20:44:45Z
Статус: **COLLECTING**

## Покрытие
- Fixtures в текущем inventory: 129 (finished: 9).
- Fixture history: 178 unique fixtures / 1925 observations / 15 observation runs (finished observed: 52).
- Historical fixture catalog: 178 fixtures (terminal 52, rescheduled 1), history coverage 100.00%; missing 0, orphan 0.
- Finished fixtures с player stats: 0 / 9 (0.00%).
- Stage77 durable backlog: pending 14; captured 30; total 44.
- Normalized lineup archive: 6 rows / 2 fixtures; injury archive: 51 rows / 2 fixtures.
- Match event archive: 16 rows / 1 fixtures; backlog pending 0 / total 1.
- Stage81 durable backlog: pending 1; captured 15; total 16.
- Team match statistics: 15 complete fixtures / 30 team rows; current finished coverage 88.89%.
- Team xG: 5 complete fixtures / 10 team rows; captured-team-stat coverage 33.33%.
- Player xG/xA source: RESEARCH_SOURCE_EXTERNAL_LOCAL_ATTESTED_MAPPED_TO_PBK.
- Player stat rows: 1306; уникальных игроков: 1303.
- Player Grade rows: 1306; уникальных игроков: 1303.
- Current roster: 96 команд / 2951 игроковых строк.
- Player profile evidence: 2745 rows (2667 team-source + 78 residual-ID) / 2670 players / 96 teams; current-roster coverage 85.15%; identity-ready 2489 players (79.82%).
- Roster history: 96 команд / 96 team-snapshots / 2949 строк.
- Membership intervals: 2949 (open 2949, closed-by-observed-absence 0).
- Verified PBK↔Transfermarkt identities: 1051 rows / 1051 PBK players; invalid 0.
- Verified historical transfers: 7694 rows / 980 PBK players; dates 1998-07-01 → 2027-06-30; invalid 0.
- EPL referee research: 47 referees / 897 referee×team pairs / 3420 source matches; scope EPL_ONLY; penalties unavailable.
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
- REFEREE_HISTORY_TOP5_PARTIAL_EPL_ONLY
- MATCH_CONTEXT_COVERAGE_IS_CANONICAL_SCOPE_ONLY
- PLAYER_PROFILE_PARTIAL_CURRENT_ROSTER_COVERAGE
- TEAM_XG_PARTIAL_CAPTURED_FIXTURE_COVERAGE

Readiness — telemetry only. Этот отчёт не создаёт ставки, не меняет probability/EV, eligibility, stake или Forward journal.
