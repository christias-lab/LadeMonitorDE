from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import redis.asyncio as redis
import structlog
from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from ladepulse_core.config import get_settings
from ladepulse_core.db import engine, get_session
from ladepulse_core.metrics import floor_to_ten_minutes
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ladepulse_api.repository import (
    data_notice,
    fetch_map_sites,
    fetch_pulse,
    fetch_station,
    fetch_station_history,
)
from ladepulse_api.schemas import (
    DataMode,
    MapResponse,
    MetadataResponse,
    PulseResponse,
    StationDetailResponse,
    StationHistoryResponse,
)

settings = get_settings()
logger = structlog.get_logger()

app = FastAPI(
    title="LadePulse DE API",
    version="0.1.0",
    description="Normalized observability APIs for public EV charging infrastructure.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        path=request.url.path,
    )
    response = await call_next(request)
    response.headers["x-correlation-id"] = correlation_id
    logger.info("request_completed", status_code=response.status_code)
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    redis_client = redis.from_url(settings.redis_url)
    try:
        await redis_client.ping()
    finally:
        await redis_client.aclose()
    return {"status": "ready"}


@app.get("/v1/meta", response_model=MetadataResponse)
async def metadata(
    data_mode: DataMode = "synthetic_demo",
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    reference_time = await session.scalar(
        text(
            """
            SELECT MAX(bucket_start)
            FROM national_snapshots
            WHERE data_mode = :data_mode
            """
        ),
        {"data_mode": data_mode},
    )
    if reference_time is None:
        reference_time = settings.demo_reference_time
    return {
        "product": "LadePulse DE",
        "tagline": (
            "Official public charging inventory for Germany."
            if data_mode == "live_partial"
            else "The health monitor of Germany's public EV charging network."
        ),
        "api_version": "0.1.0",
        "data_mode": data_mode,
        "synthetic_notice": data_notice(data_mode),
        "reference_time": reference_time,
        "map_style_url": settings.map_style_url,
        "methodology_url": "/docs/metrics",
    }


@app.get("/v1/pulse", response_model=PulseResponse)
async def pulse(
    at: datetime | None = None,
    data_mode: DataMode = "synthetic_demo",
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    requested_at = _requested_at(at)
    return await fetch_pulse(session, requested_at, data_mode)


@app.get("/v1/map", response_model=MapResponse)
async def map_features(
    west: float = Query(ge=-180, le=180),
    south: float = Query(ge=-90, le=90),
    east: float = Query(ge=-180, le=180),
    north: float = Query(ge=-90, le=90),
    zoom: float = Query(ge=3, le=18),
    at: datetime | None = None,
    bundesland: str | None = None,
    power_class: str | None = Query(default=None, pattern="^(ac|dc|hpc)$"),
    available_now: bool = False,
    freshness: str | None = Query(default=None, pattern="^(fresh|stale)$"),
    data_mode: DataMode = "synthetic_demo",
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return await fetch_map_sites(
        session,
        west=west,
        south=south,
        east=east,
        north=north,
        zoom=zoom,
        requested_at=_requested_at(at),
        bundesland=bundesland,
        power_class=power_class,
        available_now=available_now,
        freshness=freshness,
        data_mode=data_mode,
    )


@app.get("/v1/stations/{site_id}", response_model=StationDetailResponse)
async def station_detail(
    site_id: uuid.UUID,
    at: datetime | None = None,
    data_mode: DataMode = "synthetic_demo",
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    return await fetch_station(session, site_id, _requested_at(at), data_mode)


@app.get("/v1/stations/{site_id}/history", response_model=StationHistoryResponse)
async def station_history(
    site_id: uuid.UUID,
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    data_mode: DataMode = "synthetic_demo",
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    end = _requested_at(to_time)
    start = _aware_utc(from_time) if from_time else end - timedelta(hours=24)
    return await fetch_station_history(session, site_id, start, end, data_mode)


def _requested_at(value: datetime | None) -> datetime:
    return floor_to_ten_minutes(_aware_utc(value) if value else settings.demo_reference_time)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
