# Stage80 — Player Profile Identity Enrichment

Status: **BOUNDED IDENTITY EVIDENCE — NO BETTING AUTHORITY**

Stage80 collects richer API-Football player profiles for already known PBK roster
teams so abbreviated roster names can be resolved conservatively without fuzzy
matching.

## Source

Provider endpoint:

`/players?team=<API_FOOTBALL_TEAM_ID>&season=<SEASON>`

The collector uses only the shared API-Football broker/backend. Successful real
provider payloads therefore follow the existing raw R2 archive path.

## Durable evidence

PBK output:

`ops/player_profile_evidence.csv`

Identity key:

- API-Football team ID;
- season;
- API-Football player ID.

Persisted fields include:

- provider player ID;
- display name;
- first name;
- last name;
- birth date;
- birth place/country;
- nationality;
- height/weight;
- provider team and season;
- capture timestamp and source.

Missing facts remain empty/UNKNOWN. They are never zero-filled.

## Bounded collection

The operational workflow is deliberately low priority.

Current limits:

- daily shared API ceiling: 7000;
- maximum profile calls per run: 24;
- maximum teams per run: 8;
- maximum pages per team: 4;
- protected reserve for LIVE/current-round/standings/safety remains unavailable
  to this collector.

A team is persisted only after all reported pages are captured successfully.
Partial pagination does not create partial team evidence.

Big-5 teams are prioritized when current-round league context is available.

## Identity-ready evidence

A profile row can support the stronger Transfermarkt bridge only when it provides:

- a non-abbreviated full name;
- an explicit birth date;
- current team evidence.

The downstream Stage80 Transfermarkt mapper requires all of the following before
creating `EXACT_PROFILE_NAME_DOB_CURRENT_CLUB/HIGH`:

1. exact full-name match;
2. exact date-of-birth match;
3. current-club match;
4. unique PBK owner of the profile name+club+DOB tuple;
5. exactly one Transfermarkt candidate satisfying the tuple.

There is no fuzzy fallback from profile evidence.

## Automation

A successful main player-profile workflow completion triggers the Transfermarkt
mapping workflow. This lets newly collected profile evidence expand the durable
PBK↔Transfermarkt identity bridge without manual file movement.

Stage80 readiness separately reports:

- profile rows;
- unique profiled players/teams;
- current-roster profile coverage;
- identity-ready player coverage.

## Governance

Player-profile evidence:

- is identity/research enrichment only;
- does not replace canonical PBK/API-Football player IDs;
- creates no probability, EV or value;
- creates no signal;
- changes no R1/R2/R3 eligibility;
- changes no stake or settlement;
- does not mutate Forward Journal;
- never grants betting/model authority to Transfermarkt or StatsBomb research.
