# PBK Generic 1X2 Probability v1 — forward review protocol

Date: 2026-09-16  
Authority: RESEARCH  
Historical result: `PASS_HISTORICAL_PROBABILITY_GATE`  
Forward phase: `FORWARD_REVIEW_REQUIRED`

## Purpose

Generic 1X2 Probability v1 passed its preregistered historical out-of-sample probability gate. The historical improvement over the Bet365 no-vig baseline was positive but small. The next phase is therefore prospective forward monitoring, not production promotion.

This protocol freezes the forward rules before prospective outcomes are accumulated.

It does not create a betting strategy and does not authorize value, stakes, canonical status, or production use.

## Frozen model

The model is unchanged from the historical PASS:

- M0: Bet365 1X2 no-vig probabilities.
- M1: `softmax(log(p_market_c) + alpha_c)`.
- `alpha_H = -0.018000000000000002`
- `alpha_D = 0.0`
- `alpha_A = -0.004`

No fitting, tuning, subgroup rescue, league-specific adjustment, odds-band adjustment, or parameter update is allowed inside v1 forward monitoring.

Any changed model requires a separately named/versioned research protocol.

## Prospective scope

Forward monitoring is limited to the same Big-5 league family:

- Premier League
- La Liga
- Serie A
- Bundesliga
- Ligue 1

Market:

`Bet365 Match Winner 1X2`

A fixture is eligible for freezing only when a complete valid Bet365 H/D/A vector is observed before kickoff.

There is:

- no bookmaker substitution;
- no Avg-odds fallback;
- no historical backfill;
- no retroactive reconstruction of a missed prematch observation.

## Snapshot rule

For each fixture, freeze the:

`FIRST_COMPLETE_VALID_BET365_PREMATCH_OBSERVATION`

Both timestamps must be before kickoff:

1. the source observation timestamp;
2. the monitor processing timestamp.

This dual timestamp rule prevents an old-looking observation from being injected after kickoff.

Once a fixture is frozen, later prices cannot overwrite its forward record.

The frozen record stores both M0 and M1 full H/D/A probability vectors. It contains no result.

## Settlement

Settlement is stored in a separate append-only journal.

A settlement is accepted only when:

- the fixture has a frozen prematch event;
- the result is H, D, or A;
- the settlement timestamp is after kickoff.

Settlement computes only prospective probability-quality metrics:

- multiclass Brier score for M0 and M1;
- multiclass log-loss for M0 and M1;
- M1 H/D/A calibration.

ROI, profit, EV, value labels and stake outcomes are outside this forward probability protocol.

## Forward checkpoints

Diagnostic checkpoints:

- 250 settled fixtures;
- 500 settled fixtures.

These checkpoints are descriptive only. They cannot promote or reject the model.

Formal forward review is allowed only after:

- at least 1,000 settled fixtures; and
- at least 150 H outcomes;
- at least 150 D outcomes;
- at least 150 A outcomes.

The sample thresholds are frozen before prospective results are accumulated.

## Formal review criteria

At the formal review sample, all of the following are required for a forward PASS:

1. M1 multiclass Brier score is strictly lower than M0.
2. M1 log-loss is strictly lower than M0.
3. M1 absolute class-calibration error is at most 0.03 for H, D and A.
4. Each M1 probability vector sums to one within `1e-9`.
5. All accepted prematch observations satisfy forward-only / no-backfill timestamp rules.

If the formal sample is not ready, status is:

`COLLECTING`

If the formal sample is ready and all criteria pass:

`FORWARD_REVIEW_READY_PASS`

If the formal sample is ready and any criterion fails:

`FORWARD_REVIEW_READY_FAIL`

Neither status automatically changes canonical or production authority.

## Governance locks

Forward monitoring has the following fixed policy:

- `authority = RESEARCH`
- `creates_signal = false`
- `value_authorized = false`
- `stake_changes_authorized = false`
- `profitability_or_roi_conclusion = false`
- `r1_r2_r3_changes_authorized = false`
- `production_integration_authorized = false`
- `ui_integration_authorized = false`
- `automatic_canonical_promotion = false`
- `manual_governance_review_required = true`

A forward PASS would authorize a separate governance review only. It would not by itself make Generic 1X2 v1 CANONICAL.

## Implementation boundary of this change

This change implements the provider-free forward ledger/calculation core and its guardrail tests.

It deliberately does **not** wire a live provider polling schedule yet. A later, separate integration change may feed prospectively observed Bet365 H/D/A rows into this core, provided that integration preserves this protocol exactly and cannot backfill missed fixtures.

The historical canonical CSV is not an input to the forward monitor and must not be used to seed the forward journals.
