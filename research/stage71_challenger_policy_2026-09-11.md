# PBK — Stage 71 League & Market Challenger Policy

Date locked: 2026-09-11
Status: **PREREGISTERED GOVERNANCE — NO AUTOMATIC PROMOTION**

## Goal

Allow the PBK system to change when evidence changes. A league that is weak today may become the strongest future environment for a strategy family, while a currently active league may degrade.

The unit of comparison is **strategy family × league**, not a league in the abstract. A Polish R1-analogue is compared with the same R1 family in Serie A; it is not allowed to replace Serie A merely because a completely different Polish market performs well.

## Locked competition universe

The geographic universe is the 16 leagues in `config/pbk_competition_scope.json`. No additional domestic leagues enter Stage 71 unless the project owner explicitly unlocks the scope.

## Status model

- `DATA_REQUIRED` — comparable history/forward evidence is missing.
- `MONITORING` — data are being collected; no promotion claim.
- `REGIME_DISCOVERY_ELIGIBLE` — a large fresh forward sample suggests the old/missing historical regime may no longer describe the league; this can only start a new preregistered holdout.
- `CHALLENGER` — historical gate passed and prospective monitoring is active.
- `REVIEW_ELIGIBLE` — all locked historical + prospective gates passed; human review is allowed.
- `ACTIVE` — explicitly approved canonical scope.
- `DEGRADATION_REVIEW` — an active family has enough prospective evidence to justify review of deterioration.
- `SUSPENSION_REVIEW` — stronger deterioration threshold reached; still no automatic suspension.
- `SUSPENDED` — only after explicit governance decision.

## Historical challenger gate

A league/family may be called `CHALLENGER` only when a pre-specified rule is evaluated without league-specific tuning and all are true:

1. TRAIN and TEST are chronological and fixed before looking at TEST.
2. TRAIN sample >= 150 bets.
3. TEST sample >= 100 bets.
4. TRAIN ROI > 0.
5. TEST ROI > 0.
6. At least 60% of available seasons are positive, where a season-level split is available.
7. Rule definition, market, stake and settlement are identical to the family being compared.

A dataset with missing prices or incompatible market definitions is `DATA_REQUIRED`, not zero ROI.

## Prospective promotion gate

A `CHALLENGER` becomes only `REVIEW_ELIGIBLE` when all are true:

1. >= 60 settled executable prospective bets.
2. Marathonbet execution coverage >= 90%.
3. Prospective ROI > 0.
4. First chronological half ROI > 0.
5. Second chronological half ROI > 0.
6. No historical backfill into the prospective sample.
7. Same frozen rule/market used for every prospective event; no post-result market substitution.

`REVIEW_ELIGIBLE` is not automatic promotion.

## Regime-change discovery path

The system must remain capable of discovering a league that was historically negative or for which old comparable odds history is unavailable.

A non-active league/family may become `REGIME_DISCOVERY_ELIGIBLE` only after a **fresh prospective discovery sample** satisfies all of:

1. >= 120 settled executable bets.
2. Marathonbet coverage >= 90%.
3. Total discovery-sample ROI > 0.
4. First chronological half ROI > 0.
5. Second chronological half ROI > 0.

This status **cannot promote the strategy**. It only authorizes a new preregistration with a future holdout starting after the discovery sample is frozen. The discovery rows may not be reused as that holdout. A later promotion review therefore requires genuinely new evidence.

This path is how a league such as Poland can emerge as a serious candidate even if it had no old PBK historical dataset, while preventing a good retrospective run from becoming a strategy immediately.

## Active-rule deterioration gate

No active strategy is judged for deterioration before 60 settled executable forward bets.

`DEGRADATION_REVIEW` requires all of:
- >= 60 settled executable forward bets;
- total forward ROI <= 0;
- first chronological half ROI <= 0;
- second chronological half ROI <= 0.

`SUSPENSION_REVIEW` requires all of:
- >= 100 settled executable forward bets;
- total forward ROI <= 0;
- ROI of the most recent 60 settled bets <= 0.

Neither status suspends anything automatically.

## Challenger vs incumbent

A challenger is never allowed to remove a healthy incumbent automatically.

- If challenger = `REVIEW_ELIGIBLE` and incumbent remains healthy, both may be considered for `ACTIVE` after review.
- If challenger = `REVIEW_ELIGIBLE` and incumbent = `DEGRADATION_REVIEW`/`SUSPENSION_REVIEW`, a replacement review may be opened.
- A user-facing “leader” is descriptive only and must not change stakes or canonical eligibility by itself.

## Current seed evidence

For R1/R2, the existing fixed Big-5 audit is the initial comparable evidence. Serie A remains the only `ACTIVE` league for R1/R2. The other Big-5 leagues failed the unchanged historical transfer. The 11 newly locked leagues begin as `DATA_REQUIRED` until comparable historical evidence is built or fresh prospective discovery evidence activates the regime-change path.

## Governance

- No automatic R4/R5 creation.
- No league-specific threshold optimization to manufacture a challenger.
- No changing the market after a result is known.
- Research WATCH never increases canonical exposure.
- Discovery samples and future validation holdouts must remain separated.
- Every promotion, degradation or suspension decision must preserve the evidence snapshot and reason.
