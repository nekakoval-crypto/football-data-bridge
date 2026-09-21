# PBK Item 11 — Player Synergy Research Foundation

## Purpose

Checklist item 11 introduces a separate research layer for combinations that a
single-player grade cannot represent:

- player pairs;
- player trios;
- positional lines (D / M / F);
- descriptive anti-synergy candidates;
- later: substitutions, bench/starting interactions and rotation combinations.

The key principle is that **Raphinha + Yamal is not assumed to equal the sum of
two Player Grades**.  Combinations must earn their own evidence and later their
own validation authority.

## Inputs

Provider-free persisted PBK evidence only:

- `ops/historical_lineup_snapshots.csv`
- `ops/pbk16_all_competition_fixture_history.csv`

Identity uses exact provider `fixture_id`, `team_id` and `player_id`.
Fuzzy player/team matching is forbidden.

## Outputs

- `ops/player_synergy_pair_research.csv`
- `ops/player_synergy_trio_research.csv`
- `ops/player_synergy_line_research.csv`
- `ops/player_anti_synergy_research.csv`
- `ops/player_synergy_walk_forward.csv`
- `ops/player_synergy_readiness.json`

## Association semantics

Pair/trio/line rows compare observed co-start outcomes with the members' own
team-start outcome baselines.  Positive or negative deltas are **descriptive
associations only**.  They are not causal chemistry estimates and do not imply
a betting edge.

Anti-synergy is deliberately conservative: a combination is only flagged when
it passes the sample gate and both points and goal-difference deltas are
negative.  The flag remains `DESCRIPTIVE_ASSOCIATION_ONLY`.

No arbitrary mega-score is created.

## Strictly-prior walk-forward contract

For each historical team fixture the walk-forward row is materialized **before**
that fixture is added to pair/trio/line history.  Therefore the target match
outcome cannot contribute to its own synergy features.

This protects chronology, but historical lineups were captured retrospectively.
The temporal authority is therefore
`RETROSPECTIVE_CHRONOLOGY_ONLY`, not `PREMATCH_FROZEN`.

## Authority

This foundation may produce research features and validation datasets only.

It must not:

- create a signal;
- mutate probability;
- mutate eligibility;
- change stake;
- claim EV/value;
- promote any pair, trio or line to operational betting authority.

Before operational use, strictly-prior synergy features need market-adjusted,
out-of-sample specialist validation and contextual-confounder controls.
Substitution interactions remain a separate required follow-up.
