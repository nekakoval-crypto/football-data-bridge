# Manual Lineup Scenario contract

`PBK_MANUAL_LINEUP_SCENARIO_V1` is a user-entered WHAT-IF layer for private lineup information.

A READY scenario requires a fixture id, one formation and exactly 11 unique starters for each side. Draft mode may hold incomplete teams while the user is editing. Official XI is the preferred comparison baseline; Expected XI is used only when official data is unavailable.

The scenario output may include changed starters, formation changes, Player Grade XI-quality deltas, line-quality deltas and optional Player Importance delta. It is explicitly research-only and cannot overwrite provider data, probability, R1/R2/R3 eligibility, stake, Forward journal, settlement, motivation or other factual match context.

Saved scenarios are append-only JSONL records keyed by deterministic scenario id. Re-saving the same scenario is idempotent.