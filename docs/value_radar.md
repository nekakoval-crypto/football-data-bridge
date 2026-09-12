# Value Radar v1

Research attention layer over Stage75 frozen predictions. The module reads existing
files only and never calls providers, creates signals, changes eligibility, stakes,
R1/R2/R3, WATCH or probability calibration. Only active canonical PAPER/OPEN/REVIEW
rows with validated frozen prematch provenance qualify. Result-known and post-kickoff
observations cannot create crossings. R2 wins nested R1/R2 projection conflicts.

Decimal comparisons use the unrounded probabilities and frozen prospective Marathonbet
paper execution odds. STRONG_VALUE requires EV >=5% and edge >=3pp; WATCH_VALUE >=2%
and >=2pp; MARKET_DISAGREEMENT requires edge >=5pp and no executable price.
HIGH_PROB_LOW_VALUE requires p >=65% and numeric EV <2%. LONGSHOT_STRONG accompanies
STRONG_VALUE only at odds >=2. Other bookmakers never supply executable EV.

`ops/stage75_value_radar.jsonl` is append-only. Each id is the first 24 hex characters
of SHA256(model_version|api_fixture_id|selection|radar_kind). Existing bytes and order
are preserved; duplicate/corrupt ledgers fail closed. An exclusive local lock and
serialized Stage75 workflow prevent competing writers. Interrupted runs may leave
a lock: verify no writer remains before removing it; never repair the ledger silently.
The atomic current projection is published after the ledger, so reruns recover without
duplicating crossings. No historical crossing time is inferred from prediction time.

Stage75 publishes `value_radar_current.json` and Radar counters in its last-run metadata.
On initial rollout, Stage75 creates artifacts on main; Stage72 accepts a missing ledger
as an empty stable table. Stage72 schema 8 projects JSONL into `value_radar_events`, with
source hash/count and indexes. The source ledger remains authoritative.

Stage74 exposes read-only `/v1/value-radar?limit=50` (clamped 1..100) and additive
`value_radar` in `/v1/match`. Missing optional data is NO_DATA with empty items.
The Today block loads the local endpoint only, clears stale cards on failure, and uses
the existing match dialog. Service-worker shell v10 includes both Radar assets.

Validation commands:

```
python -m unittest discover -s scripts/tests
node --test app/tests/*.test.mjs
python scripts/stage72_build_data_layer.py
python scripts/stage73_internal_api.py --self-test
python scripts/stage74_app_api.py --self-test
```

The integration test disables sockets and proves Stage75 frozen prediction, settlement,
trigger and forward input bytes are unchanged. Projection tests fix the build timestamp
to demonstrate repeatable SQLite bytes. Boundary and near-miss tests include wrong
bookmakers, nonfinite fields, prematch timing, WATCH exclusion, nested dedupe, immutable
first events, transitions, new model ids and repeat runs. Synthetic transitions are
test fixtures, not permission to edit frozen production source prices.

Local browser smoke on 2026-09-12: 320/390/1440, three real-source Radar cards,
no horizontal overflow or console errors; match button opens Sassuolo–Juventus.
Windows preview substitutes Linux load-average telemetry only in its external local
harness; Linux CI is authoritative for the unchanged runtime self-test.

Completion still requires green PR CI, merge, actual production release/health/Radar
readback and PBK master/checklist update. A design pack or this document is not completion.
