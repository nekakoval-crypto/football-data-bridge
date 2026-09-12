# Stage71 card observations

The Leagues cards explain their captured/executable/settled aggregates through
an accessible native `Наблюдения` disclosure. Opening a card loads five rows;
`Показать все` reads further pages and `Свернуть до 5` restores the compact view.
Rows use descending kickoff time (UTC), with descending observation ID as a
deterministic tie-breaker. Filters/refresh/offline invalidate pending responses.
The UI distinguishes an empty ledger from an unavailable source or request error.

## Read-only contract

`GET /v1/challengers/observations?family=R1&league=Premier%20League`
(PWA prefix: `/api`). Both parameters must identify an existing board card;
otherwise the endpoint returns HTTP 404 `UNKNOWN_CHALLENGER_CARD`.

Pagination: `limit` defaults to 5, bounded to 1–500; `offset` defaults to 0.
Response: `items`, `count` (full filtered total), `limit`, `offset`, `source`,
`available`, `read_only: true`. An absent source table returns `available: false`.
Items contain `id`, `home_team`, `away_team`, `kickoff_utc`, `selection`,
`bet365_price`, `marathonbet_price`, `status`, `final_home_goals`,
`final_away_goals`, `result`, and `user_profit_u`.

Source selection matches `stage71_progress_overlay.group_rows`: ACTIVE,
DEGRADATION_REVIEW and SUSPENSION_REVIEW use `canonical_signals` by rule/league
(legacy missing canonical league means Serie A). Other cards use
`challenger_signals` by family/league and are explicitly research-only.
The existing board and its counters are not rewritten by this endpoint.

Bet365 uses the frozen selected-side price, never another outcome's price.
Only an explicitly recorded Marathonbet execution is labelled Marathonbet.
Canonical PAPER is presented as PENDING; other source statuses are preserved.
Settlement fields display only on SETTLED observations. Missing score/price/P&L
stays `—`; in particular the current canonical view does not carry final goals.
No outcome or profit is inferred from a score. Zero goals and zero profit remain
visible. All external text is escaped.

Only existing Stage72 SQLite tables are read. There are no provider requests,
ledger writes, eligibility changes, gates changes, stake changes, WATCH changes,
scope changes to the 16 locked leagues, or automatic promotion.

## Validation and release

Run `node --test app/tests/challengers.test.mjs` and
`python -m unittest discover -s scripts/tests`.
Stage74 CI runs frontend and observation contract tests plus the existing
Stage72/73/74/75 checks. Shell cache is `pbk-shell-v8`.
Browser smoke covers 320/375/768/1440px, long team names, five/all/collapse,
and document horizontal overflow. Merge and green CI do not prove deployment;
production needs a separate release/API/PWA check.
