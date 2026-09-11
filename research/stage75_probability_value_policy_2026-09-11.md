# Stage75 — PBK Probability & Value Engine — preregistration

Date locked: 2026-09-11
Status at creation: PREREGISTERED_BEFORE_TEST_METRICS

## Purpose
PBK must answer two different questions without conflating them:
1. **Максимальная вероятность прохода** — which currently valid canonical exposure has the highest validated estimated probability of winning.
2. **Лучший value** — which currently valid canonical exposure has the largest validated expected edge at the executable user price.

These rankings are not the same thing.

## Scope v1
Only already-locked canonical rule families are eligible:
- R1 — Serie A away favourite, locked odds/eligibility definition.
- R2 — locked R1 subset with current-season last-5 PPG condition.
- R3 — locked Big-5 Monday/end-season draw candidate definition.

WATCH, challenger, discovery and deferred markets are excluded from recommendation rankings in v1. They may later receive their own separately validated probability models.

## Historical split
- R1/R2 TRAIN: 2016/17–2021/22.
- R1/R2 TEST: 2022/23–2025/26.
- R3 TRAIN: modern seasons 2019/20–2021/22.
- R3 TEST: 2022/23–2025/26.

TEST is never used to fit or choose the calibrator.

## Market baseline M0
For the selected outcome, calculate Bet365 1X2 no-vig probability from the first historical price snapshot available under the locked rule definition:

`p_market = (1 / selected_odds) / ((1/H) + (1/D) + (1/A))`

This is explicitly labelled **market probability**, not PBK probability.

## Candidate calibrator M1
Rule-specific one-parameter logit shift only:

`p_pbk = logistic(logit(p_market) + alpha_rule)`

`alpha_rule` is fitted on TRAIN only by Bernoulli maximum likelihood.

Why intentionally simple:
- preserves most information in the market price;
- allows a locked rule's historical conditional edge to shift the probability;
- low parameter count reduces overfit risk;
- makes every prediction reproducible and auditable.

No slope fitting, form features, xG, injuries, lineups, weather or post-kickoff information are allowed in v1.

## TEST acceptance gate — fixed before metrics
A rule may expose `PBK_PROBABILITY_VALIDATED` only if all are true:
1. TEST N >= 80 settled historical rule observations.
2. M1 Brier score is strictly lower than M0 Brier score.
3. M1 log-loss is not worse than M0 log-loss.
4. Absolute TEST calibration-in-the-large error `abs(mean(p_pbk) - observed_hit_rate)` <= 0.05.
5. No future information is used; historical predictor is available at the rule's decision time.

If any gate fails, UI continues to show market probability only and PBK probability remains `NOT_VALIDATED` for that rule.

No threshold may be weakened after TEST is opened.

## Forward ranking rules
When/if a rule passes:
- **Макс. вероятность** sorts unique active canonical exposures by frozen `p_pbk` descending.
- **Лучший value** sorts by `EV = p_pbk * executable_user_odds - 1` descending.
- Display `p_market` separately from `p_pbk`.
- An exposure with negative EV is never called value-positive merely because its win probability is high.
- R1+R2 same fixture/selection remain one logical exposure; if R2 is active and validated, its more-specific validated calibrator is used, otherwise R1.
- R3 versus R1/R2 opposite selections on one fixture remains MANUAL_REVIEW, never an automatic two-sided recommendation.

## Forward validation after historical gate
Passing historical TEST does not make the probability model immortal.
Every forward probability is frozen before kickoff and appended prospectively. Review calibration after >=50 settled predictions per rule using Brier/log-loss/calibration-in-the-large. No historical backfill into the forward probability ledger.

## Governance
- This module ranks already-valid signals; it does not create new strategy eligibility.
- It cannot alter stake sizing in v1.
- It cannot alter R1/R2 odds bounds or any rule threshold.
- It cannot promote WATCH/challenger to canonical.
- Probability estimates are decision support, never certainty.
