# PBK Generic 1X2 Probability v1 — forward review protocol

Date: 2026-09-16  
Authority: RESEARCH  
Historical result: `PASS_HISTORICAL_PROBABILITY_GATE`  
Forward phase: `FORWARD_REVIEW_REQUIRED`

## Purpose

Generic 1X2 Probability v1 passed its preregistered historical out-of-sample probability gate on the Big-5 historical domain. The improvement over the Bet365 no-vig baseline was positive but small. The next phase is prospective forward monitoring, not production promotion.

This protocol freezes the forward rules before prospective outcomes accumulate. It does not create a betting strategy and does not authorize value, stakes, canonical status, production use, or UI use.

## Frozen model

The model is unchanged from the historical PASS:

- M0: Bet365 1X2 no-vig probabilities.
- M1: `softmax(log(p_market_c) + alpha_c)`.
- `alpha_H = -0.018000000000000002`
- `alpha_D = 0.0`
- `alpha_A = -0.004`

No fitting, tuning, subgroup rescue, league-specific adjustment, odds-band adjustment, or parameter update is allowed inside Generic 1X2 v1 forward monitoring.

Any changed model requires a separately named/versioned research protocol.

## Locked 16-league capture universe

PBK's locked competition universe contains 16 leagues. Forward capture therefore does not discard the 11 extended leagues.

### VALIDATED_DOMAIN — official Generic 1X2 v1 forward gate

These are the same five league families represented in the historical OOS validation:

- Premier League
- La Liga
- Serie A
- Bundesliga
- Ligue 1

Only settlements from this domain can enter the formal Generic 1X2 v1 forward gate.

### EXTENDED_SHADOW_RESEARCH — collected, scored, but excluded from the official gate

These 11 leagues are captured prospectively from the same day forward:

- Austrian Bundesliga
- Belgian Pro League
- Danish Superliga
- A Lyga
- Virsliga
- Eredivisie
- Eliteserien
- Ekstraklasa
- Primeira Liga
- Super Lig
- Scottish Premiership

For these leagues the same frozen M1 transform is applied and the same probability-quality metrics are recorded. This is transfer/shadow research only because the historical Generic 1X2 v1 TEST did not validate these leagues.

Their results must never be pooled into, rescue, weaken, strengthen, or otherwise alter the official Big-5 forward gate.

A future decision about extending the validated domain requires a separate explicit governance decision and, if needed, a separately preregistered model/version.

## Market and snapshot rule

Market:

`Bet365 Match Winner 1X2`

A fixture is eligible for freezing only when a complete valid Bet365 H/D/A vector is observed before kickoff.

There is:

- no bookmaker substitution;
- no Avg-odds fallback;
- no historical backfill;
- no retroactive reconstruction of a missed prematch observation.

For each fixture, freeze the:

`FIRST_COMPLETE_VALID_BET365_PREMATCH_OBSERVATION`

Both timestamps must be before kickoff:

1. source observation timestamp;
2. monitor processing timestamp.

Once a fixture is frozen, later prices cannot overwrite its forward record.

The frozen record stores:

- league;
- monitoring domain;
- whether it is formal-review eligible;
- M0 H/D/A probabilities;
- M1 H/D/A probabilities;
- immutable frozen alphas.

It contains no result.

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

## Official forward review

Formal Generic 1X2 v1 review uses `VALIDATED_DOMAIN` only.

Diagnostic checkpoints:

- 250 settled validated-domain fixtures;
- 500 settled validated-domain fixtures.

These checkpoints are descriptive only.

Formal forward review is allowed only after:

- at least 1,000 settled validated-domain fixtures;
- at least 150 H outcomes;
- at least 150 D outcomes;
- at least 150 A outcomes.

At the formal review sample all of the following are required:

1. M1 multiclass Brier score is strictly lower than M0.
2. M1 log-loss is strictly lower than M0.
3. M1 absolute class-calibration error is at most 0.03 for H, D and A.
4. Each M1 probability vector sums to one within `1e-9`.
5. All accepted prematch observations satisfy forward-only / no-backfill rules.

Statuses:

- `COLLECTING`
- `FORWARD_REVIEW_READY_PASS`
- `FORWARD_REVIEW_READY_FAIL`

Neither PASS nor FAIL automatically changes canonical or production authority.

## Extended shadow reporting

`EXTENDED_SHADOW_RESEARCH` is reported separately.

Shadow reporting includes:

- number of frozen prematch fixtures;
- number of settled fixtures;
- H/D/A counts;
- M0/M1 Brier;
- M0/M1 log-loss;
- M1 class calibration;
- probability-sum and no-backfill diagnostics.

Shadow status remains `SHADOW_COLLECTING` under this protocol.

There is no automatic shadow promotion and no combined 16-league forward verdict.

## Governance locks

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
- `shadow_excluded_from_official_gate = true`

A forward PASS would authorize a separate governance review only. It would not by itself make Generic 1X2 v1 CANONICAL.

## Implementation boundary

This change implements the provider-free forward ledger/calculation core and guardrail tests for all 16 locked leagues.

It deliberately does **not** wire a live provider polling schedule yet. A later separate integration change may feed genuinely prospective Bet365 H/D/A observations into this core, provided it preserves the frozen protocol exactly and cannot backfill missed fixtures.

The historical canonical CSV is not an input to the forward monitor and must not be used to seed either domain.
