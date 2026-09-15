# Player Grade / lineup data status

Status on current `main` before Stage80: **ACTIVE RESEARCH / IMPLEMENTED THROUGH STAGE79**.

Implemented and merged:
- Player Grade foundation, Form 5/10, XI Quality and manual lineup scenario contract;
- Stage77 provider-backed per-fixture player-stat capture through the shared broker, with immutable Player Grade snapshots and no-lookahead consumption;
- Stage72-compatible projection of captured player data;
- Match Card Player Grade / XI Quality rendering and manual lineup configurator;
- Stage78 provider-free coverage/integrity audit, XI-quality history and conservative Player Importance research;
- always-on Manual Lineup WHAT-IF forecast sandbox, explicitly unvalidated and isolated from canonical probability/EV/eligibility/stake/Forward;
- Stage79 cached current team rosters for the player picker when expected/official XI is absent.

Not claimed complete:
- durable history for slow-changing roster state beyond the current read model (Stage80 begins this);
- complete historical player/event warehouse across all leagues/seasons;
- verified xG/xA/event-level coverage for the full PBK scope;
- promotion of Player Grade/Importance into canonical probability or strategy logic.

Promotion rule remains unchanged: Player Grade / XI / Importance evidence is research/context only until independent prospective validation demonstrates stable incremental value and a separately locked model change is approved.
