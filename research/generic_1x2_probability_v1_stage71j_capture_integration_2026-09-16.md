# PBK Generic 1X2 Probability v1 — Stage71J prospective capture integration

Date: 2026-09-16  
Authority: RESEARCH  
Forward protocol: unchanged

## Purpose

This change connects Generic 1X2 v1 to the existing Stage71J prospective market-capture cycle without adding another provider polling path.

Stage71J already fetches the locked 16-league upcoming fixture universe and one unfiltered API-Football `/odds` response per fixture. Generic 1X2 reuses those same in-memory responses.

## Source contract

- Provider: API-Football
- Bookmaker: Bet365
- Market: `Match Winner`
- API-Football bet id: `1`
- Required outcomes: complete Home / Draw / Away vector
- Bookmaker substitution: forbidden
- Avg-odds fallback: forbidden
- Historical backfill: forbidden
- Additional provider calls for Generic 1X2: `0`

The canonical league name is inherited from the locked Stage71J league-id query, not inferred from free-form provider text.

## Timestamp contract

The source observation timestamp is the explicit API-Football `/odds` response `update` timestamp attached to the provider odds record.

The monitor processing timestamp is generated when the Stage71J adapter processes the already-fetched cache.

The existing forward monitor remains authoritative and rejects a row when either source observation time or processing time is not strictly before kickoff.

A missing provider update timestamp is not reconstructed and the row is not captured.

## Append-only rule

The adapter feeds candidate rows into the already-frozen Generic 1X2 forward monitor. The first valid complete Bet365 prematch observation for a fixture is immutable; later Stage71J cycles cannot overwrite it.

## League validation

All 16 locked leagues are eligible for prospective capture. Forward evaluation remains independent by league under the protocol merged in PR #64.

The historical pooled Big-5 PASS remains pooled historical evidence only and is not converted into a league-specific PASS by this integration.

## Scope boundary

This integration performs prematch capture only.

It does not:

- settle match outcomes;
- change frozen model alphas;
- change per-league forward thresholds;
- authorize EV/value, stakes, R1/R2/R3 changes, production probability, or UI;
- rerun or read the historical TEST dataset;
- add a second API-Football polling schedule.

Settlement remains a separate follow-up step after prospective prematch capture is operating correctly.
