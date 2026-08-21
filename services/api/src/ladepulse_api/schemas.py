from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

DataMode = Literal["synthetic_demo", "live_partial", "live_verified"]


class Coverage(BaseModel):
    inventory_connectors: int
    reported_connectors: int
    fresh_connectors: int
    live_coverage: float


class PressureComponents(BaseModel):
    utilization: float
    offline_share: float
    deviation: float
    alternatives_gap: float
    confidence: float
    raw_pressure: float
    score: int
    sufficient_confidence: bool
    weights: dict[str, float]


class PulseResponse(BaseModel):
    data_mode: DataMode
    synthetic_notice: str
    bucket_start: datetime
    source_observed_at: datetime
    generated_at: datetime
    available: int
    in_use: int
    out_of_service: int
    stale_unknown: int
    hpc_available: int
    utilization: float | None
    normal_utilization: float | None
    utilization_deviation: float | None
    coverage: Coverage
    pressure: PressureComponents | None
    serious_incidents: int
    recovered_last_hour: int


class StateCounts(BaseModel):
    available: int
    in_use: int
    out_of_service: int
    stale_unknown: int


class MapFeature(BaseModel):
    kind: Literal["cluster", "site"]
    id: str
    site_id: UUID | None = None
    name: str
    bundesland: str | None
    latitude: float
    longitude: float
    site_count: int
    connector_count: int
    states: StateCounts
    utilization: float | None
    offline_share: float | None
    confidence: float
    max_power_kw: float
    new_serious_outage: bool


class MapResponse(BaseModel):
    data_mode: DataMode
    synthetic_notice: str
    requested_at: datetime
    bbox: list[float] = Field(min_length=4, max_length=4)
    zoom: float
    clustered: bool
    truncated: bool
    feature_limit: int
    features: list[MapFeature]


class ConnectorDetail(BaseModel):
    connector_id: UUID
    external_id: str
    evse_external_id: str
    connector_type: str
    max_power_kw: float
    current_type: str
    physical_state: str
    effective_state: str
    source_observed_at: datetime | None
    ingested_at: datetime | None
    data_age_seconds: int | None
    price_eur_per_kwh: float | None


class AlternativeSite(BaseModel):
    site_id: UUID
    name: str
    distance_km_straight_line: float
    max_power_kw: float
    reliability_score: float | None


class ReliabilitySummary(BaseModel):
    window_days: int
    uptime: float | None
    observable_share: float
    outage_count: int
    median_outage_minutes: float | None
    mttr_minutes: float | None
    sample_size: int


class StationDetailResponse(BaseModel):
    data_mode: DataMode
    synthetic_notice: str
    site_id: UUID
    external_id: str
    name: str
    address: str | None
    bundesland: str
    latitude: float
    longitude: float
    corridor: bool
    operator_name: str
    requested_at: datetime
    connectors: list[ConnectorDetail]
    reliability: ReliabilitySummary
    nearby_alternatives: list[AlternativeSite]
    source_name: str
    publication_name: str
    licence_code: str
    licence_url: str | None
    attribution: str | None


class HistoryPoint(BaseModel):
    bucket_start: datetime
    states: StateCounts
    utilization: float | None
    observable_connectors: int


class StationHistoryResponse(BaseModel):
    data_mode: DataMode
    synthetic_notice: str
    site_id: UUID
    from_time: datetime
    to_time: datetime
    bucket_minutes: int
    points: list[HistoryPoint]


class MetadataResponse(BaseModel):
    product: str
    tagline: str
    api_version: str
    data_mode: DataMode
    synthetic_notice: str
    reference_time: datetime
    map_style_url: str
    methodology_url: str
