# Stage77 Historical Player Backfill

Status: **IMPLEMENTED HISTORICAL ARCHIVE COLLECTOR - RESEARCH ONLY**

Purpose:

Populate PBK-owned player match-stat and Player Grade history from the already
persisted PBK16 historical fixture archive.

Pipeline:

`PBK16 fixture archive`
-> `historical candidate selection`
-> `shared API-Football broker`
-> `durable R2 raw archive`
-> `player_stats_snapshots.csv`
-> `player_grade_snapshots.csv`
-> `Stage78 research`
-> `Stage72 SQLite`
-> `Stage73 archive API`

## Source denominator

The collector reads:

`ops/pbk16_all_competition_fixture_history.csv`

Only historical terminal fixtures (`FT`, `AET`, `PEN`, `FINISHED`) are eligible.

It never invents historical fixtures and does not discover competitions by
guessing.

## Resumable state

The collector stores only attempted historical fixture state:

`ops/stage77_historical_player_backfill_state.csv`

Possible attempt results:

- `CAPTURED`
- `NO_DATA`
- `ERROR`

`NO_DATA` is terminal for V1 because the fixture is historical and repeatedly
polling the same empty provider endpoint would waste quota.

`ERROR` remains retryable.

Fixtures already present in both normalized player-stat and Player Grade ledgers
are excluded even when no explicit historical state row exists.

## Priority

V1 processes:

1. domestic leagues;
2. UEFA;
3. cups / other historical competitions;

and within each group starts with the newest season.

The priority improves useful Form-3/Form-5/Form-10 coverage quickly while the
full PBK16 archive remains the eventual denominator.

## API budget

Historical collection uses the existing shared Stage71 budget and protected
reserve.

The scheduled workflow currently permits at most 240 provider calls per run.
The shared daily limit remains 7000 and LIVE/current-round/standings/safety
reserve remains protected.

## Raw archive

The collector uses the existing PBK API-Football broker.

Therefore every successful real provider response is copied into the configured
durable R2/S3 raw archive before downstream normalized research use.

Cache hits never fabricate new raw-provider observations.

## Governance

Historical player backfill:

- is research/archive only;
- is no-lookahead;
- creates no canonical probability;
- creates no EV/value;
- changes no R1/R2/R3 eligibility;
- creates no betting signal;
- changes no stake;
- does not mutate Forward Journal;
- does not convert missing provider data into zeros;
- keeps historical `NO_DATA` explicit.
