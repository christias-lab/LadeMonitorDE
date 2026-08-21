# ADR 0001: Native PostgreSQL partitioning first

Status: accepted

Use PostgreSQL/PostGIS with native range partitioning for time-series observations. This keeps local and deployment environments portable and avoids adopting TimescaleDB before real ingestion volume is measured. Revisit TimescaleDB after Phase 3 load evidence.

