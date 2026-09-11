# Stage71 observation completeness and settlement

The locked universe remains 16 leagues. Stage71 writes research R1/R2 observations
for the 15 non-Serie-A leagues; Serie A remains owned by canonical forward.
Health reports canonical captured counts read-only and does **not** certify the
canonical writer's completeness. No changes to eligibility thresholds, 1u,
60/120 gates, WATCH, promotion policy, or the PWA.

## Findings in the previous capture

* `next=5` silently truncated busy rounds; no independent expected fixture count.
* 07:17 and 13:17 UTC had an 18-hour overnight gap against a 12-hour R2 window.
* Run-start timestamps could label an odds response obtained after kickoff as
  pre-match. The fixture's status and known scores were not checked.
* FT-only season queries could not explain postponed/cancelled rows; old-season
  pending IDs could remain invisible indefinitely.
* Dictionary/set lookups masked pre-existing duplicate ledger keys.
* Missing credentials, incomplete API responses and swallowed execution errors
  could look like successful empty scans or unpriced observations.

## Reconciliation

One complete `/fixtures?league=…&season=…` inventory per research league replaces
both next and FT requests. The first five upcoming fixtures are still considered;
all additional NS fixtures within 24 hours are included. Candidates are processed
in kickoff order. FT history and settlement reuse the inventory, without an
additional result request. Up to 20 missing pending IDs use one batch lookup per
run, oldest-attempt first, including previous seasons. Every pending row is retried
on every available league inventory, not just newly captured rows.

Capture requires NS, unknown scores, a future kickoff, finite decimal odds >1,
and no future provider update. Actual response-time timestamps are checked again
before trigger and execution writes. Stored triggers require pre-kickoff provenance;
missing legacy fixture-status evidence is explicitly legacy, not reconstructed.
R2 uses only official FT history before the evaluation time and the unchanged
12-hour window. Unknown historical R2 eligibility is never backfilled.

Trigger and family/league/fixture keys are unique. Existing duplicates stop the
writer and are reported for manual evidence review. Atomic file replacement and
an exclusive local lock prevent partial CSV replacement/concurrent local writers.
The opener is persisted before the execution lookup; failed lookups retry later
without changing the opener. An unavailable bookmaker in a valid complete response
still produces an unpriced research observation, preserving the existing coverage
semantics. Workflow runs are serialized; PR/feature CI has no API secret or writer.
Git publication rebases unrelated upstream changes and fails on conflicting edits;
the artifact preserves the attempted snapshot, never force-pushes a lost update.

Only official `FT` with valid scores settles once. PST, CANC, SUSP, ABD, AWD,
AET/PEN and missing results never become an inferred loss. Rescheduling is tracked
separately without overwriting frozen kickoff or eligibility. Already captured
rows wait for official FT; a changed trigger schedule blocks new observations
pending research review. A moved kickoff earlier than capture cannot settle as
clean forward. Cancellation remains unresolved research pending (flagged in health),
not an invented bookmaker void/refund policy and not a settled gate observation.

## Health and budget

`stage71_observation_audit.py` reads local files only and writes
`ops/stage71_observation_health.json`. Capture maintains
`ops/stage71_observation_state.json` with observed schedules, evaluation times,
rescheduling and retry state. Counts cover expected/scanned fixtures, captured
research rows, missed-or-at-risk fixtures, pending/stale rows (>48h after current
kickoff), rescheduled/cancelled fixtures, settled rows and duplicate keys. These
have intentionally different units, documented in the JSON. A missing inventory
is UNKNOWN, not a certified zero; `legacy_next5_omitted` quantifies truncation risk.

Schedule: 07:17, 15:17, 23:17 UTC (8h gaps, 4h slack for the R2 window). Delayed or
skipped Actions runs still cannot be guaranteed. Default capture ceilings are 60
attempts/run and 180/UTC day, including errors, with durable pre-request accounting.
Base fixture cost is 45/day across three runs; missing-ID retries add at most three
calls/day. Odds consume the remainder. This is a Stage71 cap, **not** knowledge of
the account-wide quota used by other workflows. Catalog resolution retains its
existing separate cached behavior. A hard-killed worker may leave a local lock;
remove that lock only after verifying no writer exists. A fresh Actions checkout
does not inherit the lock. Failed unpublished workflow snapshots require artifact
recovery; exactly-once remote durability is conditional on successful publication.

Provider-visible schedule coverage is not proof that every qualifying observation
existed in available odds. Late odds, provider omissions, quota exhaustion, outages,
reschedule review and missed runs remain explicit risks. Historical inventory is
not relabeled as a prospective expectation. Guaranteed eventual settlement is
conditional on the provider eventually publishing official FT and successful runs;
cancelled fixtures may never have FT. No production/VPS deployment is claimed.

API response semantics: [official fixture guide](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide).

## Verification

Run `python -m unittest discover -s scripts/tests -p 'test_stage71*.py' -v`.
Tests use deterministic fake API responses and temporary ledgers, with no live API
calls. The workflow additionally rebuilds Stage72 and checks Stage73/74 API contracts.
