# Stage80 — ClubElo daily archive

Status: **EXTERNAL STRENGTH ENRICHMENT — POINT-IN-TIME ARCHIVE**

PBK stores one daily ClubElo snapshot as append-only historical enrichment.

ClubElo explicitly permits reuse of its calculations/rankings with citation. PBK records attribution to ClubElo.com / Lars Schiefler and keeps the source URL on every row.

## Source

Daily CSV endpoint:

`api.clubelo.com/<YYYY-MM-DD>`

The source exposes club, country, level, Elo and effective From/To boundaries. PBK archives the point-in-time daily response rather than repeatedly asking the source for the same date.

## Identity

`snapshot_date + club + country`

The first observation for one date/club/country wins. A later repeated run for the same day is idempotent and does not rewrite the original row.

## Cadence

The workflow runs once daily at 05:27 UTC and may also be run manually. HTTPS is attempted first with HTTP fallback because the public source is historically documented on the HTTP API endpoint.

## Governance

ClubElo is a research/enrichment strength baseline only.

It is not:
- API-Football replacement;
- PBK canonical probability;
- R1/R2/R3 eligibility authority;
- EV/value authority;
- stake/settlement/Forward authority.

Rows with missing club/country/Elo identity are rejected, never zero-filled. Team-name mapping to PBK entities is a separate step and must preserve source provenance.
