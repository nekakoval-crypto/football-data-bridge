# Stage80 Player Layer Finalization

This stage is the final provider-free data/research pass for PBK checklist item 10.

## What it solves

1. Rebuilds `player_importance_research.csv` from the historical official-XI archive plus terminal results instead of relying only on the tiny current-round rotation sample.
2. Builds XI quality using **only player-match grades from fixtures strictly earlier than the target fixture**.
3. Compares current and previous XI membership at the same target cutoff, preventing target-match performance from entering the XI quality delta.
4. Builds rotation/outcome, absence/outcome and return-reconstruction datasets.
5. Emits a final readiness document separating data-engineering completion from predictive betting authority.

## Temporal semantics

Historical lineup and injury endpoints were queried retrospectively. Therefore:

- `RETROSPECTIVE_ONLY` means the evidence describes what happened historically;
- `RETROSPECTIVE_CHRONOLOGY_ONLY` means a feature is reconstructed using only earlier fixture chronology;
- neither status proves the information was actually observed before kickoff at that historical time.

This distinction is mandatory. The stage cannot turn retrospective injury data into a historical PREMATCH_FROZEN fact.

## Player Importance

The research estimate compares team results in captured official-XI fixtures where a player starts vs captured fixtures where that player does not start.

Minimum sample:
- 5 starts;
- 5 non-starts.

The score is shrunk and explicitly non-causal. It is suitable for downstream research/validation, not automatic betting decisions.

## XI quality

For every target XI:

- player grade rows must belong to an earlier fixture kickoff;
- target-match grade is excluded;
- only rows with >=30 minutes are used;
- up to five strictly earlier matches are averaged;
- XI quality delta requires at least 8 covered players in both current and previous memberships.

## Availability / return

Injury and reconstructed-return datasets are descriptive only because historical retrieval timestamps are after the fixtures. Genuine pre-match absence/return validation still requires evidence that was actually captured before kickoff.

## Closure semantics

The final readiness file can state:

- **DATA/RESEARCH FOUNDATION COMPLETE**
- while simultaneously stating:
- **PREDICTIVE AUTHORITY NOT AUTHORIZED**

That is intentional. PBK does not convert data coverage into betting authority without market-adjusted out-of-sample validation and trustworthy prematch temporal evidence.
