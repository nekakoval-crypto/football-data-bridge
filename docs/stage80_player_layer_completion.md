# Stage80 Player Layer Completion

This stage closes the **research/readiness foundation** for PBK checklist item 10 without inventing predictive authority.

## Inputs

- `ops/player_grade_snapshots.csv`
- `ops/player_form_walk_forward.csv`
- `ops/player_importance_research.csv`
- `ops/historical_lineup_snapshots.csv`
- `ops/historical_injury_snapshots.csv`
- `ops/international_duty_player_return_load.csv`
- Stage77/Stage78 telemetry

## Outputs

- `ops/player_layer_availability_research.csv`
- `ops/player_layer_rotation_research.csv`
- `ops/player_layer_completion_readiness.json`

## Hard semantic rules

1. Historical lineup/injury rows captured after the fact remain `RETROSPECTIVE_ONLY`.
2. Retrospective injury evidence is not relabeled as a known pre-match absence.
3. Structural rotation (retained/changed starters) is materialized independently from player quality.
4. XI quality delta is blocked until a strictly-prior player-quality join exists.
5. Player Quality, Current Form, Player Importance, Availability, XI/Rotation and International Return Load remain separate dimensions.
6. Raw components may not be summed into one mega-score without separate validation.
7. This stage cannot create a signal, probability, EV, eligibility change, stake change or Forward Journal mutation.

## Readiness semantics

- `DATA_MISSING` — evidence absent.
- `RESEARCH_ONLY` — useful descriptive/reconstruction evidence, no predictive authority.
- `VALIDATION_PENDING` — evidence pipeline exists and is suitable for validation, but not authorized for betting decisions.
- `OPERATIONAL_AUTHORIZED` is used here only for the **governance separation/double-counting guard**, not for a predictive player factor.

The overall player layer must remain non-operational for betting until absence/return, XI quality/rotation and player-form contributions are validated without lookahead and without double counting.
