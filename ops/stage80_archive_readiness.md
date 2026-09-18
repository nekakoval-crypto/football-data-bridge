# PBK Stage80 Archive Readiness

Обновлено UTC: 2026-09-18T18:55:21Z
Статус: **COLLECTING**

## Покрытие
- Fixtures в текущем inventory: 129 (finished: 1).
- Fixture history: 178 unique fixtures / 1796 observations / 14 observation runs (finished observed: 44).
- Historical fixture catalog: 178 fixtures (terminal 44, rescheduled 1), history coverage 100.00%; missing 0, orphan 0.
- Finished fixtures с player stats: 0 / 1 (0.00%).
- Stage77 durable backlog: pending 39; captured 5; total 44.
- Normalized lineup archive: 6 rows / 2 fixtures; injury archive: 51 rows / 2 fixtures.
- Match event archive: 16 rows / 1 fixtures; backlog pending 0 / total 1.
- Stage81 durable backlog: pending 1; captured 7; total 8.
- Team match statistics: 7 complete fixtures / 14 team rows; current finished coverage 0.00%.
- Team xG: 4 complete fixtures / 8 team rows; captured-team-stat coverage 57.14%.
- Player xG/xA source: RESEARCH_SOURCE_EXTERNAL_LOCAL_ATTESTED_MAPPED_TO_PBK.
- Player stat rows: 215; уникальных игроков: 215.
- Player Grade rows: 215; уникальных игроков: 215.
- Current roster: 96 команд / 2951 игроковых строк.
- Player profile evidence: 2667 rows (2667 team-source + 0 residual-ID) / 2592 players / 96 teams; current-roster coverage 82.5%; identity-ready 2419 players (77.45%).
- Roster history: 96 команд / 96 team-snapshots / 2949 строк.
- Membership intervals: 2949 (open 2949, closed-by-observed-absence 0).
- Verified PBK↔Transfermarkt identities: 743 rows / 743 PBK players; invalid 0.
- Verified historical transfers: 5630 rows / 695 PBK players; dates 1998-07-01 → 2026-07-01; invalid 0.
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
- MATCH_CONTEXT_COVERAGE_IS_CANONICAL_SCOPE_ONLY
- PLAYER_PROFILE_PARTIAL_CURRENT_ROSTER_COVERAGE
- TEAM_XG_PARTIAL_CAPTURED_FIXTURE_COVERAGE

Readiness — telemetry only. Этот отчёт не создаёт ставки, не меняет probability/EV, eligibility, stake или Forward journal.
