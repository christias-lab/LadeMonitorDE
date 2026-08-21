# LadePulse DE

LadePulse DE is an Android-first Flutter observability app for Germany's public EV charging network. It focuses on network health, utilization, outages, reliability, history, and data transparency rather than navigation, payment, or session control.

The default mode is a deterministic local demonstration. An opt-in
`live_partial` mode uses the official Bundesnetzagentur static register and
never represents inventory as live availability.

## Repository

- `apps/mobile` — Flutter application.
- `services/api` — FastAPI public API.
- `services/ingestion` — ingestion worker and deterministic demo generator.
- `packages/backend_core` — shared domain, persistence, and analytics.
- `packages/contracts` — OpenAPI contract and generated-client boundary.
- `infra` — container configuration.
- `docs` — sources, architecture, metrics, security, and ADRs.

## Prerequisites

- Docker with Compose.
- Flutter 3.44.8 / Dart 3.12.2 for mobile development.
- Android Studio or an Android SDK/emulator.

The backend runs in containers and does not require host Python packages.

## Quick start

```bash
cp .env.example .env
make infra-up
make migrate
make demo-seed
make official-import
make backend-up
```

API documentation is available at `http://localhost:8000/docs`. The demo reference time defaults to `2026-07-29T12:00:00Z`, so the complete deterministic history remains available regardless of wall-clock time.

Phase 1 API routes:

- `GET /v1/meta`
- `GET /v1/pulse?at=...`
- `GET /v1/map?west=...&south=...&east=...&north=...&zoom=...&at=...`
- `GET /v1/stations/{site_id}?at=...`
- `GET /v1/stations/{site_id}/history?from=...&to=...`

Run the mobile app:

```bash
make mobile-get
make mobile-run
```

Run against the imported official register:

```bash
DATA_MODE=live_partial API_BASE_URL=http://localhost:8000 make mobile-run
```

`live_partial` means official inventory with unknown availability. The current
register snapshot is not a real-time status feed. Mobilithek dynamic status is
disabled until an approved publication URL and its X.509 client certificate
are configured.

For an Android emulator, override the API URL when needed:

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

Use `http://localhost:8000` for a physical device only when the device can
resolve that host (for example via `adb reverse tcp:8000 tcp:8000`); otherwise
pass the development machine's LAN address. Release builds do not opt into
cleartext HTTP.

The map style defaults to MapLibre's public demonstration style. Configure an
appropriately licensed/self-hosted style before production use.

## Verification

```bash
make test-backend
make test-mobile
make test
```

Formatting and linting:

```bash
make format
make lint
```

## Data semantics

- All stored timestamps are UTC.
- `source_observed_at` is distinct from `ingested_at`.
- Stale status is unknown, not offline.
- Utilization excludes offline and unknown connectors.
- Every aggregate returns denominators and coverage.
- Responses explicitly identify `synthetic_demo` or `live_partial`.
- `live_partial` reports zero live coverage until a verified dynamic feed is
  connected.

See [architecture](docs/architecture.md), [metrics](docs/metrics.md), and [data sources](docs/data-sources.md).
