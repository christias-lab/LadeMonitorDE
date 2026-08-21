from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from ladepulse_core.metrics import ConnectorState, effective_state, floor_to_ten_minutes
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

SYNTHETIC_NOTICE = "Deterministic demonstration data — not live charging data."
LIVE_PARTIAL_NOTICE = (
    "Official Bundesnetzagentur static register — availability is unknown; "
    "no live status feed is connected."
)
FEATURE_LIMIT = 500


def data_notice(data_mode: str) -> str:
    return LIVE_PARTIAL_NOTICE if data_mode == "live_partial" else SYNTHETIC_NOTICE


async def fetch_pulse(
    session: AsyncSession, requested_at: datetime, data_mode: str
) -> dict[str, Any]:
    result = await session.execute(
        text(
            """
            SELECT *
            FROM national_snapshots
            WHERE data_mode = :data_mode AND bucket_start <= :requested_at
            ORDER BY bucket_start DESC
            LIMIT 1
            """
        ),
        {"requested_at": requested_at, "data_mode": data_mode},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="No snapshot exists at or before that time")
    inventory = row["inventory_connectors"]
    coverage = row["fresh_connectors"] / inventory if inventory else 0.0
    return {
        "data_mode": row["data_mode"],
        "synthetic_notice": data_notice(data_mode),
        "bucket_start": row["bucket_start"],
        "source_observed_at": row["source_observed_at"],
        "generated_at": row["generated_at"],
        "available": row["available"],
        "in_use": row["in_use"],
        "out_of_service": row["out_of_service"],
        "stale_unknown": row["stale_unknown"],
        "hpc_available": row["hpc_available"],
        "utilization": row["utilization"],
        "normal_utilization": row["normal_utilization"],
        "utilization_deviation": (
            None
            if row["utilization"] is None or row["normal_utilization"] is None
            else row["utilization"] - row["normal_utilization"]
        ),
        "coverage": {
            "inventory_connectors": inventory,
            "reported_connectors": row["reported_connectors"],
            "fresh_connectors": row["fresh_connectors"],
            "live_coverage": coverage,
        },
        "pressure": row["pressure_components"],
        "serious_incidents": row["serious_incidents"],
        "recovered_last_hour": row["recovered_last_hour"],
    }


async def fetch_map_sites(
    session: AsyncSession,
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    zoom: float,
    requested_at: datetime,
    bundesland: str | None,
    power_class: str | None,
    available_now: bool,
    freshness: str | None,
    data_mode: str,
) -> dict[str, Any]:
    if west >= east or south >= north:
        raise HTTPException(status_code=422, detail="Invalid bounding box ordering")
    if not (-180 <= west <= 180 and -180 <= east <= 180):
        raise HTTPException(status_code=422, detail="Longitude outside valid range")
    if not (-90 <= south <= 90 and -90 <= north <= 90):
        raise HTTPException(status_code=422, detail="Latitude outside valid range")
    if data_mode == "live_partial":
        return await _fetch_static_map_sites(
            session,
            west=west,
            south=south,
            east=east,
            north=north,
            zoom=zoom,
            requested_at=requested_at,
            bundesland=bundesland,
            power_class=power_class,
            available_now=available_now,
            freshness=freshness,
        )

    power_predicate = ""
    if power_class == "ac":
        power_predicate = "AND c.max_power_kw <= 22"
    elif power_class == "dc":
        power_predicate = "AND c.max_power_kw > 22 AND c.max_power_kw < 150"
    elif power_class == "hpc":
        power_predicate = "AND c.max_power_kw >= 150"

    query = text(
        f"""
        WITH selected_connectors AS (
          SELECT
            s.id AS site_id, s.name, s.bundesland, s.latitude, s.longitude,
            c.id AS connector_id, c.max_power_kw,
            obs.state AS physical_state,
            obs.source_observed_at,
            obs.stale_after_seconds
          FROM charging_sites s
          JOIN charging_stations st ON st.site_id = s.id
          JOIN evses e ON e.station_id = st.id
          JOIN connectors c ON c.evse_id = e.id
          LEFT JOIN LATERAL (
            SELECT so.state, so.source_observed_at, p.stale_after_seconds
            FROM status_observations so
            JOIN source_publications p ON p.id = so.publication_id
            WHERE so.connector_id = c.id
              AND so.source_observed_at <= :requested_at
            ORDER BY so.source_observed_at DESC
            LIMIT 1
          ) obs ON TRUE
          WHERE s.data_mode = :data_mode
            AND s.longitude BETWEEN :west AND :east
            AND s.latitude BETWEEN :south AND :north
            AND (
              CAST(:bundesland AS text) IS NULL
              OR s.bundesland = CAST(:bundesland AS text)
            )
            {power_predicate}
        ),
        effective AS (
          SELECT *,
            CASE
              WHEN source_observed_at IS NULL
                OR :requested_at - source_observed_at
                   > make_interval(secs => stale_after_seconds)
                THEN 'stale_unknown'
              ELSE physical_state
            END AS effective_state
          FROM selected_connectors
        )
        SELECT
          site_id, name, bundesland, latitude, longitude,
          COUNT(*)::int AS connector_count,
          MAX(max_power_kw) AS max_power_kw,
          COUNT(*) FILTER (WHERE effective_state = 'available')::int AS available,
          COUNT(*) FILTER (WHERE effective_state = 'in_use')::int AS in_use,
          COUNT(*) FILTER (WHERE effective_state = 'out_of_service')::int AS out_of_service,
          COUNT(*) FILTER (WHERE effective_state IN ('stale_unknown', 'unknown'))::int
            AS stale_unknown,
          MAX(source_observed_at) AS newest_observation
        FROM effective
        GROUP BY site_id, name, bundesland, latitude, longitude
        ORDER BY site_id
        """
    )
    result = await session.execute(
        query,
        {
            "requested_at": requested_at,
            "west": west,
            "east": east,
            "south": south,
            "north": north,
            "bundesland": bundesland,
            "data_mode": data_mode,
        },
    )
    sites = [_site_row(row) for row in result.mappings()]
    if available_now:
        sites = [site for site in sites if site["available"] > 0]
    if freshness == "fresh":
        sites = [site for site in sites if site["stale_unknown"] == 0]
    elif freshness == "stale":
        sites = [site for site in sites if site["stale_unknown"] > 0]

    clustered = zoom < 9 or len(sites) > FEATURE_LIMIT
    features = _cluster_sites(sites, zoom) if clustered else [_site_feature(s) for s in sites]
    truncated = len(features) > FEATURE_LIMIT
    features = features[:FEATURE_LIMIT]
    return {
        "data_mode": data_mode,
        "synthetic_notice": data_notice(data_mode),
        "requested_at": requested_at,
        "bbox": [west, south, east, north],
        "zoom": zoom,
        "clustered": clustered,
        "truncated": truncated,
        "feature_limit": FEATURE_LIMIT,
        "features": features,
    }


async def _fetch_static_map_sites(
    session: AsyncSession,
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    zoom: float,
    requested_at: datetime,
    bundesland: str | None,
    power_class: str | None,
    available_now: bool,
    freshness: str | None,
) -> dict[str, Any]:
    # The register contains inventory, not status. Filters that require a fresh
    # availability observation must therefore return no matches.
    if available_now or freshness == "fresh":
        features: list[dict[str, Any]] = []
        clustered = zoom < 10
        truncated = False
    else:
        power_predicate = ""
        if power_class == "ac":
            power_predicate = "AND c.max_power_kw <= 22"
        elif power_class == "dc":
            power_predicate = "AND c.max_power_kw > 22 AND c.max_power_kw < 150"
        elif power_class == "hpc":
            power_predicate = "AND c.max_power_kw >= 150"
        parameters = {
            "west": west,
            "south": south,
            "east": east,
            "north": north,
            "bundesland": bundesland,
            "limit": FEATURE_LIMIT + 1,
        }
        site_rollup = f"""
          SELECT s.id AS site_id, s.name, s.bundesland, s.latitude, s.longitude,
                 COUNT(c.id)::int AS connector_count,
                 MAX(c.max_power_kw) AS max_power_kw
          FROM charging_sites s
          JOIN charging_stations st ON st.site_id = s.id
          JOIN evses e ON e.station_id = st.id
          JOIN connectors c ON c.evse_id = e.id
          WHERE s.data_mode = 'live_partial'
            AND s.longitude BETWEEN :west AND :east
            AND s.latitude BETWEEN :south AND :north
            AND (
              CAST(:bundesland AS text) IS NULL
              OR s.bundesland = CAST(:bundesland AS text)
            )
            {power_predicate}
          GROUP BY s.id, s.name, s.bundesland, s.latitude, s.longitude
        """
        if zoom >= 10:
            result = await session.execute(
                text(
                    f"""
                    WITH site_rollup AS ({site_rollup})
                    SELECT * FROM site_rollup
                    ORDER BY site_id
                    LIMIT :limit
                    """
                ),
                parameters,
            )
            rows = [dict(row) for row in result.mappings()]
            truncated = len(rows) > FEATURE_LIMIT
            features = [
                _site_feature(
                    {
                        **row,
                        "available": 0,
                        "in_use": 0,
                        "out_of_service": 0,
                        "stale_unknown": row["connector_count"],
                    }
                )
                for row in rows[:FEATURE_LIMIT]
            ]
            clustered = False
        else:
            grid = max((east - west) / 24, (north - south) / 18, 0.002)
            parameters["grid"] = grid
            result = await session.execute(
                text(
                    f"""
                    WITH site_rollup AS ({site_rollup}),
                    cells AS (
                      SELECT
                        FLOOR(longitude / :grid)::int AS grid_x,
                        FLOOR(latitude / :grid)::int AS grid_y,
                        COUNT(*)::int AS site_count,
                        SUM(connector_count)::int AS connector_count,
                        AVG(latitude) AS latitude,
                        AVG(longitude) AS longitude,
                        MAX(max_power_kw) AS max_power_kw,
                        CASE WHEN COUNT(DISTINCT bundesland) = 1
                             THEN MIN(bundesland) END AS bundesland
                      FROM site_rollup
                      GROUP BY grid_x, grid_y
                    )
                    SELECT * FROM cells
                    ORDER BY grid_x, grid_y
                    LIMIT :limit
                    """
                ),
                parameters,
            )
            rows = [dict(row) for row in result.mappings()]
            truncated = len(rows) > FEATURE_LIMIT
            features = [
                {
                    "kind": "cluster",
                    "id": f"static-{zoom:.1f}-{row['grid_x']}-{row['grid_y']}",
                    "site_id": None,
                    "name": f"{row['site_count']} locations",
                    "bundesland": row["bundesland"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "site_count": row["site_count"],
                    "connector_count": row["connector_count"],
                    "states": {
                        "available": 0,
                        "in_use": 0,
                        "out_of_service": 0,
                        "stale_unknown": row["connector_count"],
                    },
                    "utilization": None,
                    "offline_share": None,
                    "confidence": 0.0,
                    "max_power_kw": row["max_power_kw"],
                    "new_serious_outage": False,
                }
                for row in rows[:FEATURE_LIMIT]
            ]
            clustered = True
    return {
        "data_mode": "live_partial",
        "synthetic_notice": LIVE_PARTIAL_NOTICE,
        "requested_at": requested_at,
        "bbox": [west, south, east, north],
        "zoom": zoom,
        "clustered": clustered,
        "truncated": truncated,
        "feature_limit": FEATURE_LIMIT,
        "features": features,
    }


async def fetch_station(
    session: AsyncSession,
    site_id: UUID,
    requested_at: datetime,
    data_mode: str,
) -> dict[str, Any]:
    site_result = await session.execute(
        text(
            """
            SELECT s.*, o.name AS operator_name, ds.name AS source_name,
                   p.name AS publication_name,
                   dl.code AS licence_code, dl.url AS licence_url, dl.attribution
            FROM charging_sites s
            JOIN operators o ON o.id = s.operator_id
            JOIN source_publications p ON p.id = s.publication_id
            JOIN data_sources ds ON ds.id = p.data_source_id
            JOIN data_licences dl ON dl.id = p.licence_id
            WHERE s.id = :site_id AND s.data_mode = :data_mode
            """
        ),
        {"site_id": site_id, "data_mode": data_mode},
    )
    site = site_result.mappings().one_or_none()
    if site is None:
        raise HTTPException(status_code=404, detail="Station not found")

    connector_result = await session.execute(
        text(
            """
            SELECT c.id AS connector_id, c.external_id, e.external_id AS evse_external_id,
                   c.connector_type, c.max_power_kw, e.current_type,
                   obs.state AS physical_state, obs.source_observed_at, obs.ingested_at,
                   obs.stale_after_seconds,
                   price.per_kwh
            FROM charging_stations st
            JOIN evses e ON e.station_id = st.id
            JOIN connectors c ON c.evse_id = e.id
            LEFT JOIN LATERAL (
              SELECT so.state, so.source_observed_at, so.ingested_at,
                     p.stale_after_seconds
              FROM status_observations so
              JOIN source_publications p ON p.id = so.publication_id
              WHERE so.connector_id = c.id AND so.source_observed_at <= :requested_at
              ORDER BY so.source_observed_at DESC LIMIT 1
            ) obs ON TRUE
            LEFT JOIN LATERAL (
              SELECT per_kwh
              FROM price_observations po
              WHERE po.connector_id = c.id AND po.source_observed_at <= :requested_at
              ORDER BY po.source_observed_at DESC LIMIT 1
            ) price ON TRUE
            WHERE st.site_id = :site_id
            ORDER BY e.external_id, c.external_id
            """
        ),
        {"site_id": site_id, "requested_at": requested_at},
    )
    connectors = []
    for row in connector_result.mappings():
        source_at = row["source_observed_at"]
        physical = row["physical_state"] or "unknown"
        effective = (
            "stale_unknown"
            if source_at is None
            else effective_state(
                ConnectorState(physical),
                source_at,
                requested_at,
                timedelta(seconds=row["stale_after_seconds"]),
            ).value
        )
        age = None if source_at is None else max(0, int((requested_at - source_at).total_seconds()))
        connectors.append(
            {
                **dict(row),
                "physical_state": physical,
                "effective_state": effective,
                "data_age_seconds": age,
                "price_eur_per_kwh": (None if row["per_kwh"] is None else float(row["per_kwh"])),
            }
        )

    reliability_result = await session.execute(
        text(
            """
            SELECT window_days, uptime, observable_share, outage_count,
                   median_outage_minutes, mttr_minutes, sample_size
            FROM reliability_metrics
            WHERE scope_type = 'site' AND scope_id = :site_id
            ORDER BY window_days ASC LIMIT 1
            """
        ),
        {"site_id": site_id},
    )
    reliability = reliability_result.mappings().one_or_none() or {
        "window_days": 7,
        "uptime": None,
        "observable_share": 0.0,
        "outage_count": 0,
        "median_outage_minutes": None,
        "mttr_minutes": None,
        "sample_size": 0,
    }
    alternatives_result = await session.execute(
        text(
            """
            SELECT candidate.id AS site_id, candidate.name,
                   ST_Distance(candidate.geom::geography, origin.geom::geography) / 1000.0
                     AS distance_km,
                   MAX(c.max_power_kw) AS max_power_kw,
                   COALESCE(MAX(rm.uptime), 0.90) AS reliability
            FROM charging_sites origin
            JOIN charging_sites candidate ON candidate.id <> origin.id
            JOIN charging_stations st ON st.site_id = candidate.id
            JOIN evses e ON e.station_id = st.id
            JOIN connectors c ON c.evse_id = e.id
            LEFT JOIN reliability_metrics rm
              ON rm.scope_type = 'site' AND rm.scope_id = candidate.id
            WHERE origin.id = :site_id
              AND candidate.data_mode = :data_mode
              AND ST_DWithin(candidate.geom::geography, origin.geom::geography, 75000)
            GROUP BY candidate.id, candidate.name, candidate.geom, origin.geom
            ORDER BY distance_km
            LIMIT 3
            """
        ),
        {"site_id": site_id, "data_mode": data_mode},
    )
    alternatives = [
        {
            "site_id": row["site_id"],
            "name": row["name"],
            "distance_km_straight_line": round(row["distance_km"], 1),
            "max_power_kw": row["max_power_kw"],
            "reliability_score": (
                None if data_mode == "live_partial" else round(float(row["reliability"]) * 100, 1)
            ),
        }
        for row in alternatives_result.mappings()
    ]
    return {
        "data_mode": data_mode,
        "synthetic_notice": data_notice(data_mode),
        "site_id": site["id"],
        "external_id": site["external_id"],
        "name": site["name"],
        "address": site["address"],
        "bundesland": site["bundesland"],
        "latitude": site["latitude"],
        "longitude": site["longitude"],
        "corridor": site["corridor"],
        "operator_name": site["operator_name"],
        "requested_at": requested_at,
        "connectors": connectors,
        "reliability": dict(reliability),
        "nearby_alternatives": alternatives,
        "source_name": site["source_name"],
        "publication_name": site["publication_name"],
        "licence_code": site["licence_code"],
        "licence_url": site["licence_url"],
        "attribution": site["attribution"],
    }


async def fetch_station_history(
    session: AsyncSession,
    site_id: UUID,
    from_time: datetime,
    to_time: datetime,
    data_mode: str,
) -> dict[str, Any]:
    exists = await session.scalar(
        text(
            """
            SELECT EXISTS(
              SELECT 1 FROM charging_sites
              WHERE id = :site_id AND data_mode = :data_mode
            )
            """
        ),
        {"site_id": site_id, "data_mode": data_mode},
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Station not found")
    if to_time <= from_time or to_time - from_time > timedelta(days=7):
        raise HTTPException(
            status_code=422, detail="History range must be positive and at most 7 days"
        )

    rows_result = await session.execute(
        text(
            """
            SELECT c.id AS connector_id, p.stale_after_seconds,
                   so.source_observed_at, so.state
            FROM charging_stations st
            JOIN evses e ON e.station_id = st.id
            JOIN connectors c ON c.evse_id = e.id
            LEFT JOIN status_observations so
              ON so.connector_id = c.id
             AND so.source_observed_at BETWEEN :lookback AND :to_time
            LEFT JOIN source_publications p ON p.id = so.publication_id
            WHERE st.site_id = :site_id
            ORDER BY so.source_observed_at, c.id
            """
        ),
        {
            "site_id": site_id,
            "lookback": from_time - timedelta(hours=1),
            "to_time": to_time,
        },
    )
    observations: dict[UUID, list[tuple[datetime, str, int]]] = defaultdict(list)
    connector_ids: set[UUID] = set()
    for row in rows_result.mappings():
        connector_ids.add(row["connector_id"])
        if row["source_observed_at"] is not None:
            observations[row["connector_id"]].append(
                (row["source_observed_at"], row["state"], row["stale_after_seconds"])
            )

    cursors = {connector_id: 0 for connector_id in connector_ids}
    latest: dict[UUID, tuple[datetime, str, int]] = {}
    points = []
    bucket = floor_to_ten_minutes(from_time)
    to_bucket = floor_to_ten_minutes(to_time)
    while bucket <= to_bucket:
        counts = {"available": 0, "in_use": 0, "out_of_service": 0, "stale_unknown": 0}
        for connector_id in connector_ids:
            entries = observations[connector_id]
            cursor = cursors[connector_id]
            while cursor < len(entries) and entries[cursor][0] <= bucket:
                latest[connector_id] = entries[cursor]
                cursor += 1
            cursors[connector_id] = cursor
            current = latest.get(connector_id)
            if current is None or bucket - current[0] > timedelta(seconds=current[2]):
                counts["stale_unknown"] += 1
            elif current[1] in counts:
                counts[current[1]] += 1
            else:
                counts["stale_unknown"] += 1
        denominator = counts["available"] + counts["in_use"]
        points.append(
            {
                "bucket_start": bucket,
                "states": counts,
                "utilization": counts["in_use"] / denominator if denominator else None,
                "observable_connectors": sum(counts.values()) - counts["stale_unknown"],
            }
        )
        bucket += timedelta(minutes=10)
    return {
        "data_mode": data_mode,
        "synthetic_notice": data_notice(data_mode),
        "site_id": site_id,
        "from_time": floor_to_ten_minutes(from_time),
        "to_time": to_bucket,
        "bucket_minutes": 10,
        "points": points,
    }


def _site_row(row: Any) -> dict[str, Any]:
    return dict(row)


def _site_feature(site: dict[str, Any]) -> dict[str, Any]:
    known = site["available"] + site["in_use"]
    observable = known + site["out_of_service"]
    return {
        "kind": "site",
        "id": str(site["site_id"]),
        "site_id": site["site_id"],
        "name": site["name"],
        "bundesland": site["bundesland"],
        "latitude": site["latitude"],
        "longitude": site["longitude"],
        "site_count": 1,
        "connector_count": site["connector_count"],
        "states": {
            "available": site["available"],
            "in_use": site["in_use"],
            "out_of_service": site["out_of_service"],
            "stale_unknown": site["stale_unknown"],
        },
        "utilization": site["in_use"] / known if known else None,
        "offline_share": site["out_of_service"] / observable if observable else None,
        "confidence": observable / site["connector_count"] if site["connector_count"] else 0.0,
        "max_power_kw": site["max_power_kw"],
        "new_serious_outage": (
            site["out_of_service"] == site["connector_count"] and site["connector_count"] > 0
        ),
    }


def _cluster_sites(sites: list[dict[str, Any]], zoom: float) -> list[dict[str, Any]]:
    grid = 2.0 if zoom <= 5 else 1.0 if zoom <= 6 else 0.5 if zoom <= 7 else 0.2
    groups: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for site in sites:
        groups[(math.floor(site["longitude"] / grid), math.floor(site["latitude"] / grid))].append(
            site
        )
    features = []
    for key, members in sorted(groups.items()):
        if len(members) == 1:
            features.append(_site_feature(members[0]))
            continue
        counts = {
            name: sum(member[name] for member in members)
            for name in ("available", "in_use", "out_of_service", "stale_unknown")
        }
        connector_count = sum(member["connector_count"] for member in members)
        known = counts["available"] + counts["in_use"]
        observable = known + counts["out_of_service"]
        features.append(
            {
                "kind": "cluster",
                "id": f"cluster-{zoom:.1f}-{key[0]}-{key[1]}",
                "site_id": None,
                "name": f"{len(members)} locations",
                "bundesland": (
                    members[0]["bundesland"]
                    if all(m["bundesland"] == members[0]["bundesland"] for m in members)
                    else None
                ),
                "latitude": sum(m["latitude"] for m in members) / len(members),
                "longitude": sum(m["longitude"] for m in members) / len(members),
                "site_count": len(members),
                "connector_count": connector_count,
                "states": counts,
                "utilization": counts["in_use"] / known if known else None,
                "offline_share": counts["out_of_service"] / observable if observable else None,
                "confidence": observable / connector_count if connector_count else 0.0,
                "max_power_kw": max(m["max_power_kw"] for m in members),
                "new_serious_outage": all(
                    m["out_of_service"] == m["connector_count"] for m in members
                ),
            }
        )
    return features
