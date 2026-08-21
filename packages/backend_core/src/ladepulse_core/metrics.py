from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo


class ConnectorState(StrEnum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    OUT_OF_SERVICE = "out_of_service"
    UNKNOWN = "unknown"
    STALE_UNKNOWN = "stale_unknown"


@dataclass(frozen=True)
class PressureResult:
    utilization: float
    offline_share: float
    deviation: float
    alternatives_gap: float
    confidence: float
    raw_pressure: float
    score: int
    sufficient_confidence: bool
    weights: dict[str, float]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def utilization(available: int, in_use: int) -> float | None:
    denominator = available + in_use
    if denominator <= 0:
        return None
    return in_use / denominator


def offline_share(available: int, in_use: int, out_of_service: int) -> float | None:
    denominator = available + in_use + out_of_service
    if denominator <= 0:
        return None
    return out_of_service / denominator


def effective_state(
    state: ConnectorState,
    source_observed_at: datetime,
    requested_at: datetime,
    stale_after: timedelta,
) -> ConnectorState:
    if source_observed_at.tzinfo is None or requested_at.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    if requested_at - source_observed_at > stale_after:
        return ConnectorState.STALE_UNKNOWN
    return state


def charging_pressure(
    *,
    utilization_value: float | None,
    offline_share_value: float | None,
    normal_utilization: float | None,
    alternatives_gap: float,
    live_coverage: float,
    freshness_quality: float,
    identifier_completeness: float,
) -> PressureResult | None:
    if utilization_value is None or offline_share_value is None or normal_utilization is None:
        return None
    u = _clamp(utilization_value)
    o = _clamp(offline_share_value)
    d = _clamp((u - normal_utilization) / max(0.10, 1 - normal_utilization))
    r = _clamp(alternatives_gap)
    c = _clamp(live_coverage * freshness_quality * identifier_completeness)
    weights = {
        "utilization": 0.40,
        "offline_share": 0.25,
        "deviation": 0.20,
        "alternatives_gap": 0.15,
    }
    raw = weights["utilization"] * u
    raw += weights["offline_share"] * o
    raw += weights["deviation"] * d
    raw += weights["alternatives_gap"] * r
    score = round(100 * (c * raw + (1 - c) * 0.50))
    return PressureResult(u, o, d, r, c, raw, score, c >= 0.50, weights)


def floor_to_ten_minutes(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    utc_value = value.astimezone(UTC)
    return utc_value.replace(minute=(utc_value.minute // 10) * 10, second=0, microsecond=0)


def display_german_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(ZoneInfo("Europe/Berlin"))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2
    a += math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
