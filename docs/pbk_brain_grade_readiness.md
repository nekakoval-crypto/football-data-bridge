# PBK Brain — Grade / Metrics Readiness Audit

This document is the operational truth for checklist item **МОЗГИ #3 — Grades / Metrics Audit**.

## Rule

`CODE_READY` is not the same as `DATA_READY`, and a calculated metric is not the same as a validated predictive feature.

No grade/lineup metric in this audit may alter canonical R1/R2/R3 eligibility, probability, EV, stake, settlement or the immutable Forward journal before separate out-of-sample validation and explicit project-owner approval.

## Current audit

| Metric | Current status | What exists | What blocks decision use |
| --- | --- | --- | --- |
| Player Overall Grade | DATA_BLOCKED | PBK V1 grade, position weights, component scores, confidence | production player stats/grade history is empty |
| Attack | CODE_READY within Overall | aggregate attacking inputs | predictive validation pending |
| Progression | PROXY_LIMITED | pass/dribble proxy | no true progression/event quality in aggregate source |
| Creation | CODE_READY within Overall | chance-creation related aggregate inputs | predictive validation pending |
| Possession | CODE_READY within Overall | aggregate possession/pass inputs | predictive validation pending |
| Defending | CODE_READY within Overall | tackles/interceptions/duels | predictive validation pending |
| Pressing | unavailable in aggregate source | event prototype can represent pressure | no production event feed for locked leagues |
| Discipline | CODE_READY within Overall | fouls/cards/penalties | predictive validation pending |
| Form-5 / Form-10 | DATA_BLOCKED | strict prior-match rolling logic | zero production grade rows |
| XI Quality | DATA_BLOCKED | confirmed/expected XI aggregation and no-lookahead logic | XI exists, but covered players=0 and quality is blank |
| Player Importance | DATA_BLOCKED | starts-vs-no-starts, min sample guard, shrinkage | zero production importance rows; descriptive, not causal |
| Rotation Count | VALIDATION_PENDING | current XI vs previous XI membership snapshots | needs explicit historical/prospective validation |
| Rotation Quality Impact | DATA_BLOCKED | XI-quality delta plumbing exists | player grade coverage is empty |
| Absence Impact | NOT_IMPLEMENTED | hypothesis only | needs confirmed absence + importance/grade + replacement quality |
| Return Impact | NOT_IMPLEMENTED | hypothesis only | needs longitudinal observed presence/absence evidence |
| Team Overall Grade | NOT_IMPLEMENTED | intentionally not an arbitrary average | component incremental value must be validated first |
| Matchup Grade | NOT_IMPLEMENTED | hypothesis only | needs explicit style/event features and validation |

## Production evidence at audit time

Stage78 is `WAITING`: `grade_rows=0`, `importance_rows=0`, while four XI history rows exist. Those XI rows have 11 named starters but `covered_players=0`, `coverage_pct=0`, `grade_confidence=UNKNOWN`, and blank XI quality values.

Stage77 has a durable backlog of finished fixtures, but protected API reserve currently defers `/fixtures/players`; this must not be weakened merely to populate research grades.

## Source limitations that must remain visible

The aggregate Player Grade source cannot honestly claim full event quality:

- progression is proxy-only;
- pressing is unavailable in the aggregate source;
- aggregate data cannot reconstruct true action quality;
- provider rating may be retained as reference only and is not PBK Overall Grade.

## Validation gates

1. Preserve API safety and allow Stage77 to capture real finished-fixture player data when budget permits.
2. Accumulate sufficient strictly prior-match grade history.
3. Validate grade stability by position and sample size.
4. Test Form-5/Form-10 versus season baseline without leakage.
5. Validate XI Quality and XI delta versus market baseline/team strength.
6. Evaluate Player Importance stability and confounding; do not make causal claims from starts-vs-no-starts alone.
7. Define Absence/Return metrics only from observed evidence and replacement quality.
8. Only after component evidence exists, evaluate whether a Team Overall Grade or Matchup Grade adds out-of-sample predictive information.

## Separate identity issue discovered by audit

`player_grade_context.py` currently contains a compatibility fallback that can parse a team id from a team-logo URL when an explicit provider team id is absent. This conflicts with the newer PBK identity governance: provider IDs must come from provider identity fields, never be reconstructed from logo URLs or fuzzy team names. It should be removed as part of Team Identity Foundation, while legacy observations without real IDs remain blank/unknown.

## UI freeze

No UI work is required by this audit. Grade readiness is a brain/data/governance concern.
