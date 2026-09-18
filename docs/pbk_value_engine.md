# PBK Value Engine v2

Status: **GOVERNED ANALYTIC READ MODEL — NO BETTING AUTHORITY**

Value Engine v2 classifies and ranks descriptive value only after Probability
Engine has attached an official PBK probability to the exact
market/line/selection.

It is the recovered successor to the abandoned PR #71 design, adapted to the
current PBK architecture.

## Source of truth

Input:

`ops/probability_engine_latest.json`

Output:

`ops/value_engine_latest.json`

Official value is allowed only when:

- `probability_status = VALIDATED_CANONICAL_CONTEXT`;
- the exact row carries a valid `p_pbk`;
- the current reference market has
  `p_market_status = NO_VIG_VALID_EXHAUSTIVE`.

Today the official PBK probability contexts remain the already validated
Stage75 R1/R2/R3 exact 1X2 selections. Value Engine does not authorize a new
market model.

## Canonical arithmetic

Value Engine does **not** own a second set of thresholds.

All descriptive ratings are delegated to
`scripts/pbk_calculation_contract.py` / `PBK_CALC_V1`, which is already used
by the immutable Forward Journal and is consistent with the existing Value
Radar.

The contract currently emits:

- `STRONG_VALUE`: EV >= 5% and model-vs-market edge >= 3 percentage points;
- `WATCH_VALUE`: EV >= 2% and model-vs-market edge >= 2 percentage points;
- `MARKET_DISAGREEMENT`: no executable price and model-vs-market edge >= 5 pp;
- `HIGH_PROB_LOW_VALUE`: PBK probability >= 65% with EV below the watch threshold;
- otherwise no descriptive value threshold.

`LONGSHOT_STRONG` is a tag on `STRONG_VALUE` when executable decimal odds are
at least 2.00.

The existing PBK term `WATCH_VALUE` is retained. It is **not** Stage WATCH and
does not create a watch lifecycle row.

## Execution metrics

For an executable row Value Engine also exposes:

- executable odds/bookmaker;
- raw executable implied probability;
- execution edge;
- EV.

Execution edge is informational. It is not a hidden second classification
contract. Rating authority remains `PBK_CALC_V1`.

## Research-only probability

Generic 1X2 forward probability candidates may remain visible for research, but
they are returned as:

`RESEARCH_ONLY_NOT_VALUE_AUTHORIZED`

They receive no official fair odds, Edge, EV, ranking eligibility or best-value
status until their own per-league forward validation authorizes them.

No probability is transferred across market, line or selection.

## Ranking

Only official `STRONG_VALUE` and `WATCH_VALUE` rows are ranking-eligible.

Within a fixture, Value Engine can expose the best official value candidate. This
is a descriptive analytical ranking only. It does not create a bet.

## Separation from Value Radar

The existing Stage75 Value Radar is an append-only first-crossing attention
ledger for prospective evidence.

Value Engine is different:

- Value Radar records first crossings under its prospective evidence rules.
- Value Engine is the current governed classification/read model over
  Probability Engine output.

Both use the same canonical calculation contract semantics. Neither creates a
signal or stake.

## Guardrails

Value Engine:

- adds zero provider/API calls;
- creates no signal;
- creates no Stage WATCH row;
- changes no R1/R2/R3 rule;
- changes no canonical eligibility;
- changes no stake;
- changes no settlement;
- never mutates the immutable Forward Journal;
- creates no UI authority;
- fails closed when Probability Engine is unavailable or current market
  probability is not a valid no-vig exhaustive market.
