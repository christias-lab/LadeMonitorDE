from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from ladepulse_api.main import app
from ladepulse_core.db import engine
from sqlalchemy import text

REFERENCE_TIME = "2026-07-29T12:00:00Z"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_seeded_api_contract_end_to_end() -> None:
    async with engine.connect() as connection:
        counts = (
            (
                await connection.execute(
                    text(
                        """
                    SELECT
                      (SELECT count(*) FROM charging_sites
                       WHERE data_mode = 'synthetic_demo') AS sites,
                      (SELECT count(*) FROM connectors c
                       JOIN evses e ON e.id = c.evse_id
                       JOIN charging_stations st ON st.id = e.station_id
                       JOIN charging_sites s ON s.id = st.site_id
                       WHERE s.data_mode = 'synthetic_demo') AS connectors,
                      (SELECT count(*) FROM national_snapshots
                       WHERE data_mode = 'synthetic_demo') AS snapshots,
                      (SELECT count(*) FROM raw_payload_envelopes r
                       JOIN source_publications p ON p.id = r.publication_id
                       JOIN data_sources ds ON ds.id = p.data_source_id
                       WHERE ds.data_mode = 'synthetic_demo') AS payloads
                    """
                    )
                )
            )
            .mappings()
            .one()
        )
    assert dict(counts) == {
        "sites": 512,
        "connectors": 3072,
        "snapshots": 289,
        "payloads": 1,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        meta = (await client.get("/v1/meta")).raise_for_status().json()
        assert meta["data_mode"] == "synthetic_demo"
        assert "not live" in meta["synthetic_notice"]

        pulse = (
            (await client.get("/v1/pulse", params={"at": REFERENCE_TIME})).raise_for_status().json()
        )
        assert pulse["coverage"]["inventory_connectors"] == 3072
        assert pulse["pressure"]["score"] in range(101)

        clustered = (
            (
                await client.get(
                    "/v1/map",
                    params={
                        "west": 5.8,
                        "south": 47.1,
                        "east": 15.2,
                        "north": 55.1,
                        "zoom": 6,
                        "at": REFERENCE_TIME,
                    },
                )
            )
            .raise_for_status()
            .json()
        )
        assert clustered["clustered"]
        assert len(clustered["features"]) <= clustered["feature_limit"] == 500

        sites = (
            (
                await client.get(
                    "/v1/map",
                    params={
                        "west": 5.8,
                        "south": 47.1,
                        "east": 15.2,
                        "north": 55.1,
                        "zoom": 12,
                        "at": REFERENCE_TIME,
                        "power_class": "hpc",
                    },
                )
            )
            .raise_for_status()
            .json()
        )
        site_id = sites["features"][0]["site_id"]
        UUID(site_id)

        detail = (
            (
                await client.get(
                    f"/v1/stations/{site_id}",
                    params={"at": REFERENCE_TIME},
                )
            )
            .raise_for_status()
            .json()
        )
        assert detail["site_id"] == site_id
        assert len(detail["connectors"]) > 0
        assert len(detail["nearby_alternatives"]) <= 3

        history = (
            (
                await client.get(
                    f"/v1/stations/{site_id}/history",
                    params={
                        "from": "2026-07-28T12:00:00Z",
                        "to": REFERENCE_TIME,
                    },
                )
            )
            .raise_for_status()
            .json()
        )
        assert history["bucket_minutes"] == 10
        assert len(history["points"]) == 145

        invalid_bbox = await client.get(
            "/v1/map",
            params={
                "west": 15,
                "south": 47,
                "east": 6,
                "north": 55,
                "zoom": 8,
            },
        )
        assert invalid_bbox.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_official_static_mode_never_claims_live_availability() -> None:
    async with engine.connect() as connection:
        has_static_import = await connection.scalar(
            text(
                """
                SELECT EXISTS(
                  SELECT 1 FROM national_snapshots
                  WHERE data_mode = 'live_partial'
                )
                """
            )
        )
    if not has_static_import:
        pytest.skip("official static register has not been imported")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        meta = (
            (await client.get("/v1/meta", params={"data_mode": "live_partial"}))
            .raise_for_status()
            .json()
        )
        assert meta["reference_time"].startswith("2026-07-28")
        assert "availability is unknown" in meta["synthetic_notice"]

        pulse = (
            (
                await client.get(
                    "/v1/pulse",
                    params={
                        "data_mode": "live_partial",
                        "at": "2026-07-28T00:00:00Z",
                    },
                )
            )
            .raise_for_status()
            .json()
        )
        assert pulse["coverage"]["inventory_connectors"] == 207225
        assert pulse["coverage"]["reported_connectors"] == 0
        assert pulse["stale_unknown"] == 207225
        assert pulse["utilization"] is None

        mapped = (
            (
                await client.get(
                    "/v1/map",
                    params={
                        "data_mode": "live_partial",
                        "west": 5.5,
                        "south": 47,
                        "east": 15.5,
                        "north": 55.3,
                        "zoom": 5.4,
                        "at": "2026-07-28T00:00:00Z",
                    },
                )
            )
            .raise_for_status()
            .json()
        )
        assert mapped["clustered"]
        assert mapped["features"]
        assert len(mapped["features"]) <= 500
        assert all(
            feature["states"]["stale_unknown"] == feature["connector_count"]
            for feature in mapped["features"]
        )
