# Architecture

## System boundary

LadePulse consumes official/backend source publications, normalizes them into a provenance-preserving model, derives state events and exact ten-minute snapshots, and serves bounded/aggregated APIs to Flutter. Mobile devices never ingest provider feeds.

## Runtime components

1. **Ingestion worker**
   - Runs adapters on source-specific schedules.
   - Applies authentication, conditional requests, rate limiting, exponential backoff, and `Retry-After`.
   - Hashes payloads, validates schemas, preserves full/delta metadata, and writes feed health.
   - Stores raw payloads only when licence metadata permits.

2. **Normalization and persistence**
   - PostgreSQL/PostGIS stores inventory, observations, events, snapshots, incidents, licences, and metrics.
   - Original source identifiers remain immutable.
   - Observation tables are range-partitioned by UTC time.
   - Event derivation is idempotent and uses source observation time.

3. **Analytics**
   - Ten-minute national/region snapshots are exact analytical buckets, independent of source cadence.
   - Physical state, freshness, observable coverage, and identifier completeness remain separate dimensions.

4. **FastAPI**
   - Read-only Phase 1 API.
   - Pulse, bounded map, station detail/history, and time-series endpoints.
   - Redis is health-checked and available for coordination/caching; Phase 1's
     bounded demo queries read PostgreSQL directly so cache invalidation is not
     falsely presented as implemented.
   - OpenAPI is the client contract source.

5. **Flutter**
   - Material 3, Riverpod, go_router, Dio, MapLibre.
   - German and English localization.
   - Server-side clusters and bounded site queries.
   - Persistent data-mode, coverage, freshness, and licence disclosure.

## Core entities

- `DataSource`, `SourcePublication`, `DataLicence`
- `Operator`
- `ChargingSite`, `ChargingStation`, `EVSE`, `Connector`, `StaticCapability`
- `StatusObservation`, `StatusEvent`, `PriceObservation`, `FeedHealthObservation`
- `RegionSnapshot`, `NationalSnapshot`
- `DetectedIncident`, `ReliabilityMetric`
- `RawPayloadEnvelope`

## Data-state rules

- The latest source state is preserved even after it becomes stale.
- Query-time effective state becomes `stale_unknown` after the publication-specific threshold.
- Offline is accepted only from a current observation that semantically represents unavailability/failure.
- Aggregates expose observed, registered/reconciled, and total-in-demo denominators separately.

## Security

- Source credentials and X.509 material are backend-only secrets.
- The Flutter app receives no provider endpoints or credentials.
- Payload content is excluded from application logs.
- Phase 1 is read-only and has no user PII.
