# LadePulse DE repository guidance

## Product invariants

- Synthetic data must always be labelled `synthetic_demo` in storage, APIs, and UI.
- Unknown or stale status is not offline.
- Keep `source_observed_at` and `ingested_at` as separate UTC timestamps.
- Every aggregate must expose its denominator, coverage, and confidence.
- Never deduplicate primarily by station name or coordinates.
- Do not add or guess live endpoints, credentials, licences, rate limits, or coverage.
- Mobile clients use normalized bounding-box and aggregate APIs; they never download a national feed.

## Engineering conventions

- Backend: Python 3.13, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL/PostGIS.
- Python source lives under `src/` and is formatted/linted with Ruff.
- Flutter: Material 3, Riverpod, go_router, Dio, intl, and MapLibre.
- Internal timestamps and API timestamps are UTC. Display times use `Europe/Berlin`.
- Add migrations for schema changes and tests for metric/state semantic changes.
- Preserve source provenance and original identifiers.

## Verification

- Backend: `make test-backend`
- Flutter: `make test-mobile`
- All checks: `make test`
- Do not deploy, push, or provision external credentials without explicit permission.


## GitHub automation protection

Do not create, modify, delete, enable, disable, or rename `.github/workflows/**` or `.github/dependabot.yml`.
Do not add GitHub Actions, CI/CD, scheduled jobs, release automation, artifact uploads, or Actions caches.
If a task would benefit from any of these changes, stop and request explicit approval first.
