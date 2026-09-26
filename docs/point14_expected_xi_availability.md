# PBK Point 14A — Expected XI Availability + Suspension Gate V1

## Purpose

This layer resolves whether a player can enter the Expected XI candidate pool
for a specific prematch fixture.

It is evidence-first and fail-closed.

## Red-card / suspension contract

A red card by itself is not treated as an automatic next-match ban.

The chain is:

`RED_CARD_EVENT`
→ `SUSPENSION_PENDING / CONFIRMED_SUSPENSION`
→ `APPEAL_PENDING / APPEAL_REJECTED / SUSPENSION_OVERTURNED / SUSPENSION_REDUCED`
→ final fixture-specific availability.

Competition scope must match the target fixture.

A suspension may be:
- upheld;
- overturned;
- reduced;
- already served;
- irrelevant to a different competition.

Therefore only a confirmed, still-applicable suspension may force
`P(start)=0`.

## Injury contract

- confirmed OUT → unavailable;
- doubtful/questionable → uncertain;
- cleared/fit → available.

Uncertainty is preserved rather than converted into a false binary decision.

## Output

- AVAILABLE
- UNCERTAIN
- UNAVAILABLE

`UNAVAILABLE` means the player must be excluded from Expected XI and receives
a hard probability ceiling of zero.

`UNCERTAIN` means Expected XI must preserve uncertainty.

## Governance

Provider-free foundation only.

This module cannot:
- create a signal;
- mutate PBK probability;
- mutate R1/R2/R3 eligibility;
- create EV/value;
- change stake;
- mutate Forward Journal.

Next phase wires persisted discipline, injury, registration and transfer evidence
into this resolver, then builds the positional Expected XI specialist.
