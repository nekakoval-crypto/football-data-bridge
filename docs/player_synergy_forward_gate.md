# PBK Item 11 — Final data/research foundation and prospective gate

This stage closes the engineering foundation without pretending that synergy is
already a betting model.

## Prospective prematch bridge

The stage reads official `lineup_snapshots.csv` observations only when
`captured_at_utc <= kickoff_utc`.  The latest valid observation per
fixture/team becomes a genuine `PREMATCH_FROZEN` XI record.

That XI is projected onto the existing retrospective PAIR / TRIO / LINE
association tables.  Historical association authority stays research-only; the
new fact being established prospectively is **which XI was actually known
before kickoff**.

This creates the forward validation rail we were missing.

## Fail-closed promotion gate

Current evidence is not force-promoted:

- PAIR: not promoted; train/holdout sign was unstable.
- TRIO: not promoted; train/holdout sign was unstable.
- LINE: research candidate only; sign stability alone is insufficient.
- ANTI_SYNERGY: research candidate only; descriptive association is not causal.
- SUBSTITUTION: postmatch research only.

No combined synergy mega-score is permitted.

## Closure semantics

When this stage reports
`checklist_item_11_data_engineering_foundation = COMPLETE`, checklist item 11
may be closed as a DATA/RESEARCH foundation.

Predictive authority remains `NOT_AUTHORIZED` until enough prospective
prematch observations accumulate and a dedicated synergy specialist model
passes calibration, incremental-market-value and out-of-sample validation.
