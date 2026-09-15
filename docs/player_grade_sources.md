# Player Grade source provenance

PBK Player Grade research currently targets two source tiers.

- **API-Football `/fixtures/players`** — aggregate per-match player statistics for production v0.1. PBK stores the provider rating only as a reference and computes its own transparent research grade.
- **StatsBomb Open Data (`hudl/open-data`)** — public JSON research corpus with competitions, matches, lineups, events and selected 360 files. PBK uses this for event-level action grading experiments and must preserve StatsBomb attribution when publishing analysis derived from the dataset.

The code in this repository does not fetch either source during PR/push CI. Data ingestion remains separate from grading so provider budget/network access cannot be triggered by the grade engine.