# Stage80 — archive read API

Status: **READ-ONLY PROVIDER-FREE ARCHIVE ACCESS**

Stage73 now exposes PBK-owned historical evidence without polling API-Football.

## Endpoints

### GET /v1/archive/fixture?fixture_id=<id>

Returns, when available:

- normalized historical fixture row;
- append-only fixture observations;
- official lineup archive rows;
- injury evidence rows;
- match event rows;
- team match statistics;
- player match statistics.

### GET /v1/archive/player?player_id=<id>

Returns, when available:

- historical player catalog row;
- roster-history observations;
- observed membership intervals;
- captured player match statistics;
- research Player Grade rows.

Both endpoints are read-only and use only the Stage72 SQLite projection built from PBK-persisted CSV evidence.

## Contract

- no provider calls;
- missing archive layers remain empty arrays instead of fabricated data;
- a fixture/player may be partially covered;
- `partial_sources_possible = true` is explicit;
- no probability, EV/value, R1/R2/R3 eligibility, stake, settlement, model or Forward mutation;
- API-Football remains responsible for current operational collection, while these endpoints read PBK's own persisted archive.

This is the first archive-facing backend surface. It does not yet expose external historical artifacts such as Football-Data or Transfermarkt mapping packages until those sources have a separately approved normalized warehouse materialization path.
