# Data sources and access status

Verified on 30 July 2026. A source is not enabled until its exact publication-level access, licence, storage rights, cadence, and rate limits are recorded.

## Bundesnetzagentur charging register

- Purpose: static inventory and reconciliation.
- Enabled mode: `live_partial`.
- Imported snapshot: 28 July 2026, containing 115,435 locations and 207,225
  declared charging points.
- Status semantics: no availability observations are present; every charging
  point remains `stale_unknown`.
- Public downloads: CSV/XLSX, updated monthly.
- Public REST interface: JSON/XML dataset, updated daily. The Bundesnetzagentur supplies its OpenAPI description and prerequisites on request; no endpoint is assumed here.
- Authentication: none stated for public files; API prerequisites remain to be confirmed from its OpenAPI package.
- Licence/storage: CC BY 4.0. Storage, transformation, and redistribution are permitted with attribution to `bundesnetzagentur.de`.
- Coverage: completed public charging-point notifications only. The authority explicitly states that the Ladesäulenverordnung does not ensure complete coverage.
- Official pages:
  - https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/DownloadundKontakt.html
  - https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/FAQ/start.html
  - https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/Schnittstellen/start.html

## Mobilithek AFIR publications

- Purpose: discover and consume operator static/dynamic publications.
- Runtime status: disabled pending an approved technical-consumer subscription.
  The application requires an explicitly supplied publication URL, certificate
  path, and private-key path and has no guessed default endpoint.
- Catalog status at verification: 69 AFIR search hits; 65 in charging, 57 DATEX II v3, and 57 brokered. Static/dynamic pairs mean these are not independent nationwide networks.
- Format: Germany's AFIR profile uses JSON DATEX II v3. Static and dynamic publications are separate; dynamic publications support deltas.
- Publication cadence: static changes no later than 24 hours after change; dynamic changes no later than one minute after change.
- Delivery: HTTPS, with push used by providers. Consumer pull and push delivery are supported by the broker.
- Authentication: organization registration, subscription, and Mobilithek-issued X.509 machine certificate for broker M2M access.
- Conditional pull: `Last-Modified` and `If-Modified-Since` are defined.
- Licence: the German AFIR publication guidance requires CC0; each offer is still persisted with its own effective metadata.
- Rate limits: no universal public value was found. Effective limits and `Retry-After` behavior must be verified after subscription.
- Raw storage: allowed only when the effective offer licence permits it. The ingestion envelope persists the decision.
- Official pages:
  - https://mobilithek.info/cms/downloads/afir-hilfe
  - https://mobilithek.info/cms/assets/65545c25-c155-488c-9c7c-b9da1c7685b5?download=

## EU requirements

Commission Implementing Regulation (EU) 2025/655:

- Static data: change-triggered and no later than 24 hours after change.
- Dynamic data: change-triggered and no later than one minute after change.
- DATEX II including CEN/TS 16157-10:2022 applies from 14 April 2026.
- Required qualities: completeness, correctness, consistency, timeliness, and reliability.

Source: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32025R0655

## Direct operator APIs

Direct APIs are enabled only when referenced by Mobilithek or supplied by the operator. Each adapter configuration must record:

- authoritative endpoint and publication IDs;
- authentication/secret location;
- static/dynamic and full/delta semantics;
- observation and update cadence;
- rate limit and retry behavior;
- licence, attribution, redistribution, and raw-retention rights;
- geographic/operator coverage and identifier namespace.

No direct operator endpoint is included in Phase 1.
