# Definition of done — Player Grade foundation

This foundation slice is complete when provider-free CI proves: aggregate normalization and grading are deterministic; event action scores remain on the -2..+2 half-step scale; rolling form respects the pre-match cutoff; XI Quality reports missing coverage; manual scenarios require valid XIs for READY state; official XI is preferred as baseline; scenario persistence is append-only/idempotent; and all canonical/model/stake/Forward mutation flags remain false.

Production ingestion, Stage72 projection, Match Card rendering and the interactive manual configurator remain subsequent slices.