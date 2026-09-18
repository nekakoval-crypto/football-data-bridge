# Stage80 — match event archive

Status: **LOW-PRIORITY DURABLE PROVIDER ARCHIVE**

PBK captures finished-fixture event timelines from API-Football `/fixtures/events` through the shared broker and shared Stage71 budget.

## Durable queue

`stage80_match_event_backlog.csv` is produced from already-observed terminal fixtures in `current_round_fixtures.csv`.

A fixture stays `PENDING` until at least one usable normalized event row is persisted. Empty provider responses stay retryable; PBK does not convert an empty response into invented "no events" evidence.

## Event ledger

`match_event_snapshots.csv` is append-only, first-observation-wins historical evidence.

Because API-Football event rows do not expose a stable event ID, PBK creates a deterministic SHA-256 identity from:

- fixture id;
- elapsed/extra minute;
- team;
- player;
- assist;
- type/detail/comments;
- occurrence number among exact duplicate signatures in the provider response.

The deterministic identity makes repeated provider reads idempotent while preserving legitimate exact duplicate event rows.

Stored evidence includes:
- fixture/league/season/round/kickoff;
- first observed timestamp;
- elapsed + stoppage time;
- team/player/assist IDs and names;
- provider event type, detail and comments;
- explicit source and archive version.

## Budget and cadence

The workflow runs every two hours and may use at most 8 event calls per run. It shares the Stage71 observation-state budget and reserves capacity for LIVE/current-round/standings/Stage77/Stage81 before event capture.

## Governance

- source: API-Football via the shared broker only;
- terminal fixtures only;
- no direct HTTP access from the stage;
- no probability/EV/value/eligibility/stake/settlement/Forward mutation;
- empty/missing data remains unknown/retryable;
- raw provider payload archival remains separately gated by durable storage configuration.
