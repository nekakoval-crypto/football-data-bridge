# Stage80 — API-Football Top-5 referee historical backfill

Status: **HISTORICAL RESEARCH / ARCHIVE ENRICHMENT**

This layer complements the existing Football-Data EPL referee research archive with a provider-side Top-5 referee fixture history.

## Scope

Five domestic leagues:

- Premier League — API-Football league 39
- Bundesliga — 78
- Serie A — 135
- La Liga — 140
- Ligue 1 — 61

Completed seasons: **2017/18 through 2025/26**. API-Football uses the season start year, so the query matrix is 2017…2025.

The matrix contains exactly **45 league-season queries**.

## Collection

Endpoint:

`/fixtures?league=<id>&season=<year>`

The capture uses the shared API-Football broker, shared daily call state and durable raw S3 archive. It keeps a persistent league-season state file, so already-captured cells are not requested again on later runs.

A full first run needs at most 45 logical provider calls. A protected daily reserve is maintained for LIVE/current-round operational traffic.

## Durable outputs

- `top5_referee_fixture_history.csv` — provider fixture/referee evidence;
- `top5_referee_profiles_research.csv` — league-scoped referee result/goal aggregates;
- `top5_referee_team_splits_research.csv` — league+referee+team historical result/goal splits;
- `stage80_top5_referee_backfill_state.csv` — resumable league-season collection state;
- `stage80_top5_referee_backfill_last_run.json` — capture telemetry.

## Important limitations

- API-Football exposes referee as text in the fixture payload; this layer does **not** claim a stable provider referee ID.
- Exact referee strings are aggregated only inside each league to avoid inventing cross-league identity.
- The `/fixtures` payload does not provide the historical foul/card/penalty totals needed for richer officiating profiles. Cards, fouls and penalties therefore remain **UNAVAILABLE**, not zero.
- The existing Football-Data EPL archive remains useful as an independent richer EPL source for fouls/cards.
- Missing referee text remains **UNKNOWN** and is reported as coverage telemetry.
- Referee/team splits are descriptive associations only. They do not establish bias, causation, probability, EV or betting eligibility.

## Governance

This layer is:

- historical backfill only;
- research only;
- not operational betting authority;
- unable to mutate R1/R2/R3 eligibility;
- unable to mutate probability, EV/value, stake or Forward journal.
