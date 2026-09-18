# Stage80 — PBK ↔ Transfermarkt player entity mapping

Status: **CONSERVATIVE ENRICHMENT MAPPING FOUNDATION**

PBK and Transfermarkt use different player-ID namespaces. This slice introduces an auditable mapping layer instead of silently treating IDs as interchangeable.

## Inputs

- PBK `ops/historical_players.csv`
- PBK `ops/player_stats_snapshots.csv` full-name/team evidence
- PBK `ops/player_profile_evidence.csv` full-name/date-of-birth/team evidence
- Transfermarkt `players.csv.gz`
- Transfermarkt `transfers.csv.gz`

## Mapping policy

Automatic mapping is deliberately narrow.

### AUTO_MATCH

Three conservative HIGH-confidence methods are allowed.

#### Catalog name + current club

1. normalized PBK catalog name matches exactly;
2. PBK latest observed roster team matches Transfermarkt current club after conservative club-name normalization;
3. exactly one Transfermarkt candidate satisfies the pair.

Method: `EXACT_NAME_CURRENT_CLUB`

#### Player-profile full name + date of birth + current club

When the PBK catalog name is abbreviated, Stage80 first prefers the richer
API-Football `player_profile_evidence.csv` identity evidence.

AUTO_MATCH is allowed only when:

1. API-Football provides a non-abbreviated full name from `firstname + lastname`;
2. that full name exactly matches Transfermarkt after the existing conservative normalization;
3. API-Football birth date exactly equals Transfermarkt `date_of_birth`;
4. API-Football profile team matches Transfermarkt current club;
5. the full-name+club+DOB evidence belongs to exactly one PBK player ID;
6. exactly one Transfermarkt player satisfies all three facts.

Method: `EXACT_PROFILE_NAME_DOB_CURRENT_CLUB`

Profile matching normalizes provider formatting without using similarity:

- a DOB such as `1995-07-19 00:00:00` is compared as the explicit ISO date
  `1995-07-19`;
- `firstname + lastname` is tried exactly after normalization;
- when API-Football firstname contains middle names, the deterministic
  `first firstname token + lastname` variant may also be tried;
- common legal club tokens such as `FC`, `AFC`, `CFC`, `US`, `AJ`,
  a leading German-style `1.`, and a trailing four-digit founding year are
  removed only for this DOB-backed club confirmation.

All accepted candidates still require exact DOB, unique PBK ownership and one
unique Transfermarkt candidate. No edit-distance or fuzzy score is used.

#### Match-stat full name + same club

When the PBK catalog name is abbreviated, Stage80 may use API-Football
`player_stats_snapshots.csv` as additional identity evidence only when:

1. the API-Football match-stat name is non-abbreviated;
2. the full name exactly matches Transfermarkt;
3. the match-stat team matches Transfermarkt current club;
4. that full-name+club evidence belongs to exactly one PBK player ID;
5. exactly one Transfermarkt candidate satisfies the same full-name+club pair.

Method: `EXACT_STATS_NAME_CURRENT_CLUB`

All three methods use confidence `HIGH`.

If two PBK identities claim the same Transfermarkt player under an automatic method,
the collision is demoted to REVIEW/LOW instead of silently overwriting one mapping.

### REVIEW only

These are never auto-promoted:

- exact unique full-name match without current-club confirmation;
- initial + surname + current-club match;
- ambiguous exact-name matches.

No edit distance, fuzzy text score, nationality inference, inferred date of birth, or manual-looking guess is used for automatic mapping. The profile method requires an explicit exact DOB from both sources.

## Outputs

The Transfermarkt fetch workflow publishes a separate 30-day artifact:

`transfermarkt-pbk-mapping`

containing:

- `pbk_transfermarkt_player_mapping_candidates.csv`
- `pbk_transfermarkt_player_identity.csv`
- `pbk_transfer_history_exact_mapped.csv`
- `stage80_transfer_mapping_meta.json`

The workflow also publishes the durable identity projection to:

`ops/pbk_transfermarkt_player_identity.csv`

This file contains every AUTO_MATCH/HIGH PBK↔Transfermarkt identity even when the
player has no row in Transfermarkt's transfer-event table. Transfer history and
identity are therefore separate concerns.

The normalized transfer-history file contains only rows belonging to
`AUTO_MATCH` players that also have transfer-event evidence.

## Governance

- Transfermarkt remains historical enrichment only;
- API-Football remains operational current-data authority;
- mapping artifacts do not mutate canonical PBK player IDs;
- REVIEW candidates have no downstream authority;
- no transfer row changes probability, EV/value, R eligibility, stake, settlement or Forward;
- the upstream Transfermarkt snapshot age remains a provenance limitation.
