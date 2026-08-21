from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
import psycopg
from ladepulse_core.config import get_settings
from ladepulse_core.events import StateMessage, derive_status_events
from ladepulse_core.metrics import charging_pressure, offline_share, utilization

NAMESPACE = uuid.UUID("1336b867-693c-47ae-83c4-846a2d7e6621")
SOURCE_ID = uuid.uuid5(NAMESPACE, "source:synthetic-demo")
LICENCE_ID = uuid.uuid5(NAMESPACE, "licence:synthetic-demo")
STATIC_PUBLICATION_ID = uuid.uuid5(NAMESPACE, "publication:synthetic-static")
DYNAMIC_PUBLICATION_ID = uuid.uuid5(NAMESPACE, "publication:synthetic-dynamic")
SITE_COUNT = 512
EVSE_PER_SITE = 3
CONNECTORS_PER_EVSE = 2
BUCKET_COUNT = 289
DATA_MODE = "synthetic_demo"

STATE_CENTERS = {
    "Baden-Württemberg": (48.54, 9.04),
    "Bayern": (48.95, 11.40),
    "Berlin": (52.52, 13.405),
    "Brandenburg": (52.40, 13.05),
    "Bremen": (53.08, 8.80),
    "Hamburg": (53.55, 10.00),
    "Hessen": (50.55, 9.00),
    "Mecklenburg-Vorpommern": (53.75, 12.50),
    "Niedersachsen": (52.75, 9.20),
    "Nordrhein-Westfalen": (51.45, 7.60),
    "Rheinland-Pfalz": (49.95, 7.35),
    "Saarland": (49.38, 6.95),
    "Sachsen": (51.05, 13.35),
    "Sachsen-Anhalt": (51.95, 11.70),
    "Schleswig-Holstein": (54.20, 9.80),
    "Thüringen": (50.95, 11.10),
}
OPERATOR_NAMES = (
    "DemoCharge Nord",
    "DemoCharge Süd",
    "Rhein Demo Energie",
    "Pulse Autobahn",
    "Stadtstrom Demo",
    "Hanseatic Demo",
    "MittelDE Demo",
    "Alpenstrom Demo",
)


@dataclass(frozen=True)
class DemoConnector:
    index: int
    id: uuid.UUID
    site_id: uuid.UUID
    site_index: int
    bundesland: str
    max_power_kw: float


def stable_id(value: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, value)


def seed_demo(reset: bool) -> None:
    settings = get_settings()
    rng = random.Random(settings.demo_seed)
    reference_time = settings.demo_reference_time.astimezone(UTC)
    start_time = reference_time - timedelta(hours=48)
    connectors: list[DemoConnector] = []

    with psycopg.connect(settings.psycopg_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(128041)")
            if reset:
                _delete_existing_demo(cursor)
            _insert_metadata(cursor, reference_time)
            _insert_inventory(cursor, rng, connectors)
            _insert_prices(cursor, connectors, start_time)
            _insert_history_and_snapshots(
                cursor,
                connectors,
                start_time,
                reference_time,
            )
            _insert_reliability_and_incidents(cursor, connectors, reference_time)
            payload = _manifest_payload(settings.demo_seed, reference_time)
            _store_payload(cursor, payload, reference_time)
        connection.commit()
    _upload_payload(payload)
    print(
        json.dumps(
            {
                "data_mode": DATA_MODE,
                "seed": settings.demo_seed,
                "reference_time": reference_time.isoformat(),
                "sites": SITE_COUNT,
                "evses": SITE_COUNT * EVSE_PER_SITE,
                "connectors": len(connectors),
                "buckets": BUCKET_COUNT,
            },
            sort_keys=True,
        )
    )


def _delete_existing_demo(cursor: psycopg.Cursor[Any]) -> None:
    cursor.execute(
        """
        DELETE FROM reliability_metrics
        WHERE scope_type = 'site'
          AND scope_id IN (
            SELECT s.id
            FROM charging_sites s
            JOIN source_publications p ON p.id = s.publication_id
            WHERE p.data_source_id = %s
          )
        """,
        (SOURCE_ID,),
    )
    cursor.execute("DELETE FROM national_snapshots WHERE data_mode = %s", (DATA_MODE,))
    cursor.execute("DELETE FROM region_snapshots WHERE data_mode = %s", (DATA_MODE,))
    # Remove sites before the source cascades into operators. PostgreSQL may
    # otherwise visit the operator foreign key before the publication cascade.
    cursor.execute(
        """
        DELETE FROM charging_sites
        WHERE publication_id IN (
          SELECT id FROM source_publications WHERE data_source_id = %s
        )
        """,
        (SOURCE_ID,),
    )
    cursor.execute("DELETE FROM data_sources WHERE id = %s", (SOURCE_ID,))


def _insert_metadata(cursor: psycopg.Cursor[Any], now: datetime) -> None:
    cursor.execute(
        """
        INSERT INTO data_licences (
          id, code, name, url, attribution, raw_storage_allowed,
          redistribution_allowed, verified_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET verified_at = EXCLUDED.verified_at
        """,
        (
            LICENCE_ID,
            "SYNTHETIC-DEMO-1.0",
            "LadePulse deterministic demonstration data",
            None,
            "Generated by LadePulse DE; not an official source.",
            True,
            True,
            now,
        ),
    )
    cursor.execute(
        """
        INSERT INTO data_sources (id, key, name, kind, data_mode, base_url, enabled, created_at)
        VALUES (%s, %s, %s, %s, %s, NULL, TRUE, %s)
        """,
        (
            SOURCE_ID,
            "synthetic-demo",
            "LadePulse deterministic demonstration generator",
            "synthetic",
            DATA_MODE,
            now,
        ),
    )
    publication_rows = (
        (
            STATIC_PUBLICATION_ID,
            SOURCE_ID,
            LICENCE_ID,
            "ladepulse-demo-static-v1",
            "Synthetic German static inventory",
            "application/json",
            "ladepulse-demo-1.0",
            "generated",
            "static",
            False,
            86400,
            172800,
            "Local deterministic generator; no external rate limit.",
            True,
        ),
        (
            DYNAMIC_PUBLICATION_ID,
            SOURCE_ID,
            LICENCE_ID,
            "ladepulse-demo-dynamic-v1",
            "Synthetic German dynamic status",
            "application/json",
            "ladepulse-demo-1.0",
            "generated",
            "dynamic",
            True,
            600,
            1200,
            "Local deterministic generator; no external rate limit.",
            True,
        ),
    )
    cursor.executemany(
        """
        INSERT INTO source_publications (
          id, data_source_id, licence_id, external_id, name, format, schema_version,
          delivery_mode, publication_type, supports_delta, update_interval_seconds,
          stale_after_seconds, rate_limit_notes, storage_rights_verified
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """,
        publication_rows,
    )
    operator_rows = [
        (
            stable_id(f"operator:{index}"),
            SOURCE_ID,
            f"DE-LPD-{index:03d}",
            name,
            "DE",
        )
        for index, name in enumerate(OPERATOR_NAMES)
    ]
    cursor.executemany(
        """
        INSERT INTO operators (id, data_source_id, external_id, name, country_code)
        VALUES (%s, %s, %s, %s, %s)
        """,
        operator_rows,
    )


def _insert_inventory(
    cursor: psycopg.Cursor[Any],
    rng: random.Random,
    connectors: list[DemoConnector],
) -> None:
    states = tuple(STATE_CENTERS)
    site_rows = []
    station_rows = []
    evse_rows = []
    connector_rows = []
    capability_rows = []
    connector_index = 0
    for site_index in range(SITE_COUNT):
        bundesland = states[site_index % len(states)]
        center_lat, center_lon = STATE_CENTERS[bundesland]
        scale = 0.10 if bundesland in {"Berlin", "Bremen", "Hamburg", "Saarland"} else 0.75
        latitude = center_lat + rng.uniform(-scale, scale)
        longitude = center_lon + rng.uniform(-scale * 1.25, scale * 1.25)
        site_id = stable_id(f"site:{site_index}")
        station_id = stable_id(f"station:{site_index}")
        operator_index = (site_index * 5 + site_index // 11) % len(OPERATOR_NAMES)
        site_rows.append(
            (
                site_id,
                STATIC_PUBLICATION_ID,
                stable_id(f"operator:{operator_index}"),
                f"DEMO-SITE-{site_index:04d}",
                f"LadePulse Demo {bundesland} {site_index + 1}",
                f"Demostraße {1 + site_index % 199}",
                bundesland,
                latitude,
                longitude,
                longitude,
                latitude,
                site_index % 7 == 0,
                DATA_MODE,
            )
        )
        station_rows.append((station_id, site_id, f"DE*LPD*S{site_index:06d}"))
        for evse_number in range(EVSE_PER_SITE):
            evse_id = stable_id(f"evse:{site_index}:{evse_number}")
            power = (22.0, 50.0, 150.0, 300.0)[(site_index + evse_number) % 4]
            current_type = "AC" if power <= 22 else "DC"
            evse_external = f"DE*LPD*E{site_index:06d}{evse_number + 1}"
            evse_rows.append((evse_id, station_id, evse_external, power, current_type))
            for connector_number in range(CONNECTORS_PER_EVSE):
                connector_id = stable_id(f"connector:{site_index}:{evse_number}:{connector_number}")
                connector_external = f"{evse_external}*{connector_number + 1}"
                connector_type = "Type 2" if power <= 22 else "CCS 2"
                connector_rows.append(
                    (
                        connector_id,
                        evse_id,
                        connector_external,
                        connector_type,
                        power,
                    )
                )
                capability_rows.append(
                    (
                        stable_id(f"capability:{connector_id}:auth"),
                        connector_id,
                        "ad_hoc_payment",
                        "supported",
                    )
                )
                connectors.append(
                    DemoConnector(
                        connector_index,
                        connector_id,
                        site_id,
                        site_index,
                        bundesland,
                        power,
                    )
                )
                connector_index += 1
    cursor.executemany(
        """
        INSERT INTO charging_sites (
          id, publication_id, operator_id, external_id, name, address, bundesland,
          latitude, longitude, geom, corridor, data_mode
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s,
          ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s
        )
        """,
        site_rows,
    )
    cursor.executemany(
        "INSERT INTO charging_stations (id, site_id, external_id) VALUES (%s, %s, %s)",
        station_rows,
    )
    cursor.executemany(
        """
        INSERT INTO evses (id, station_id, external_id, max_power_kw, current_type)
        VALUES (%s, %s, %s, %s, %s)
        """,
        evse_rows,
    )
    cursor.executemany(
        """
        INSERT INTO connectors (id, evse_id, external_id, connector_type, max_power_kw)
        VALUES (%s, %s, %s, %s, %s)
        """,
        connector_rows,
    )
    cursor.executemany(
        """
        INSERT INTO static_capabilities (id, connector_id, capability, value)
        VALUES (%s, %s, %s, %s)
        """,
        capability_rows,
    )


def _insert_prices(
    cursor: psycopg.Cursor[Any],
    connectors: list[DemoConnector],
    observed_at: datetime,
) -> None:
    rows = []
    for connector in connectors:
        if connector.index % 5 != 0:
            continue
        price = 0.39 + 0.02 * (connector.site_index % 12)
        rows.append(
            (
                stable_id(f"price:{connector.id}:{observed_at.isoformat()}"),
                connector.id,
                observed_at,
                "EUR",
                price,
                None,
                None,
                0.10 if connector.site_index % 9 == 0 else None,
            )
        )
    cursor.executemany(
        """
        INSERT INTO price_observations (
          id, connector_id, source_observed_at, currency,
          per_kwh, per_minute, session_fee, blocking_fee
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        rows,
    )


def _insert_history_and_snapshots(
    cursor: psycopg.Cursor[Any],
    connectors: list[DemoConnector],
    start_time: datetime,
    reference_time: datetime,
) -> None:
    last_observation: list[tuple[datetime, str] | None] = [None] * len(connectors)
    previous_site_outage: dict[int, bool] = defaultdict(bool)
    recovery_times: deque[datetime] = deque()
    national_rows: list[tuple[Any, ...]] = []
    region_rows: list[tuple[Any, ...]] = []
    sequence = 0
    state_count = len(STATE_CENTERS)
    inventory_per_region = (SITE_COUNT // state_count) * EVSE_PER_SITE * CONNECTORS_PER_EVSE

    with cursor.copy(
        """
        COPY status_observations (
          id, connector_id, publication_id, source_observed_at, ingested_at,
          state, payload_hash, sequence_number, is_delta
        ) FROM STDIN
        """
    ) as observation_copy:
        for bucket_index in range(BUCKET_COUNT):
            bucket = start_time + timedelta(minutes=10 * bucket_index)
            region_counts: dict[str, dict[str, int]] = defaultdict(_empty_counts)
            national = _empty_counts()
            hpc_available = 0
            site_counts: dict[int, dict[str, int]] = defaultdict(_empty_counts)
            for connector in connectors:
                if _is_stale_gap(connector.site_index, bucket_index):
                    latest = last_observation[connector.index]
                else:
                    state = _state_for(connector, bucket_index, bucket)
                    sequence += 1
                    observation_id = stable_id(f"observation:{connector.index}:{bucket_index}")
                    payload_hash = hashlib.sha256(
                        f"{connector.id}|{bucket.isoformat()}|{state}".encode()
                    ).hexdigest()
                    observation_copy.write_row(
                        (
                            observation_id,
                            connector.id,
                            DYNAMIC_PUBLICATION_ID,
                            bucket,
                            bucket + timedelta(seconds=8 + connector.index % 21),
                            state,
                            payload_hash,
                            sequence,
                            bucket_index > 0,
                        )
                    )
                    latest = (bucket, state)
                    last_observation[connector.index] = latest
                effective = (
                    "stale_unknown"
                    if latest is None or bucket - latest[0] > timedelta(minutes=20)
                    else latest[1]
                )
                national[effective] += 1
                region_counts[connector.bundesland][effective] += 1
                site_counts[connector.site_index][effective] += 1
                if effective == "available" and connector.max_power_kw >= 150:
                    hpc_available += 1

            serious = 0
            for site_index, counts in site_counts.items():
                all_offline = counts["out_of_service"] == (EVSE_PER_SITE * CONNECTORS_PER_EVSE)
                if all_offline:
                    serious += 1
                if previous_site_outage[site_index] and not all_offline:
                    recovery_times.append(bucket)
                previous_site_outage[site_index] = all_offline
            while recovery_times and bucket - recovery_times[0] > timedelta(hours=1):
                recovery_times.popleft()

            national_rows.append(
                _national_snapshot_row(
                    bucket,
                    reference_time,
                    national,
                    hpc_available,
                    serious,
                    len(recovery_times),
                    len(connectors),
                )
            )
            for bundesland, counts in region_counts.items():
                region_rows.append(
                    _region_snapshot_row(
                        bundesland,
                        bucket,
                        counts,
                        inventory_per_region,
                    )
                )
    cursor.executemany(
        """
        INSERT INTO national_snapshots (
          bucket_start, data_mode, available, in_use, out_of_service, stale_unknown,
          inventory_connectors, reported_connectors, fresh_connectors, hpc_available,
          utilization, normal_utilization, pressure_score, pressure_components,
          serious_incidents, recovered_last_hour, source_observed_at, generated_at
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
          %s, %s, %s, %s::jsonb, %s, %s, %s, %s
        )
        """,
        national_rows,
    )
    cursor.executemany(
        """
        INSERT INTO region_snapshots (
          bundesland, bucket_start, data_mode, available, in_use, out_of_service,
          stale_unknown, inventory_connectors, utilization, pressure_score, confidence
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        region_rows,
    )
    _insert_status_events(cursor, connectors, start_time)


def _insert_status_events(
    cursor: psycopg.Cursor[Any],
    connectors: list[DemoConnector],
    start_time: datetime,
) -> None:
    with cursor.copy(
        """
        COPY status_events (
          id, connector_id, from_state, to_state, started_at, ended_at
        ) FROM STDIN
        """
    ) as event_copy:
        for connector in connectors:
            messages = []
            for bucket_index in range(BUCKET_COUNT):
                if _is_stale_gap(connector.site_index, bucket_index):
                    continue
                bucket = start_time + timedelta(minutes=10 * bucket_index)
                state = _state_for(connector, bucket_index, bucket)
                messages.append(StateMessage(observed_at=bucket, state=state))
            for event in derive_status_events(messages):
                event_copy.write_row(
                    (
                        stable_id(
                            f"event:{connector.index}:"
                            f"{event.started_at.isoformat()}:{event.to_state}"
                        ),
                        connector.id,
                        event.from_state,
                        event.to_state,
                        event.started_at,
                        event.ended_at,
                    )
                )


def _national_snapshot_row(
    bucket: datetime,
    reference_time: datetime,
    counts: dict[str, int],
    hpc_available: int,
    serious: int,
    recovered_last_hour: int,
    inventory: int,
) -> tuple[Any, ...]:
    util = utilization(counts["available"], counts["in_use"])
    offline = offline_share(
        counts["available"],
        counts["in_use"],
        counts["out_of_service"],
    )
    normal = _normal_utilization(bucket)
    fresh = inventory - counts["stale_unknown"]
    pressure = charging_pressure(
        utilization_value=util,
        offline_share_value=offline,
        normal_utilization=normal,
        alternatives_gap=0.18,
        live_coverage=fresh / inventory,
        freshness_quality=0.98,
        identifier_completeness=1.0,
    )
    return (
        bucket,
        DATA_MODE,
        counts["available"],
        counts["in_use"],
        counts["out_of_service"],
        counts["stale_unknown"],
        inventory,
        inventory,
        fresh,
        hpc_available,
        util,
        normal,
        pressure.score if pressure else None,
        json.dumps(pressure.as_dict()) if pressure else json.dumps(None),
        serious,
        recovered_last_hour,
        bucket,
        reference_time + timedelta(seconds=30),
    )


def _region_snapshot_row(
    bundesland: str,
    bucket: datetime,
    counts: dict[str, int],
    inventory: int,
) -> tuple[Any, ...]:
    util = utilization(counts["available"], counts["in_use"])
    offline = offline_share(
        counts["available"],
        counts["in_use"],
        counts["out_of_service"],
    )
    fresh = inventory - counts["stale_unknown"]
    confidence = fresh / inventory if inventory else 0.0
    pressure = charging_pressure(
        utilization_value=util,
        offline_share_value=offline,
        normal_utilization=_normal_utilization(bucket),
        alternatives_gap=0.22,
        live_coverage=confidence,
        freshness_quality=0.98,
        identifier_completeness=1.0,
    )
    return (
        bundesland,
        bucket,
        DATA_MODE,
        counts["available"],
        counts["in_use"],
        counts["out_of_service"],
        counts["stale_unknown"],
        inventory,
        util,
        pressure.score if pressure else None,
        confidence,
    )


def _insert_reliability_and_incidents(
    cursor: psycopg.Cursor[Any],
    connectors: list[DemoConnector],
    reference_time: datetime,
) -> None:
    site_ids = {connector.site_index: connector.site_id for connector in connectors}
    metric_rows = []
    incident_rows = []
    for site_index, site_id in site_ids.items():
        observable = 0.82 if site_index % 41 == 0 else 0.99
        uptime_value = max(0.72, 0.995 - (site_index % 31) * 0.003)
        outage_count = 1 + site_index % 4
        metric_rows.append(
            (
                stable_id(f"reliability:{site_id}:7"),
                "site",
                site_id,
                7,
                reference_time,
                uptime_value,
                observable,
                outage_count,
                20.0 + site_index % 6 * 10,
                25.0 + site_index % 8 * 8,
                289 * EVSE_PER_SITE * CONNECTORS_PER_EVSE,
            )
        )
        if site_index % 113 == 0:
            incident_rows.append(
                (
                    stable_id(f"incident:{site_id}:current"),
                    site_id,
                    DYNAMIC_PUBLICATION_ID,
                    "complete_site_outage",
                    "serious",
                    reference_time - timedelta(hours=3),
                    None,
                    "All six demo connectors report out_of_service in the current bucket.",
                    "demo-rule-1",
                )
            )
    cursor.executemany(
        """
        INSERT INTO reliability_metrics (
          id, scope_type, scope_id, window_days, computed_at, uptime, observable_share,
          outage_count, median_outage_minutes, mttr_minutes, sample_size
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        metric_rows,
    )
    cursor.executemany(
        """
        INSERT INTO detected_incidents (
          id, site_id, publication_id, incident_type, severity, detected_at,
          recovered_at, explanation, rule_version
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        incident_rows,
    )
    cursor.execute(
        """
        INSERT INTO feed_health_observations (
          id, publication_id, observed_at, status, latency_seconds, message
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            stable_id(f"feed-health:{reference_time.isoformat()}"),
            DYNAMIC_PUBLICATION_ID,
            reference_time,
            "healthy",
            8.0,
            "Deterministic local generator completed.",
        ),
    )


def _manifest_payload(seed: int, reference_time: datetime) -> bytes:
    return json.dumps(
        {
            "schema": "ladepulse-demo-1.0",
            "data_mode": DATA_MODE,
            "seed": seed,
            "reference_time": reference_time.isoformat(),
            "sites": SITE_COUNT,
            "evses": SITE_COUNT * EVSE_PER_SITE,
            "connectors": SITE_COUNT * EVSE_PER_SITE * CONNECTORS_PER_EVSE,
            "notice": "Synthetic demonstration data. Not a live or official source.",
        },
        sort_keys=True,
    ).encode()


def _store_payload(
    cursor: psycopg.Cursor[Any],
    payload: bytes,
    reference_time: datetime,
) -> None:
    payload_hash = hashlib.sha256(payload).hexdigest()
    cursor.execute(
        """
        INSERT INTO raw_payload_envelopes (
          id, publication_id, received_at, source_observed_at, payload_hash,
          etag, last_modified, content_type, schema_version, publication_mode,
          object_key, retained, retention_reason
        ) VALUES (%s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, TRUE, %s)
        """,
        (
            stable_id(f"payload:{payload_hash}"),
            STATIC_PUBLICATION_ID,
            reference_time,
            reference_time,
            payload_hash,
            reference_time,
            "application/json",
            "ladepulse-demo-1.0",
            "full",
            f"synthetic/{payload_hash}.json",
            "Synthetic demo licence explicitly permits raw retention.",
        ),
    )


def _upload_payload(payload: bytes) -> None:
    settings = get_settings()
    if not settings.raw_payload_retention_enabled:
        return
    payload_hash = hashlib.sha256(payload).hexdigest()
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=f"synthetic/{payload_hash}.json",
        Body=payload,
        ContentType="application/json",
        Metadata={"data-mode": DATA_MODE},
    )


def _state_for(
    connector: DemoConnector,
    bucket_index: int,
    bucket: datetime,
) -> str:
    if connector.site_index % 113 == 0 and bucket_index >= BUCKET_COUNT - 19:
        return "out_of_service"
    if connector.site_index % 127 == 0 and BUCKET_COUNT - 13 <= bucket_index < BUCKET_COUNT - 6:
        return "out_of_service"
    if (connector.index * 17 + bucket_index * 3) % 149 < 3:
        return "out_of_service"
    normal = _normal_utilization(bucket)
    wave = 0.08 * math.sin((bucket_index + connector.site_index % 9) / 7)
    target = max(0.05, min(0.88, normal + wave))
    sample = ((connector.index * 73 + bucket_index * 37) % 1000) / 1000
    return "in_use" if sample < target else "available"


def _normal_utilization(bucket: datetime) -> float:
    hour = bucket.hour + bucket.minute / 60
    morning = math.exp(-((hour - 8.0) ** 2) / 7)
    afternoon = math.exp(-((hour - 17.0) ** 2) / 10)
    return min(0.78, 0.18 + 0.18 * morning + 0.30 * afternoon)


def _is_stale_gap(site_index: int, bucket_index: int) -> bool:
    return site_index % 41 == 0 and bucket_index >= BUCKET_COUNT - 5


def _empty_counts() -> dict[str, int]:
    return {
        "available": 0,
        "in_use": 0,
        "out_of_service": 0,
        "unknown": 0,
        "stale_unknown": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic LadePulse demo data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Replace only the synthetic demo source and derived demo snapshots.",
    )
    args = parser.parse_args()
    seed_demo(reset=args.reset)


if __name__ == "__main__":
    main()
