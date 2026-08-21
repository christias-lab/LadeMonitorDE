from datetime import UTC, datetime, timedelta

import pytest
from ladepulse_core.metrics import (
    ConnectorState,
    charging_pressure,
    display_german_time,
    effective_state,
    floor_to_ten_minutes,
    offline_share,
    utilization,
)


def test_utilization_excludes_offline_connectors() -> None:
    assert utilization(3, 1) == 0.25
    assert utilization(0, 0) is None
    assert offline_share(3, 1, 1) == 0.2
    assert offline_share(0, 0, 0) is None


def test_stale_data_becomes_unknown_not_offline() -> None:
    observed = datetime(2026, 7, 29, 11, 58, tzinfo=UTC)
    assert (
        effective_state(
            ConnectorState.AVAILABLE,
            observed,
            datetime(2026, 7, 29, 12, 1, tzinfo=UTC),
            timedelta(minutes=5),
        )
        == ConnectorState.AVAILABLE
    )
    assert (
        effective_state(
            ConnectorState.AVAILABLE,
            observed,
            datetime(2026, 7, 29, 12, 4, tzinfo=UTC),
            timedelta(minutes=5),
        )
        == ConnectorState.STALE_UNKNOWN
    )


def test_pressure_is_explainable_and_confidence_adjusted() -> None:
    result = charging_pressure(
        utilization_value=0.75,
        offline_share_value=0.10,
        normal_utilization=0.50,
        alternatives_gap=0.20,
        live_coverage=0.80,
        freshness_quality=0.90,
        identifier_completeness=0.95,
    )
    assert result is not None
    assert result.deviation == pytest.approx(0.5)
    assert result.confidence == pytest.approx(0.684)
    assert result.raw_pressure == pytest.approx(0.455)
    assert result.score == 47
    assert result.sufficient_confidence
    assert sum(result.weights.values()) == pytest.approx(1.0)


def test_pressure_requires_observable_inputs() -> None:
    assert (
        charging_pressure(
            utilization_value=None,
            offline_share_value=0.1,
            normal_utilization=0.5,
            alternatives_gap=0.2,
            live_coverage=1.0,
            freshness_quality=1.0,
            identifier_completeness=1.0,
        )
        is None
    )


def test_time_buckets_are_utc_and_dst_display_is_unambiguous() -> None:
    value = datetime(2026, 7, 29, 12, 19, 59, tzinfo=UTC)
    assert floor_to_ten_minutes(value) == datetime(2026, 7, 29, 12, 10, tzinfo=UTC)

    before_spring = display_german_time(datetime(2026, 3, 29, 0, 30, tzinfo=UTC))
    after_spring = display_german_time(datetime(2026, 3, 29, 1, 30, tzinfo=UTC))
    assert (before_spring.hour, before_spring.utcoffset()) == (1, timedelta(hours=1))
    assert (after_spring.hour, after_spring.utcoffset()) == (3, timedelta(hours=2))

    first_fall = display_german_time(datetime(2026, 10, 25, 0, 30, tzinfo=UTC))
    second_fall = display_german_time(datetime(2026, 10, 25, 1, 30, tzinfo=UTC))
    assert first_fall.hour == second_fall.hour == 2
    assert first_fall.utcoffset() == timedelta(hours=2)
    assert second_fall.utcoffset() == timedelta(hours=1)
    assert (first_fall.fold, second_fall.fold) == (0, 1)


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 7, 29, 12, 0),
        datetime(2026, 3, 29, 2, 30),
    ],
)
def test_naive_timestamps_are_rejected(value: datetime) -> None:
    with pytest.raises(ValueError):
        floor_to_ten_minutes(value)
