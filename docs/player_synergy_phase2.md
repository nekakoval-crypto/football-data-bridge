# PBK Item 11 — Phase 2: market-adjusted validation and substitutions

This phase continues the player-synergy foundation without promoting it to betting authority.

## Market-adjusted research

`player_synergy_walk_forward.csv` is joined by exact API-Football `fixture_id`
to `pbk14_congestion_market_join_research.csv`.

For each team-side row the stage derives the bookmaker no-vig win probability
from closing 1X2 prices and evaluates the strictly-prior PAIR / TRIO / LINE
dimensions separately against the market residual:

`actual_win - closing_no_vig_win_probability`.

The dimensions are never summed into a mega-score.  Chronological train,
validation and late-holdout buckets are reported independently.  Congestion
flags are retained as contextual controls.  This is
`MARKET_ADJUSTED_ASSOCIATION_ONLY`, not a probability model.

## Substitution interaction dataset

The substitution layer joins durable `match_event_snapshots.csv` events to the
latest official `lineup_snapshots.csv` observation captured before kickoff.

For API-Football substitution events:
- `player_id` is the player leaving;
- `assist_id` is the player entering.

The dataset records exact `team_id:out->in` transition identities and whether
the outgoing/incoming player belonged to the official starting XI.

Substitution events are `POSTMATCH_FACTUAL`.  They can train later historical
models but cannot be used as if they were known prematch.

## Authority

This phase may resolve data-engineering/research gates only.  It cannot create
signals, PBK probabilities, EV/value, eligibility or stake authority.

Predictive item-11 closure still requires a dedicated specialist model,
genuine prematch evidence and broader contextual-confounder validation.
