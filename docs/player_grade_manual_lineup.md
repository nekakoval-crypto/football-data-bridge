# PBK Player Grade & Manual Lineup Scenario

## Sources

### API-Football `/fixtures/players`
Production v0.1 source for per-match aggregate player statistics already aligned with PBK's provider stack. The adapter expects minutes, position, shots, goals, assists, passes, tackles/interceptions, duels, dribbles, fouls, cards and penalties. Provider 0-10 rating is stored only as a reference field and is not reused as PBK Overall Grade.

### StatsBomb Open Data
Provider-free research source for event-level action grading. The public dataset includes competitions, matches, lineups, events and selected 360 freeze-frame data. PBK uses it only for research/prototyping and keeps explicit source attribution/provenance. The event prototype grades individual actions on a -2..+2 half-step scale.

## `PBK_PLAYER_GRADE_V1`

The first PBK implementation is deliberately split into two tiers:

1. **Aggregate grade** — available from API-Football per-match statistics. It produces Attack, Progression (proxy), Creation, Possession, Defending, Discipline and an unavailable Pressing component when true pressure events are absent. Missing components reduce confidence instead of becoming zero.
2. **Event research grade** — StatsBomb-style events are explicitly mapped to action scores on the -2..+2 scale. This is a transparent research prototype and does not claim to reproduce any proprietary StatsBomb/Hudl grade.

Position-group weights differ for G/D/M/F. Rolling Form 5/10 uses only observations strictly before the requested cutoff. XI Quality is an average of available PBK player grades and always reports coverage/missing player IDs.

## Manual Lineup Scenario

A manual lineup scenario is a private/user supplied WHAT-IF layer for cases where the user has lineup information not yet available from public resources.

Flow:

1. Select a fixture.
2. Start from the best available baseline (Official XI first, then Expected XI).
3. Set formation and 11 starters for each team.
4. Optionally add an insider/source note.
5. Compare Manual XI vs baseline: changed players, formation change, XI Quality delta, line-by-line quality delta and optional Player Importance delta.
6. Save the scenario as append-only research evidence and rerun later.

Draft mode can hold fewer than 11 players, but a READY scenario requires exactly 11 unique starters per team and a formation.

## Safety contract

Both modules are research/context only:

- no provider data overwrite;
- no direct provider polling;
- no canonical probability mutation;
- no R1/R2/R3 eligibility mutation;
- no stake mutation;
- no Forward journal mutation;
- no settlement mutation;
- no motivation/context overwrite.

A future probabilistic WHAT-IF model, if introduced, must remain a separate sandbox output until independently forward-validated and explicitly promoted.