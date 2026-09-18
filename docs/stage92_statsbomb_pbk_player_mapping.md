# Stage92 — StatsBomb ↔ PBK player identity mapping

Status: **CONSERVATIVE RESEARCH IDENTITY BRIDGE — NO BETTING AUTHORITY**

Stage92 connects Stage91 StatsBomb player xG/xA research rows to PBK player IDs
without assuming that identifiers from different providers are interchangeable.

## Why a separate bridge is required

StatsBomb player IDs and API-Football/PBK player IDs are different namespaces.

PBK's historical player catalog also often contains abbreviated API-Football
names such as `M. Akanji` or `A. Hakimi`, while StatsBomb commonly exposes
full names. An abbreviated-name match is not strong enough evidence to attach
advanced metrics automatically.

Stage80 already has a stronger identity bridge for a subset of players:
verified historical transfer rows preserve:

- PBK player ID;
- PBK observed name;
- Transfermarkt player ID;
- full Transfermarkt player name;
- `EXACT_NAME_CURRENT_CLUB`;
- `HIGH` mapping confidence.

Stage92 reuses only that already-verified bridge.

## AUTO_MATCH / HIGH rule

A StatsBomb player is authoritative for mapped PBK research only when:

1. Stage91 has one stable name for that StatsBomb player ID;
2. the normalized StatsBomb full name exactly matches a Transfermarkt full name;
3. the Transfermarkt row comes from the verified Stage80
   `EXACT_NAME_CURRENT_CLUB/HIGH` mapping;
4. all exact-name bridge rows resolve to one PBK player ID.

The result is:

- `match_status = AUTO_MATCH`;
- `match_method = EXACT_FULL_NAME_VIA_VERIFIED_TRANSFER`;
- `match_confidence = HIGH`;
- `authoritative_for_player_xg_xa = true`.

No fuzzy matching, accent stripping or approximate edit-distance matching is
used for authority.

## REVIEW rules

API-Football abbreviated names may still be useful for review.

Stage92 can compare a StatsBomb full name to PBK historical names by:

`first initial + surname`

For example, a full name could generate a candidate against an observed PBK name
such as `A. Hakimi`.

This produces only:

- `REVIEW/MEDIUM` when exactly one PBK review candidate exists;
- `REVIEW/LOW` when multiple PBK candidates exist.

A REVIEW row never enters mapped PBK xG/xA research.

StatsBomb player-ID name drift also forces `REVIEW/LOW`, even if one of the
observed names would otherwise match exactly.

## Outputs

### Full mapping audit

`ops/statsbomb_pbk_player_mapping_candidates.csv`

Contains every observed StatsBomb player as:

- AUTO_MATCH;
- REVIEW;
- UNMATCHED.

It preserves the matching method, confidence, PBK/Transfermarkt candidates and
whether the row is authoritative for player xG/xA.

### PBK-mapped research metrics

`ops/pbk_player_xg_xa_research.csv`

Contains **only AUTO_MATCH/HIGH** Stage91 rows.

Each mapped row preserves:

- PBK player ID/name;
- StatsBomb player/match/team identity;
- xG, npxG, penalty xG and derived xA;
- Stage92 mapping method/confidence;
- Stage91 source event SHA-256 and source revision;
- StatsBomb attribution requirement;
- explicit research-only / no-operational-authority flags.

REVIEW and UNMATCHED players are physically excluded from this dataset.

## Automation

When `ops/statsbomb_player_xg_xa.csv` exists with Stage91 research rows, the
Stage92 workflow builds and safely publishes:

- `ops/statsbomb_pbk_player_mapping_candidates.csv`;
- `ops/pbk_player_xg_xa_research.csv`;
- `ops/stage92_statsbomb_pbk_player_mapping_last_run.json`.

If Stage91 has not been materialized, Stage92 exits cleanly without fabricating
empty operational evidence.

Publishing mapped research automatically triggers:

- Stage80 readiness;
- Stage72 unified SQLite rebuild;
- Stage73 archive API refresh.

## Archive API

Stage73 exposes mapped rows through:

`GET /v1/archive/player?player_id=<PBK_PLAYER_ID>`

under:

`research_xg_xa`

Coverage explicitly states:

- whether research xG/xA exists;
- row count;
- `research_xg_xa_operational_authority = false`.

These rows are historical research enrichment only.

## Readiness states

Stage80 V10 distinguishes:

- Stage91 not materialized;
- Stage91 materialized but Stage92 not materialized;
- Stage92 materialized with no AUTO/HIGH mapping;
- Stage92 AUTO/HIGH PBK research mapping materialized.

A REVIEW-only mapping can never close the high-confidence identity gap.

## Governance

Stage92:

- makes zero provider/API calls;
- creates no probability or value;
- creates no signal;
- changes no R1/R2/R3 rule;
- changes no eligibility;
- changes no stake;
- changes no settlement;
- does not mutate Forward Journal;
- does not grant operational betting authority to StatsBomb research;
- preserves StatsBomb attribution metadata;
- never silently equates StatsBomb, Transfermarkt and API-Football identifiers.
