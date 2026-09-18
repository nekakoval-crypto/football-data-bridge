# Stage91 — StatsBomb Open Data player xG/xA research archive

Status: **RESEARCH ADAPTER — PROVIDER-FREE, NOT OPERATIONAL BETTING AUTHORITY**

Stage91 adds a safe player-level advanced-metric contour without pretending that
API-Football supplies metrics it does not expose in PBK's current player-stat
capture.

## Source

Source: **StatsBomb Open Data**

Repository: https://github.com/hudl/open-data

Use of the source remains subject to the StatsBomb Open Data User Agreement and
its attribution requirements. PBK therefore records the source and attribution
requirement on every derived row.

PBK does **not** vendor or redistribute raw StatsBomb event JSON.

## Metrics

### Player xG

Player xG is a direct source metric:

- event type: Shot;
- source field: `shot.statsbomb_xg`;
- `xg_total`: sum of all valid shot xG;
- `npxg`: sum excluding shots whose type is Penalty;
- `penalty_xg`: sum of penalty-shot xG.

A real xG value of `0` is valid. Missing, negative, NaN or infinite xG is
rejected rather than converted to zero.

### Player xA / xG Assisted

StatsBomb Open Data does not provide a ready-made xA column in the event rows.

Stage91 follows StatsBomb's documented xG Assisted method:

1. find a Shot with a valid `shot.statsbomb_xg`;
2. read that Shot's `shot.key_pass_id`;
3. join `shot.key_pass_id` to the creating Pass event's event `id`;
4. assign the created shot's xG to the passer;
5. sum those values as player `xa`.

Therefore:

- xG is `SOURCE_METRIC`;
- xA is `DERIVED_RESEARCH_METRIC`;
- the derivation method is stored explicitly on every row;
- cross-team joins are rejected;
- missing key-pass events remain unmatched evidence and are not guessed.

## Output

When materialized from a local StatsBomb Open Data checkout:

`ops/statsbomb_player_xg_xa.csv`

The dataset is one row per:

`StatsBomb match + StatsBomb player + StatsBomb team`

Key fields include:

- StatsBomb match/player/team IDs and names;
- competition / season / match date when local match metadata is supplied;
- shots, non-penalty shots and penalty shots;
- xG, non-penalty xG and penalty xG;
- assisted shots and derived xA;
- exact SHA-256 of the local source event JSON;
- optional source checkout revision;
- attribution, research-only and no-authority flags.

No raw StatsBomb event payload is copied into the PBK repository.

## Identity boundary

Stage91 intentionally remains in the StatsBomb namespace.

It does **not** infer that a StatsBomb player ID equals an API-Football/PBK player
ID. A separate conservative entity-mapping stage is required before these
metrics can appear in a PBK player passport.

Until then the correct readiness gap is:

`PLAYER_XG_XA_PBK_IDENTITY_MAPPING_NOT_IMPLEMENTED`

when research rows exist.

## Readiness states

Stage80 reports one of:

- `RESEARCH_ADAPTER_READY_NOT_MATERIALIZED` — code/contract exists, no derived
  StatsBomb player xG/xA dataset has been materialized;
- `RESEARCH_SOURCE_EMPTY_OR_INVALID` — a file exists but cannot prove the
  Stage91 source/provenance contract;
- `RESEARCH_ONLY_MATERIALIZED_NOT_OPERATIONAL` — valid derived research rows
  exist, but no PBK identity mapping or betting authority is granted.

Materializing research data does **not** make it canonical probability evidence.

## Local materialization contract

Stage91 accepts only local files. It performs no download:

```
python scripts/stage91_statsbomb_player_xg_xa.py \
  --events-dir <statsbomb-open-data>/data/events \
  --matches-root <statsbomb-open-data>/data/matches \
  --source-revision <local-checkout-revision> \
  --out ops/statsbomb_player_xg_xa.csv \
  --meta-out ops/stage91_statsbomb_player_xg_xa_last_run.json
```

The raw StatsBomb checkout stays outside this repository.

## Governance

Stage91:

- makes zero API/provider calls;
- does not create probabilities or value;
- does not create R1/R2/R3 signals;
- does not change eligibility;
- does not change stake;
- does not change settlement;
- does not mutate the immutable Forward Journal;
- does not create current-squad authority;
- does not silently map StatsBomb IDs to API-Football/PBK IDs;
- preserves mandatory source attribution metadata.
