# Stage80 — Transfermarkt transfer-source foundation

Status: **HISTORICAL ENRICHMENT SOURCE — NOT CURRENT OPERATIONAL AUTHORITY**

PBK already has a fetch workflow for the public `dcaribou/transfermarkt-datasets` snapshot. This slice extends that source package with the `transfers` table and validates its schema before artifacts are published.

## Source facts

The upstream dataset currently documents a snapshot through **2026-07-06** and states that it is not currently being refreshed. PBK therefore treats it as historical enrichment only, never as authoritative current-transfer status.

The transfer table exposes:
- player id/name;
- transfer date and season;
- from/to club id and name;
- transfer fee;
- player market value at transfer time.

## PBK usage contract

- `transfers.csv.gz` is downloaded together with the existing core Transfermarkt tables;
- `dataset-metadata.json` is retained alongside the artifact for provenance;
- `stage80_transfer_source_audit.py` verifies the expected transfer schema;
- source artifacts are retained for 30 days instead of 7;
- no API-Football data is replaced by this source;
- no automatic player-ID join is assumed because Transfermarkt IDs and API-Football IDs are different namespaces;
- no current squad, injury, eligibility, probability, EV/value, stake or Forward authority is created.

## Next slice

A later normalized transfer-history layer must introduce explicit entity mapping/provenance before Transfermarkt transfer rows are joined to PBK players or teams. Until then, the source remains an auditable historical enrichment artifact rather than a canonical PBK warehouse table.
