# Stage71G — Ф1(0) / Ф2(0) prospective market capture preregistration

Locked before the first Stage71G live capture.

## Purpose
Stage71D tested a specific historical Bet365 AH=0 steam hypothesis and produced no promotable candidate because the preregistered movement samples were too small. Stage71G does not alter that result and does not create a new betting rule. Its only purpose is to build a current prospective raw market history for Ф1(0)/Ф2(0) across the locked 16 leagues.

## Market identity
- Full-time Asian Handicap market only.
- API-Football generic `Asian Handicap` market; expected catalog id 4, but live capture must verify market identity.
- Retain only exact handicap line `0` for both sides.
- User-facing selections: Ф1(0), Ф2(0).
- Never substitute Asian lines ±0.25/±0.5 or European Handicap.

## Scope
All 16 locked PBK national leagues, season 2026.

## Data sources
- Bet365: market-reference opener/current/observed-close pair at exact line 0.
- Marathonbet: executable/reference user-book price at exact line 0 when available.
- API-Football pre-match odds feed.

## Capture policy
1. Freeze the first observed complete Bet365 line-0 pair as opener.
2. Store append-only snapshots inside the tracking horizon.
3. Freeze the latest stored pre-kickoff snapshot as observed close.
4. Store Marathonbet Ф1(0)/Ф2(0) alongside Bet365 where available.
5. Normalize the two-way market to no-vig probabilities for descriptive movement only.
6. `signals_created` must always equal 0.

## Research firewall
- Stage71G is `PROSPECTIVE_CAPTURE_ONLY`.
- No +2/+3/+4 pp threshold is a signal in Stage71G.
- The old Stage71D sample cannot be reused as a future holdout.
- A future DNB hypothesis requires a separately frozen discovery sample, a new preregistration and an independent future holdout.
- No automatic strategy promotion.
