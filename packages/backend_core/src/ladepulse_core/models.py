from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DataLicence(Base):
    __tablename__ = "data_licences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    raw_storage_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    redistribution_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(50))
    data_mode: Mapped[str] = mapped_column(String(32), index=True)
    base_url: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SourcePublication(Base):
    __tablename__ = "source_publications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="CASCADE"), index=True
    )
    licence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_licences.id"))
    external_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    format: Mapped[str] = mapped_column(String(100))
    schema_version: Mapped[str | None] = mapped_column(String(100))
    delivery_mode: Mapped[str] = mapped_column(String(32))
    publication_type: Mapped[str] = mapped_column(String(32))
    supports_delta: Mapped[bool] = mapped_column(Boolean, default=False)
    update_interval_seconds: Mapped[int] = mapped_column(Integer)
    stale_after_seconds: Mapped[int] = mapped_column(Integer)
    rate_limit_notes: Mapped[str | None] = mapped_column(Text)
    storage_rights_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("data_source_id", "external_id"),)


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="CASCADE")
    )
    external_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), index=True)
    country_code: Mapped[str] = mapped_column(String(2), default="DE")
    __table_args__ = (UniqueConstraint("data_source_id", "external_id"),)


class ChargingSite(Base):
    __tablename__ = "charging_sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_publications.id", ondelete="CASCADE"), index=True
    )
    operator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operators.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500))
    bundesland: Mapped[str] = mapped_column(String(64), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    geom: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326, spatial_index=False))
    corridor: Mapped[bool] = mapped_column(Boolean, default=False)
    data_mode: Mapped[str] = mapped_column(String(32), index=True)
    __table_args__ = (
        UniqueConstraint("publication_id", "external_id"),
        Index("ix_charging_sites_geom", "geom", postgresql_using="gist"),
    )


class ChargingStation(Base):
    __tablename__ = "charging_stations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("charging_sites.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(255))
    __table_args__ = (UniqueConstraint("site_id", "external_id"),)


class EVSE(Base):
    __tablename__ = "evses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    station_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("charging_stations.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    max_power_kw: Mapped[float] = mapped_column(Float)
    current_type: Mapped[str] = mapped_column(String(16))
    __table_args__ = (UniqueConstraint("station_id", "external_id"),)


class Connector(Base):
    __tablename__ = "connectors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    evse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evses.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(255))
    connector_type: Mapped[str] = mapped_column(Text)
    max_power_kw: Mapped[float] = mapped_column(Float)
    __table_args__ = (UniqueConstraint("evse_id", "external_id"),)


class StaticCapability(Base):
    __tablename__ = "static_capabilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connectors.id", ondelete="CASCADE"), index=True
    )
    capability: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)


class StatusObservation(Base):
    __tablename__ = "status_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connectors.id", ondelete="CASCADE"), index=True
    )
    publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_publications.id", ondelete="CASCADE"), index=True
    )
    source_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(32))
    payload_hash: Mapped[str] = mapped_column(String(64))
    sequence_number: Mapped[int] = mapped_column(BigInteger)
    is_delta: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (
        PrimaryKeyConstraint("id", "source_observed_at"),
        UniqueConstraint(
            "publication_id",
            "connector_id",
            "source_observed_at",
            name="uq_status_observation_message",
        ),
        Index(
            "ix_status_connector_observed_desc",
            "connector_id",
            source_observed_at.desc(),
        ),
        {"postgresql_partition_by": "RANGE (source_observed_at)"},
    )


class StatusEvent(Base):
    __tablename__ = "status_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connectors.id", ondelete="CASCADE"), index=True
    )
    from_state: Mapped[str | None] = mapped_column(String(32))
    to_state: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PriceObservation(Base):
    __tablename__ = "price_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connectors.id", ondelete="CASCADE"), index=True
    )
    source_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    currency: Mapped[str] = mapped_column(String(3))
    per_kwh: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    per_minute: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    session_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    blocking_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))


class FeedHealthObservation(Base):
    __tablename__ = "feed_health_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_publications.id", ondelete="CASCADE"), index=True
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32))
    latency_seconds: Mapped[float | None] = mapped_column(Float)
    message: Mapped[str | None] = mapped_column(Text)


class NationalSnapshot(Base):
    __tablename__ = "national_snapshots"

    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    data_mode: Mapped[str] = mapped_column(String(32), primary_key=True)
    available: Mapped[int] = mapped_column(Integer)
    in_use: Mapped[int] = mapped_column(Integer)
    out_of_service: Mapped[int] = mapped_column(Integer)
    stale_unknown: Mapped[int] = mapped_column(Integer)
    inventory_connectors: Mapped[int] = mapped_column(Integer)
    reported_connectors: Mapped[int] = mapped_column(Integer)
    fresh_connectors: Mapped[int] = mapped_column(Integer)
    hpc_available: Mapped[int] = mapped_column(Integer)
    utilization: Mapped[float | None] = mapped_column(Float)
    normal_utilization: Mapped[float | None] = mapped_column(Float)
    pressure_score: Mapped[int | None] = mapped_column(Integer)
    pressure_components: Mapped[dict[str, Any]] = mapped_column(JSON)
    serious_incidents: Mapped[int] = mapped_column(Integer)
    recovered_last_hour: Mapped[int] = mapped_column(Integer)
    source_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RegionSnapshot(Base):
    __tablename__ = "region_snapshots"

    bundesland: Mapped[str] = mapped_column(String(64), primary_key=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    data_mode: Mapped[str] = mapped_column(String(32), primary_key=True)
    available: Mapped[int] = mapped_column(Integer)
    in_use: Mapped[int] = mapped_column(Integer)
    out_of_service: Mapped[int] = mapped_column(Integer)
    stale_unknown: Mapped[int] = mapped_column(Integer)
    inventory_connectors: Mapped[int] = mapped_column(Integer)
    utilization: Mapped[float | None] = mapped_column(Float)
    pressure_score: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)


class DetectedIncident(Base):
    __tablename__ = "detected_incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("charging_sites.id", ondelete="CASCADE"), index=True
    )
    publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_publications.id", ondelete="CASCADE"), index=True
    )
    incident_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(32))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    explanation: Mapped[str] = mapped_column(Text)
    rule_version: Mapped[str] = mapped_column(String(32))


class ReliabilityMetric(Base):
    __tablename__ = "reliability_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(32))
    scope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    window_days: Mapped[int] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    uptime: Mapped[float | None] = mapped_column(Float)
    observable_share: Mapped[float] = mapped_column(Float)
    outage_count: Mapped[int] = mapped_column(Integer)
    median_outage_minutes: Mapped[float | None] = mapped_column(Float)
    mttr_minutes: Mapped[float | None] = mapped_column(Float)
    sample_size: Mapped[int] = mapped_column(Integer)


class RawPayloadEnvelope(Base):
    __tablename__ = "raw_payload_envelopes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    publication_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_publications.id", ondelete="CASCADE"), index=True
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload_hash: Mapped[str] = mapped_column(String(64), unique=True)
    etag: Mapped[str | None] = mapped_column(String(255))
    last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_type: Mapped[str] = mapped_column(String(100))
    schema_version: Mapped[str | None] = mapped_column(String(100))
    publication_mode: Mapped[str] = mapped_column(String(16))
    object_key: Mapped[str | None] = mapped_column(Text)
    retained: Mapped[bool] = mapped_column(Boolean)
    retention_reason: Mapped[str] = mapped_column(Text)
