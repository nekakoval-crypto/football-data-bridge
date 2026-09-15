# Stage80 Historical Player Catalog

Status: **IMPLEMENTED DERIVED WAREHOUSE SLICE — production materialization pending**

`ops/historical_players.csv` is a provider-free deterministic projection over already persisted player evidence:

- `ops/team_roster_history.csv` — observed squad membership snapshots;
- `ops/player_stats_snapshots.csv` — observed player-match statistics.

Both source ledgers remain authoritative. The player catalog is only a rebuildable warehouse convenience layer.

## One row per player

Identity: `player_id`.

The catalog records:

- latest observed player name and position;
- latest observed roster-only metadata such as age, shirt number and photo URL;
- first and last evidence timestamps across roster/stat sources;
- latest roster observation timestamp and latest stats observation timestamp;
- roster observation count and number of distinct observed teams;
- team IDs/names present in the **latest roster snapshot timestamp**;
- number of fixtures with captured player stats;
- explicit source-presence flags and evidence source list.

## Anti-inference rules

The catalog intentionally does **not** expose a field called `current_team`.

`latest_roster_team_ids` / `latest_roster_team_names` mean only: teams in which the player was observed at the latest persisted roster snapshot timestamp. They are not proof of the player’s current club and are not converted into an exact transfer event.

The projection also does not fabricate:

- exact transfer dates;
- current squad membership when snapshots are stale or absent;
- xG / xA;
- player value or importance beyond explicitly available evidence.

## Bootstrap and integrity

- If neither roster history nor player stats has materialized, the catalog is header-only and metadata status is `WAITING_SOURCE`.
- A player may legitimately appear from stats evidence before roster evidence, or vice versa.
- Source rows without `player_id` are rejected, counted and make the catalog status `ATTENTION`.
- Projection order is deterministic for timestamped evidence.

## Safety

Provider calls: **0**.

The layer is registered in Stage80 Archive Manifest as `DERIVED_WAREHOUSE`; it cannot create signals or mutate probability, EV, R1/R2/R3 eligibility, stake, settlement or the Forward journal.
