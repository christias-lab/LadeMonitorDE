from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tempfile
import uuid
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import boto3
import httpx
import psycopg
from ladepulse_core.config import get_settings

NAMESPACE = uuid.UUID("1336b867-693c-47ae-83c4-846a2d7e6621")
SOURCE_ID = uuid.uuid5(NAMESPACE, "source:bundesnetzagentur-register")
LICENCE_ID = uuid.uuid5(NAMESPACE, "licence:cc-by-4.0-bnetza")
PUBLICATION_ID = uuid.uuid5(NAMESPACE, "publication:bnetza-register-csv")
DATA_MODE = "live_partial"
PUBLICATION_EXTERNAL_ID = "bnetza-ladesaeulenregister-csv"
EXPECTED_COLUMNS = {
    "Ladeeinrichtungs-ID",
    "Betreiber",
    "Status",
    "Anzahl Ladepunkte",
    "Bundesland",
    "Breitengrad",
    "Längengrad",
}


@dataclass(frozen=True)
class ChargingPointRecord:
    index: int
    connector_type: str
    max_power_kw: float
    evse_external_id: str
    public_key: str | None
    current_type: str


@dataclass(frozen=True)
class FacilityRecord:
    external_id: str
    operator_name: str
    display_name: str
    source_status: str
    address: str
    bundesland: str
    latitude: float
    longitude: float
    payment_methods: str | None
    points: tuple[ChargingPointRecord, ...]


def stable_id(value: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, value)


def source_date(path: Path) -> date:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for _ in range(20):
            line = handle.readline()
            if not line:
                break
            match = re.search(r"Letzte Aktualisierung vom:\s*(\d{2}\.\d{2}\.\d{4})", line)
            if match:
                return datetime.strptime(match.group(1), "%d.%m.%Y").date()
    raise ValueError("Bundesnetzagentur source date is missing from the CSV preamble")


def iter_facilities(path: Path) -> Iterator[FacilityRecord]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        for header in reader:
            if header and header[0] == "Ladeeinrichtungs-ID":
                break
        else:
            raise ValueError("Bundesnetzagentur CSV header was not found")
        missing = EXPECTED_COLUMNS.difference(header)
        if missing:
            raise ValueError(f"Bundesnetzagentur CSV columns missing: {sorted(missing)}")
        rows = csv.DictReader(handle, fieldnames=header, delimiter=";")
        for row_number, row in enumerate(rows, start=12):
            try:
                yield _parse_facility(row)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid Bundesnetzagentur row {row_number}: {exc}") from exc


def _parse_facility(row: dict[str, str]) -> FacilityRecord:
    facility_id = _required(row, "Ladeeinrichtungs-ID")
    operator = _required(row, "Betreiber")
    point_count = int(_required(row, "Anzahl Ladepunkte"))
    if not 1 <= point_count <= 6:
        raise ValueError(f"unsupported charging-point count {point_count}")
    source_evse_ids = [_clean(row.get(f"EVSE-ID{index}")) for index in range(1, point_count + 1)]
    duplicate_evse_ids = {
        value for value, count in Counter(source_evse_ids).items() if value and count > 1
    }
    points = []
    for index in range(1, point_count + 1):
        connector_type = _connector_type(_required(row, f"Steckertypen{index}"))
        power = _maximum_power(_required(row, f"Nennleistung Stecker{index}"))
        source_evse = source_evse_ids[index - 1]
        evse = source_evse or f"BNETZA:{facility_id}:{index}"
        if source_evse in duplicate_evse_ids:
            evse = f"{source_evse}#{index}"
        public_key = _clean(row.get(f"Public Key{index}"))
        points.append(
            ChargingPointRecord(
                index=index,
                connector_type=connector_type,
                max_power_kw=power,
                evse_external_id=evse,
                public_key=public_key,
                current_type=_current_type(connector_type, power),
            )
        )
    street = " ".join(
        part
        for part in (
            _clean(row.get("Straße")),
            _clean(row.get("Hausnummer")),
            _clean(row.get("Adresszusatz")),
        )
        if part
    )
    locality = " ".join(
        part for part in (_clean(row.get("Postleitzahl")), _clean(row.get("Ort"))) if part
    )
    address = ", ".join(part for part in (street, locality) if part)
    display_name = (
        _clean(row.get("Anzeigename (Karte)")) or _clean(row.get("Standortbezeichnung")) or operator
    )
    return FacilityRecord(
        external_id=facility_id,
        operator_name=operator,
        display_name=display_name,
        source_status=_required(row, "Status"),
        address=address,
        bundesland=_required(row, "Bundesland"),
        latitude=_decimal(_required(row, "Breitengrad")),
        longitude=_decimal(_required(row, "Längengrad")),
        payment_methods=_clean(row.get("Bezahlsysteme")),
        points=tuple(points),
    )


def _required(row: dict[str, str], key: str) -> str:
    value = _clean(row.get(key))
    if value is None:
        raise ValueError(f"{key} is empty")
    return value


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.replace("\u00a0", " ").split())
    return cleaned or None


def _decimal(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))


def _maximum_power(value: str) -> float:
    return max(_decimal(part.strip()) for part in value.split(";") if part.strip())


def _connector_type(value: str) -> str:
    distinct: list[str] = []
    for part in value.split(";"):
        cleaned = part.strip()
        if cleaned and cleaned not in distinct:
            distinct.append(cleaned)
    if not distinct:
        raise ValueError("connector type list is empty")
    return "; ".join(distinct)


def _current_type(connector_type: str, power: float) -> str:
    if "DC " in connector_type or connector_type.startswith("DC") or power > 44:
        return "DC"
    return "AC"


def download_register(target: Path, url: str, etag: str | None) -> tuple[str, str | None]:
    headers = {"User-Agent": "LadePulse-DE/0.1 (+local observability import)"}
    if etag:
        headers["If-None-Match"] = etag
    hasher = hashlib.sha256()
    with httpx.stream(
        "GET",
        url,
        headers=headers,
        follow_redirects=True,
        timeout=httpx.Timeout(120, connect=20),
    ) as response:
        if response.status_code == 304:
            raise NotModifiedError
        response.raise_for_status()
        with target.open("wb") as output:
            for chunk in response.iter_bytes():
                hasher.update(chunk)
                output.write(chunk)
        return hasher.hexdigest(), response.headers.get("etag")


class NotModifiedError(RuntimeError):
    pass


def import_register(
    path: Path, payload_hash: str, etag: str | None, source_url: str
) -> dict[str, Any]:
    settings = get_settings()
    observed_date = source_date(path)
    observed_at = datetime(
        observed_date.year,
        observed_date.month,
        observed_date.day,
        tzinfo=UTC,
    )
    object_key = f"bundesnetzagentur/{observed_date.isoformat()}/{payload_hash}.csv"
    _upload_payload(path, object_key)

    site_count = 0
    connector_count = 0
    operator_ids: set[uuid.UUID] = set()
    state_counts: dict[str, int] = {}
    with psycopg.connect(settings.psycopg_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(128042)")
            if cursor.execute(
                "SELECT 1 FROM raw_payload_envelopes WHERE payload_hash = %s",
                (payload_hash,),
            ).fetchone():
                return {
                    "status": "unchanged",
                    "payload_hash": payload_hash,
                    "source_observed_at": observed_at.isoformat(),
                }
            _upsert_metadata(cursor, observed_at, source_url)
            _clear_previous_inventory(cursor)
            _create_stage(cursor)
            with cursor.copy(
                """
                COPY bnetza_inventory_stage (
                  facility_external_id, operator_id, operator_name, site_id,
                  station_id, point_index, evse_id, evse_external_id,
                  connector_id, connector_external_id, connector_type,
                  max_power_kw, current_type, status_capability_id,
                  public_key_capability_id, display_name, address,
                  source_status, bundesland, latitude, longitude,
                  payment_methods, public_key
                ) FROM STDIN
                """
            ) as copy:
                for facility in iter_facilities(path):
                    site_count += 1
                    state_counts[facility.bundesland] = state_counts.get(
                        facility.bundesland, 0
                    ) + len(facility.points)
                    operator_id = stable_id(f"bnetza:operator:{facility.operator_name}")
                    operator_ids.add(operator_id)
                    site_id = stable_id(f"bnetza:site:{facility.external_id}")
                    station_id = stable_id(f"bnetza:station:{facility.external_id}")
                    for point in facility.points:
                        connector_count += 1
                        evse_id = stable_id(f"bnetza:evse:{facility.external_id}:{point.index}")
                        connector_id = stable_id(
                            f"bnetza:connector:{facility.external_id}:{point.index}"
                        )
                        copy.write_row(
                            (
                                facility.external_id,
                                operator_id,
                                facility.operator_name,
                                site_id,
                                station_id,
                                point.index,
                                evse_id,
                                point.evse_external_id,
                                connector_id,
                                f"{facility.external_id}:{point.index}",
                                point.connector_type,
                                point.max_power_kw,
                                point.current_type,
                                stable_id(f"bnetza:status:{connector_id}"),
                                (
                                    stable_id(f"bnetza:public-key:{connector_id}")
                                    if point.public_key
                                    else None
                                ),
                                facility.display_name,
                                facility.address,
                                facility.source_status,
                                facility.bundesland,
                                facility.latitude,
                                facility.longitude,
                                facility.payment_methods,
                                point.public_key,
                            )
                        )
            _materialize_stage(cursor)
            _insert_snapshots(
                cursor,
                observed_at,
                site_count,
                connector_count,
                state_counts,
            )
            cursor.execute(
                """
                INSERT INTO raw_payload_envelopes (
                  id, publication_id, received_at, source_observed_at,
                  payload_hash, etag, last_modified, content_type,
                  schema_version, publication_mode, object_key, retained,
                  retention_reason
                ) VALUES (
                  %s, %s, %s, %s, %s, %s, NULL, 'text/csv',
                  %s, 'full', %s, TRUE, %s
                )
                """,
                (
                    stable_id(f"raw:{payload_hash}"),
                    PUBLICATION_ID,
                    datetime.now(UTC),
                    observed_at,
                    payload_hash,
                    etag,
                    observed_date.isoformat(),
                    object_key,
                    "CC BY 4.0 permits attributed storage and transformation.",
                ),
            )
            cursor.execute(
                """
                INSERT INTO feed_health_observations (
                  id, publication_id, observed_at, status, latency_seconds, message
                ) VALUES (%s, %s, %s, 'static_import_success', NULL, %s)
                """,
                (
                    uuid.uuid4(),
                    PUBLICATION_ID,
                    datetime.now(UTC),
                    json.dumps(
                        {
                            "sites": site_count,
                            "connectors": connector_count,
                            "operators": len(operator_ids),
                            "source_date": observed_date.isoformat(),
                        },
                        sort_keys=True,
                    ),
                ),
            )
        connection.commit()
    return {
        "status": "imported",
        "data_mode": DATA_MODE,
        "source_observed_at": observed_at.isoformat(),
        "payload_hash": payload_hash,
        "sites": site_count,
        "connectors": connector_count,
        "operators": len(operator_ids),
    }


def _upsert_metadata(cursor: psycopg.Cursor[Any], observed_at: datetime, source_url: str) -> None:
    cursor.execute(
        """
        INSERT INTO data_licences (
          id, code, name, url, attribution, raw_storage_allowed,
          redistribution_allowed, verified_at
        ) VALUES (%s, 'CC-BY-4.0-BNETZA', 'Creative Commons Attribution 4.0',
          'https://creativecommons.org/licenses/by/4.0/',
          'Quelle: bundesnetzagentur.de', TRUE, TRUE, %s)
        ON CONFLICT (id) DO UPDATE SET verified_at = EXCLUDED.verified_at
        """,
        (LICENCE_ID, datetime.now(UTC)),
    )
    cursor.execute(
        """
        INSERT INTO data_sources (
          id, key, name, kind, data_mode, base_url, enabled, created_at
        ) VALUES (
          %s, 'bundesnetzagentur-register', 'Bundesnetzagentur Ladesäulenregister',
          'official_register', %s, %s, TRUE, %s
        )
        ON CONFLICT (id) DO UPDATE SET
          base_url = EXCLUDED.base_url,
          enabled = TRUE
        """,
        (SOURCE_ID, DATA_MODE, source_url, datetime.now(UTC)),
    )
    cursor.execute(
        """
        INSERT INTO source_publications (
          id, data_source_id, licence_id, external_id, name, format,
          schema_version, delivery_mode, publication_type, supports_delta,
          update_interval_seconds, stale_after_seconds, rate_limit_notes,
          storage_rights_verified
        ) VALUES (
          %s, %s, %s, %s, 'Liste der Ladesäulen (CSV)', 'text/csv',
          %s, 'pull', 'static', FALSE, 2592000, 3888000,
          'Official monthly file; conditional GET used when ETag is available.',
          TRUE
        )
        ON CONFLICT (id) DO UPDATE SET
          schema_version = EXCLUDED.schema_version,
          rate_limit_notes = EXCLUDED.rate_limit_notes
        """,
        (
            PUBLICATION_ID,
            SOURCE_ID,
            LICENCE_ID,
            PUBLICATION_EXTERNAL_ID,
            observed_at.date().isoformat(),
        ),
    )


def _clear_previous_inventory(cursor: psycopg.Cursor[Any]) -> None:
    cursor.execute(
        """
        DELETE FROM reliability_metrics
        WHERE scope_type = 'site'
          AND scope_id IN (
            SELECT id FROM charging_sites WHERE publication_id = %s
          )
        """,
        (PUBLICATION_ID,),
    )
    cursor.execute("DELETE FROM charging_sites WHERE publication_id = %s", (PUBLICATION_ID,))
    cursor.execute("DELETE FROM operators WHERE data_source_id = %s", (SOURCE_ID,))
    cursor.execute("DELETE FROM national_snapshots WHERE data_mode = %s", (DATA_MODE,))
    cursor.execute("DELETE FROM region_snapshots WHERE data_mode = %s", (DATA_MODE,))


def _create_stage(cursor: psycopg.Cursor[Any]) -> None:
    cursor.execute(
        """
        CREATE TEMP TABLE bnetza_inventory_stage (
          facility_external_id text NOT NULL,
          operator_id uuid NOT NULL,
          operator_name text NOT NULL,
          site_id uuid NOT NULL,
          station_id uuid NOT NULL,
          point_index integer NOT NULL,
          evse_id uuid NOT NULL,
          evse_external_id text NOT NULL,
          connector_id uuid NOT NULL,
          connector_external_id text NOT NULL,
          connector_type text NOT NULL,
          max_power_kw double precision NOT NULL,
          current_type text NOT NULL,
          status_capability_id uuid NOT NULL,
          public_key_capability_id uuid,
          display_name text NOT NULL,
          address text NOT NULL,
          source_status text NOT NULL,
          bundesland text NOT NULL,
          latitude double precision NOT NULL,
          longitude double precision NOT NULL,
          payment_methods text,
          public_key text
        ) ON COMMIT DROP
        """
    )


def _materialize_stage(cursor: psycopg.Cursor[Any]) -> None:
    cursor.execute(
        """
        INSERT INTO operators (id, data_source_id, external_id, name, country_code)
        SELECT DISTINCT operator_id, %s, operator_name, operator_name, 'DE'
        FROM bnetza_inventory_stage
        """,
        (SOURCE_ID,),
    )
    cursor.execute(
        """
        INSERT INTO charging_sites (
          id, publication_id, operator_id, external_id, name, address,
          bundesland, latitude, longitude, geom, corridor, data_mode
        )
        SELECT DISTINCT ON (site_id)
          site_id, %s, operator_id, facility_external_id, display_name,
          address, bundesland, latitude, longitude,
          ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
          FALSE, %s
        FROM bnetza_inventory_stage
        ORDER BY site_id
        """,
        (PUBLICATION_ID, DATA_MODE),
    )
    cursor.execute(
        """
        INSERT INTO charging_stations (id, site_id, external_id)
        SELECT DISTINCT station_id, site_id, facility_external_id
        FROM bnetza_inventory_stage
        """
    )
    cursor.execute(
        """
        INSERT INTO evses (id, station_id, external_id, max_power_kw, current_type)
        SELECT evse_id, station_id, evse_external_id, max_power_kw, current_type
        FROM bnetza_inventory_stage
        """
    )
    cursor.execute(
        """
        INSERT INTO connectors (
          id, evse_id, external_id, connector_type, max_power_kw
        )
        SELECT connector_id, evse_id, connector_external_id,
               connector_type, max_power_kw
        FROM bnetza_inventory_stage
        """
    )
    cursor.execute(
        """
        INSERT INTO static_capabilities (id, connector_id, capability, value)
        SELECT
          status_capability_id,
          connector_id, 'register_status', source_status
        FROM bnetza_inventory_stage
        UNION ALL
        SELECT
          public_key_capability_id,
          connector_id, 'public_key', public_key
        FROM bnetza_inventory_stage
        WHERE public_key IS NOT NULL
        """
    )


def _insert_snapshots(
    cursor: psycopg.Cursor[Any],
    observed_at: datetime,
    site_count: int,
    connector_count: int,
    state_counts: dict[str, int],
) -> None:
    generated_at = datetime.now(UTC)
    cursor.execute(
        """
        INSERT INTO national_snapshots (
          bucket_start, data_mode, available, in_use, out_of_service,
          stale_unknown, inventory_connectors, reported_connectors,
          fresh_connectors, hpc_available, utilization, normal_utilization,
          pressure_score, pressure_components, serious_incidents,
          recovered_last_hour, source_observed_at, generated_at
        ) VALUES (
          %s, %s, 0, 0, 0, %s, %s, 0, 0, 0,
          NULL, NULL, NULL, 'null'::jsonb, 0, 0, %s, %s
        )
        """,
        (
            observed_at,
            DATA_MODE,
            connector_count,
            connector_count,
            observed_at,
            generated_at,
        ),
    )
    cursor.executemany(
        """
        INSERT INTO region_snapshots (
          bundesland, bucket_start, data_mode, available, in_use,
          out_of_service, stale_unknown, inventory_connectors,
          utilization, pressure_score, confidence
        ) VALUES (%s, %s, %s, 0, 0, 0, %s, %s, NULL, NULL, 0)
        """,
        [(state, observed_at, DATA_MODE, count, count) for state, count in state_counts.items()],
    )
    if site_count <= 0:
        raise ValueError("Bundesnetzagentur import produced no sites")


def _upload_payload(path: Path, object_key: str) -> None:
    settings = get_settings()
    if not settings.raw_payload_retention_enabled:
        return
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )
    client.upload_file(str(path), settings.s3_bucket, object_key)


def _latest_etag() -> str | None:
    settings = get_settings()
    with (
        psycopg.connect(settings.psycopg_dsn) as connection,
        connection.cursor() as cursor,
    ):
        row = cursor.execute(
            """
            SELECT r.etag
            FROM raw_payload_envelopes r
            WHERE r.publication_id = %s
            ORDER BY r.received_at DESC
            LIMIT 1
            """,
            (PUBLICATION_ID,),
        ).fetchone()
        return None if row is None else row[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the official BNetzA register")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--url")
    args = parser.parse_args()
    settings = get_settings()
    source_url = args.url or settings.bnetza_csv_url
    if args.file:
        path = args.file
        payload_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        etag = None
        print(json.dumps(import_register(path, payload_hash, etag, source_url), sort_keys=True))
        return
    with tempfile.TemporaryDirectory(prefix="ladepulse-bnetza-") as temp:
        path = Path(temp) / "register.csv"
        try:
            payload_hash, etag = download_register(path, source_url, _latest_etag())
        except NotModifiedError:
            print(json.dumps({"status": "not_modified"}, sort_keys=True))
            return
        result = import_register(path, payload_hash, etag, source_url)
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
