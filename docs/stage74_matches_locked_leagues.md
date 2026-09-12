# Matches: locked 16-league market/research view

## Diagnosis

`app.js` renders `/v1/attention.market_cards` directly. Stage74 delegates that endpoint
to Stage73, which reads the `attention_board.json` state document imported unchanged
by Stage72. Neither API nor SQLite has a Big5 filter.

The old Stage66 appender selected canonical/WATCH/nearest board rows, not the market
capture universe. Nearest was limited to three openers from each of Stage61 (England),
Stage62 (Germany), Stage63 (Big5). The appender then capped the union at eight fixtures,
selected only TT 1.5 and EH home +1, and dropped fixtures without those Marathonbet rows.
The frontend derived league options from this already reduced set.

Stage71C/E/F/G already cover the locked 16 leagues. Stage71J already fetches the next
10 fixtures per league and shares one unfiltered odds response per fixture, within
the existing 190-call cap. No additional provider requests or schedule changes are needed.

## Projection

Stage66 now unions the existing Stage61/62/63 and Stage71 core snapshots plus the
Stage71 research 1X2 trigger ledger. It uses league IDs resolved through the locked
catalog and includes upcoming fixtures within 14 days, with no global top-eight cap.
Stage71J persists `market_research_fixtures.json` from its existing in-memory fixture
cache, independently of odds availability. The first scheduled shared capture creates
that file; existing snapshot identities supply a migration fallback immediately.
This is the observed capture universe, not a claim of a complete season schedule.

Newer Stage71 observation status/kickoff overrides obsolete identities. Started,
finished, cancelled and postponed fixtures are excluded. Prices from a different
kickoff or a post-kickoff/future capture are not attached. All collected TT/EH lines
remain available. Latest rows are chosen per fixture/family/line; a missing price does
not fall back to an older snapshot. Bet365 reference and user-bookmaker prices remain
separately labelled. The 1X2 research trigger is a frozen snapshot, not a fresh quote.

Missing market families are explicit `NO_DATA` rows. A fixture with no prices remains
`MARKET_VIEW_ONLY`, `creates_signal: false`; league choices come from all fixture cards.
The market filter selects rows within cards, retaining missing-data fixtures and the
league options. Detail view displays the same market projection and timestamps.

The `/v1/attention` envelope and Stage72 schema remain compatible. Market rows add
`bookmaker`, `captured_at_utc`, `api_update_utc`, `source`, `status` when available;
family keys are MATCH_WINNER, TOTAL, BTTS, TEAM_TOTAL, DOUBLE_CHANCE, DNB,
EUROPEAN_HANDICAP. Consumers must accept explicit NO_DATA rows.

No canonical/WATCH capture, eligibility, stakes, gates or promotion policy changes.
Existing health/staleness/offline warnings and no-store API requests remain intact;
each displayed price is labelled as a collected snapshot. Shell cache is v9.

## Validation and recovery

30 Python tests, including six offline projection/cache/Stage72-to-Stage74 contract
tests; 12 frontend tests. Local Edge browser smoke checks all 16 league options,
missing DNB filtering, reset, and long-name overflow at 320, 390 and 1440px.
An offline projection of the source checkout found 160 fixtures across all 16 leagues.
Counts are a test observation, not production coverage or a betting signal.

Stage66 builds the board; Stage72 rebuilds SQLite; Stage73/74 serve it. Only main may
commit generated Stage66 outputs. GitHub CI is required before merge. VPS deployment
and live endpoint coverage require a separate check and are not established by merge.
