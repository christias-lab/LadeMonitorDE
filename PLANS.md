# LadePulse DE implementation plan

## Phase 0 — research and architecture

Status: completed before application code.

- Verify official source access, format, cadence, authentication, and licences.
- Record the system architecture, metric definitions, and architecture decisions.
- Establish the synthetic/live separation and repository rules.

## Phase 1 — deterministic vertical slice

Status: completed.

- Dockerized PostGIS, Redis, MinIO, API, and ingestion worker.
- Deterministic German synthetic inventory and 48-hour ten-minute history.
- National pulse, bounding-box clustered map, station detail, and history APIs.
- Flutter Pulse, map, station detail, localization, and time slider.
- Backend, integration, contract, and Flutter tests.

### Acceptance record

- [x] A clean database migrates through Alembic and PostGIS initializes on
      Apple Silicon as well as x86 container hosts.
- [x] Repeated seed runs produce 512 sites, 1,536 EVSEs, 3,072 connectors,
      289 national buckets, and one deduplicated raw payload envelope.
- [x] Every stored/API/mobile demo surface is explicitly labelled
      `synthetic_demo` and never claims to be a live feed.
- [x] Pulse exposes state counts, inventory/reporting/fresh denominators,
      utilization comparison, incidents, recovery, and all pressure inputs.
- [x] Map requests require a bounding box and zoom, use server clustering, and
      return no more than 500 features.
- [x] Station detail exposes connector state/age/power/type/price, time-weighted
      reliability, 145-point 24-hour history, nearby straight-line alternatives,
      and source/licence provenance.
- [x] Flutter provides responsive German/English Material 3 dashboard, MapLibre
      map/filter/legend, station detail, and a 144-step ten-minute time slider.
- [x] Backend lint and 20 tests pass; Flutter analysis and 4 tests pass.
- [x] The Android debug APK builds with the native MapLibre integration.

## Phase 2 — Bundesnetzagentur inventory

- Repeatable official CSV import with CC BY 4.0 attribution.
- Daily REST adapter only after receiving the official OpenAPI description.
- Identifier-first reconciliation and explicit unmatched/conflict reporting.

## Phase 3 — first AFIR publication pair

- Mobilithek organization, subscription, and X.509 machine certificate.
- One verified static/dynamic DATEX II v3 pair end to end.
- Full/delta recovery, feed health, and partial-live coverage display.

## Phase 4 — analytics

- Reliability and recovery metrics, Outage Radar, full Time Machine.
- Bayesian probability of a free connector.
- Fair operator/regional comparisons, resilience, prices, and transparency.

## Phase 5 — production hardening

- Identity and notification delivery where required.
- Monitoring, backups, rate limiting, security/GDPR review, load testing, deployment.
