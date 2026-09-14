# Match Card formations and research audit

The match card shows one pitch: home at the top, away rotated by 180 degrees at
the bottom. Shirts carry numbers and surnames, without player photos. Supplied
`lastname`/`last_name` is preferred; otherwise the last token of the provider's
display name is used, with the full name in the title. Compound surnames therefore
depend on provider metadata. Coach, formation, official/expected status and source
update timestamp are shown per team. Missing data remains explicit.

Complete official XI wins over expected XI. Complete, unique provider positions
(`position: {x,y}`, finite 0–100 team-relative coordinates) take priority, followed
by valid unique `row:column` grid values. Standard formation strings summing to ten
outfield players use schematic rows, ordered by G/D/M/F with stable order within
each group. These positions are labelled as schematic, not measured tactical
coordinates. Unsupported schemes or partial XIs retain the names list and a
no-position state. Supported examples: 4-4-2, 4-3-3, 4-2-3-1, 3-5-2, 3-4-3, 5-3-2,
3-4-2-1. Both teams follow the same orientation everywhere.

## Durable evidence

Stage72 appends changed observations to `ops/formation_research.jsonl`, then
projects them to the indexed `formation_research_events` SQLite table (schema 15).
The scheduled Stage72 publisher commits this journal with its normal metadata and
rebuilds from current main on a concurrent-push retry. Generated files are not part
of the implementation PR. The database is disposable; retain the journal in
operational backups. Do not run concurrent writers against the same local journal.

Each deterministic event retains fixture, league/season, kickoff, team identities,
formation matchup, coaches, expected/official source and capture time. Expected and
official observations are separate, including when both are already present.
`recorded_at_utc` records when this audit first retained the evidence; a historical
source capture must not be mistaken for a prospective audit observation. Collection
starts when this code runs; it does not claim to recover missed observations.
Corrupt JSON aborts collection instead of silently dropping evidence.

Only existing Stage72/55/56 data is read: zero additional API-Football requests.
Existing lineup no-lookahead cutoffs remain in force. Source updates observed after
kickoff do not get retroactively inserted as pre-kickoff lineup evidence.

Results are separate observations linked by fixture ID. Only explicit provider
`FT` with two non-negative integer scores contributes to result statistics.
Postponed, cancelled, live, missing, invalid, AET/PEN results remain UNKNOWN here.
Missing observations are never converted to a loss or a clean result. Newer source
result observations take precedence; older snapshots cannot overwrite them.
Leaving the rolling current round does not erase already retained history.

## Read-only access

`GET /v1/research/formations` returns `history` and a home-vs-away `matrix`.
Optional `team_id` and `fixture_id` filters select matching fixtures; both filters
may be combined. The match-card response also includes `formation_research` for
that fixture. Missing tables produce an explicit empty research response.

History chooses the latest observation for each team, with official always above
expected. A fixture contributes once to the matrix. Cells are separated by both
formation strings and both source statuses, so mixed/expected matches are not
silently pooled into official data. Raw expected and superseded observations remain
in the journal. Counts distinguish matches from settled FT results; win-rate
denominator is settled only, null when none. `small_sample` is true below ten FT
results. These are descriptive research statistics, not causal estimates or betting
recommendations.

No canonical probability, eligibility, stake, league scope, R/WATCH, promotion,
Value Radar, or settlement policy is modified or consumes this research output.

## Validation

Run `python -m unittest discover -s scripts/tests -p 'test_formation_research.py'`
and `node --test app/tests/*.test.mjs`. The Match Card E2E + Lineup Context PR
workflow runs these with lineup, match-card, standings and today-live regressions.
The Stage74 workflow runs the existing full application validation on Linux.
Check the pitch at 320, 390 and 1440 pixels with full, partial and absent XI data.
Merge evidence and production rollout evidence are separate; this document does
not assert that the VPS has deployed the feature.
