# Stage80 — Player Profile Identity Enrichment

Status: **BOUNDED IDENTITY EVIDENCE — NO BETTING AUTHORITY**

Stage80 collects richer API-Football player profiles for already known PBK roster
players so abbreviated roster names can be resolved conservatively without fuzzy
matching.

## Sources

Primary team-season endpoint:

`/players?team=<API_FOOTBALL_TEAM_ID>&season=<SEASON>`

Residual player-ID endpoint:

`/players?id=<API_FOOTBALL_PLAYER_ID>&season=<SEASON>`

The residual path is used only for current PBK roster player IDs still missing
after team-season capture. The player's current team context comes from the PBK
current roster. It is not inferred from a historical or season-statistics team
returned by the residual endpoint.

Both paths use only the shared API-Football broker/backend. Successful real
provider payloads therefore follow the existing raw R2 archive path.

## Durable evidence

PBK profile output:

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
- PBK current team and season;
- capture timestamp and source.

Missing facts remain empty/UNKNOWN. They are never zero-filled.

Residual retry state is stored separately:

`ops/player_profile_residual_state.csv`

Identity key:

- season;
- API-Football player ID.

The ledger records CAPTURED, EMPTY, or ERROR attempts. It is operational retry
state only and never identity/model/betting authority.

## Bounded collection

The operational workflow is deliberately low priority.

Current limits:

- shared daily API ceiling: 7000;
- maximum profile provider calls per run: 400;
- maximum team candidates per run: 96;
- maximum pages per team: 4;
- maximum residual player-ID candidates per run: 400;
- team refresh TTL: 7 days;
- residual EMPTY/CAPTURED retry TTL: 7 days;
- protected reserve for LIVE/current-round/standings/safety remains unavailable
  to this collector.

A team is persisted only after all reported pages are captured successfully.
Partial pagination does not create partial team evidence.

Big-5 teams are prioritized when current-round league context is available.

A successful team+season capture is treated as fresh for 7 days. During that TTL
the collector does not re-query the whole team merely because some roster IDs
were absent from the provider's team-season response.

After the team pass, the collector calculates current-roster IDs still absent
from profile evidence and may call the player-ID endpoint one player at a time.
Only player IDs with exactly one current-roster team context are eligible.

For residual calls:

- a matching profile becomes durable profile evidence;
- an empty valid provider response is recorded as EMPTY and suppressed for the
  retry TTL;
- a transient provider/runtime error is recorded as ERROR but remains retryable;
- an ambiguous current-roster team assignment is skipped rather than guessed;
- protected-budget exhaustion defers the remaining candidates cleanly.

## Identity-ready evidence

A profile row can support the stronger Transfermarkt bridge only when it provides:

- a non-abbreviated full name;
- an explicit birth date;
- current team evidence.

The downstream Stage80 Transfermarkt mapper requires all of the following before
creating `EXACT_PROFILE_NAME_DOB_CURRENT_CLUB/HIGH`:

1. exact full-name match after deterministic normalization;
2. exact date-of-birth match;
3. current-club match;
4. unique PBK owner of the profile name+club+DOB tuple;
5. exactly one Transfermarkt candidate satisfying the tuple.

There is no fuzzy fallback from either the team-source or residual profile
evidence.

## Automation

A successful main player-profile workflow completion triggers the Transfermarkt
mapping workflow. This lets newly collected profile evidence expand the durable
PBK↔Transfermarkt identity bridge without manual file movement.

Stage80 readiness separately reports:

- total valid profile rows;
- team-source profile rows;
- residual player-ID profile rows;
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
