# PBK Brain — Grade / Metrics Readiness Audit

This document is the operational truth for checklist item **МОЗГИ #3 — Grades / Metrics Audit**.

## Rule

`CODE_READY` is not the same as `DATA_READY`, and a calculated metric is not the same as a validated predictive feature.

No grade, availability, rotation or matchup metric in this audit may alter canonical R1/R2/R3 eligibility, probability, EV, stake, settlement or the immutable Forward journal before separate out-of-sample validation and explicit project-owner approval.

## Current audit

| Metric | Current status | What exists | What blocks decision use |
| --- | --- | --- | --- |
| Player Overall Grade | DATA_BLOCKED | PBK V1 grade, position weights, component scores, confidence | production player stats/grade history is insufficient |
| Attack | CODE_READY within Overall | aggregate attacking inputs | predictive validation pending |
| Progression | PROXY_LIMITED | pass/dribble proxy | no true progression/event quality in aggregate source |
| Creation | CODE_READY within Overall | chance-creation related aggregate inputs | predictive validation pending |
| Possession | CODE_READY within Overall | aggregate possession/pass inputs | predictive validation pending |
| Defending | CODE_READY within Overall | tackles/interceptions/duels | predictive validation pending |
| Pressing | unavailable in aggregate source | event prototype can represent pressure | no production event feed for locked leagues |
| Discipline | CODE_READY within Overall | fouls/cards/penalties | predictive validation pending |
| Form-5 / Form-10 | DATA_BLOCKED | strict prior-match rolling logic | production grade history is insufficient |
| XI Quality | DATA_BLOCKED | confirmed/expected XI aggregation and no-lookahead logic | insufficient pre-kickoff player-grade coverage |
| Player Importance | DATA_BLOCKED | starts-vs-no-starts, min sample guard, shrinkage | insufficient eligible samples; descriptive, not causal |
| Rotation Count | VALIDATION_PENDING | current XI vs previous XI membership snapshots | needs explicit historical/prospective validation |
| Rotation Quality Impact | DATA_BLOCKED | retained/changed starters + XI quality delta plumbing | player-grade coverage and OOS validation are missing |
| Absence Impact | DATA_BLOCKED | explicit no-lookahead ABSENT evidence + separate importance/player/replacement components | durable availability ledger, coverage and OOS validation |
| Return Impact | DATA_BLOCKED | explicit observed ABSENT → PRESENT/STARTER/BENCH transition | longitudinal availability evidence and OOS validation |
| Team Overall Grade | NOT_IMPLEMENTED | intentionally not an arbitrary average | component incremental value and weighting must be validated first |
| Team Style Profile | FOUNDATION CODE_READY / DATA_BLOCKED | rolling raw 5/10/20 profiles for overall/home/away + per-metric provenance/coverage | durable match-stat/event feeds and later calibration |
| Matchup Grade | DATA_BLOCKED | explicit style vector + directional style-vs-style components | production style evidence and OOS component validation |

## Team Style Profile foundation

The Team Style Profile is now a provider-free, no-lookahead **raw evidence layer**. It is intentionally one step before the 0..10 style vector used by the Matchup foundation.

For each team and target cutoff it can build independent rolling windows of **5 / 10 / 20 previous matches** for:

- overall;
- home only;
- away only.

A match is eligible only if its kickoff is strictly before the target cutoff and the source row itself was observed no later than the cutoff. Every usable row needs explicit `source` and aware `observed_at_utc` provenance.

The profile exposes raw descriptive metrics such as shots, shots on target, xG/xGA when actually present, possession, corners, pass accuracy and any richer event metrics that later become available. Missing metrics stay `UNKNOWN`; they are never zero-filled. Partial coverage is retained explicitly through `sample_size`, `window_matches` and `coverage_pct`.

The engine does **not** manufacture a style rating from these raw fields. A candidate link such as `ppda/high_turnovers -> PRESS_INTENSITY` or `progressive_passes/carries -> CENTRAL_PROGRESSION` is recorded only as `REQUIRES_CALIBRATION`. No 0..10 value is emitted until a separate historical/OOS calibration is designed and validated.

Source truth at this stage:

- **API-Football fixture statistics** are an intended live source, but there is not yet a durable style-stat archive wired into this profile. The style engine itself adds zero provider calls.
- **Understat** is not currently a production team-match xG feed in PBK. The existing repository workflow clones an aggregate player dataset artifact, so it must not be mislabeled as live team style data.
- **Football-Data** can provide partial historical shots/corners-style fields where the archived season actually contains them.
- **PBK Formation Research** is available, but remains context only.
- richer pressing/progression/transition/aerial/field-tilt features require a detailed event source that is not connected yet.

## Matchup / Style-vs-Style foundation

The Matchup foundation is now code-ready as a **research representation**, not as a betting score.

It keeps explicit style dimensions separate and builds directional components such as:

- press intensity vs buildup resistance;
- transition attack vs transition defence;
- width attack vs wide defence;
- aerial/direct attack vs aerial defence;
- set-piece attack vs set-piece defence;
- low-block breaking vs low-block defence;
- central progression vs central compactness.

Each usable dimension must carry an explicit source and aware `observed_at_utc` timestamp known before the target kickoff/cutoff. Post-cutoff evidence is rejected. Missing evidence stays `UNKNOWN`; it is never converted to zero.

**Formation alone is not style.** A `4-3-3`, `3-4-2-1`, etc. may be retained as context, but formation names do not create a style vector or matchup signal by themselves.

Directional deltas are transparent descriptive components only. There is deliberately no combined Matchup Grade, selected winner, hand-written component weight, probability adjustment or stake change.

## Production evidence at audit time

Stage77/Stage78 still do not provide enough real player-grade history to validate Player Overall, XI Quality, Player Importance, Rotation Quality, Absence or Return components. API reserve protections must not be weakened merely to populate research grades.

The Team Style Profile code can now consume historical match-stat/event rows safely, but production source coverage is still incomplete. Existing formation research is useful context, but formation observations cannot substitute for event/style evidence.

## Source limitations that must remain visible

The aggregate Player Grade source cannot honestly claim full event quality:

- progression is proxy-only;
- pressing is unavailable in the aggregate source;
- aggregate data cannot reconstruct true action quality;
- provider rating may be retained as reference only and is not PBK Overall Grade.

Matchup style evidence must preserve the same honesty: if a required event/style feature is unavailable, that component remains unknown rather than inferred from a formation or team name.

## Validation gates

1. Preserve API safety and allow Stage77 to capture real finished-fixture player data when budget permits.
2. Accumulate sufficient strictly prior-match grade history.
3. Validate grade stability by position and sample size.
4. Test Form-5/Form-10 versus season baseline without leakage.
5. Validate XI Quality and XI delta versus market baseline/team strength.
6. Evaluate Player Importance stability and confounding; do not make causal claims from starts-vs-no-starts alone.
7. Populate explicit availability evidence and validate Absence/Return components independently.
8. Populate durable pre-kickoff Team Style Profile evidence for 5/10/20 overall/home/away windows.
9. Calibrate raw style inputs into explicit style dimensions without hand-written weights or leakage.
10. Validate every directional matchup component out of sample against future outcomes and market residuals.
11. Only after component evidence exists, evaluate whether a Team Overall Grade or composite Matchup Grade adds incremental predictive information. Do not create either by arbitrary averaging.

## Separate identity issue discovered by audit

`player_grade_context.py` currently contains a compatibility fallback that can parse a team id from a team-logo URL when an explicit provider team id is absent. This conflicts with the newer PBK identity governance: provider IDs must come from provider identity fields, never be reconstructed from logo URLs or fuzzy team names. It should be removed as part of Team Identity Foundation, while legacy observations without real IDs remain blank/unknown.

## UI freeze

No UI work is required by this audit. Grade and matchup readiness are brain/data/governance concerns.
