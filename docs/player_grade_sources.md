# Player Grade source provenance

PBK Player Grade research currently targets two source tiers.

- **API-Football `/fixtures/players`** — aggregate per-match player statistics for production v0.1. PBK stores the provider rating only as a reference and computes its own transparent research grade.
- **StatsBomb Open Data (`hudl/open-data`)** — public JSON research corpus with competitions, matches, lineups, events and selected 360 files. PBK uses this for event-level action grading experiments and must preserve StatsBomb attribution when publishing analysis derived from the dataset.

The code in this repository does not fetch either source during PR/push CI. Data ingestion remains separate from grading so provider budget/network access cannot be triggered by the grade engine.

## Stage91 player xG/xA research contour

StatsBomb Open Data is also the research source for Stage91 player advanced metrics.

- player xG is read directly from `shot.statsbomb_xg`;
- player xA / xG Assisted is derived by joining the creating pass event ID to `shot.key_pass_id` and assigning the created shot's xG to the passer;
- raw StatsBomb event JSON is not committed to PBK;
- StatsBomb attribution requirements are preserved;
- StatsBomb player IDs remain a separate namespace until a conservative PBK identity mapping is implemented;
- these metrics have no betting/model authority by themselves.
