# Stage80 — PBK ↔ Transfermarkt player entity mapping

Status: **CONSERVATIVE ENRICHMENT MAPPING FOUNDATION**

PBK and Transfermarkt use different player-ID namespaces. This slice introduces an auditable mapping layer instead of silently treating IDs as interchangeable.

## Inputs

- PBK `ops/historical_players.csv`
- Transfermarkt `players.csv.gz`
- Transfermarkt `transfers.csv.gz`

## Mapping policy

Automatic mapping is deliberately narrow.

### AUTO_MATCH

Allowed only when all of the following are true:

1. normalized full player name matches exactly;
2. PBK latest observed roster team matches Transfermarkt current club after conservative club-name normalization;
3. exactly one Transfermarkt candidate satisfies the pair.

Method: `EXACT_NAME_CURRENT_CLUB`

Confidence: `HIGH`

### REVIEW only

These are never auto-promoted:

- exact unique full-name match without current-club confirmation;
- initial + surname + current-club match;
- ambiguous exact-name matches.

No edit distance, fuzzy text score, nationality inference, date-of-birth inference or manual-looking guess is used for automatic mapping.

## Outputs

The Transfermarkt fetch workflow publishes a separate 30-day artifact:

`transfermarkt-pbk-mapping`

containing:

- `pbk_transfermarkt_player_mapping_candidates.csv`
- `pbk_transfer_history_exact_mapped.csv`
- `stage80_transfer_mapping_meta.json`

The normalized transfer-history file contains only rows belonging to `AUTO_MATCH` players.

## Governance

- Transfermarkt remains historical enrichment only;
- API-Football remains operational current-data authority;
- mapping artifacts do not mutate canonical PBK player IDs;
- REVIEW candidates have no downstream authority;
- no transfer row changes probability, EV/value, R eligibility, stake, settlement or Forward;
- the upstream Transfermarkt snapshot age remains a provenance limitation.
