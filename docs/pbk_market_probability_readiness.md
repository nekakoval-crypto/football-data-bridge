# PBK Market Probability Readiness

This contract separates four things that must never be conflated:

1. a bookmaker market/price exists;
2. PBK can settle the market outcome;
3. PBK has a validated probability model for this exact market/selection context;
4. PBK may compute actionable value from that probability.

`p_market_no_vig` is a market-implied probability, not PBK's own probability.
`p_pbk` may only be emitted for an explicitly validated context.

## Current state

- 1X2 is only **PARTIAL_VALIDATED**: Stage75 models are validated for locked R1 away-win, R2 away-win, and R3 draw contexts. Generic P1/X/P2 is not validated.
- Match totals, Asian handicap, BTTS, team totals, double chance, DNB and European handicap have market/evidence paths but no validated general PBK probability model yet.
- Markets without a validated model must surface `NO_VALIDATED_MODEL`; they must not receive invented probabilities or EV.

## Historical evidence constraints

The 2016-2026 Football-Data base supports historical price testing for 1X2, O/U 2.5 and Asian handicap. It does not contain equivalent historical bookmaker price coverage for BTTS, team totals, double chance, DNB or European handicap. Those families require forward captured price/outcome evidence for value validation.

## Governance

- Locked R1/R2/R3 definitions are unchanged.
- A rejected hypothesis does not ban a market family forever.
- New models require preregistration, out-of-sample validation and prospective monitoring appropriate to the available data.
- No market is promoted merely because odds are available or a historical outcome frequency looks attractive.
- Research probability/value cannot change canonical eligibility or stake without an explicit approved promotion step.
