from datetime import UTC, datetime

import pytest
from ladepulse_ingestion.adapters.base import (
    PayloadEnvelope,
    PublicationMode,
    RetryPolicy,
    SchedulePolicy,
    retry_delay_seconds,
)


def test_payload_idempotency_key_covers_publication_mode_sequence_and_hash() -> None:
    def make(sequence: int | None, mode: PublicationMode) -> PayloadEnvelope:
        return PayloadEnvelope(
            publication_external_id="dynamic-1",
            content=b'{"status":"available"}',
            content_type="application/json",
            received_at=datetime(2026, 7, 29, 12, tzinfo=UTC),
            source_observed_at=datetime(2026, 7, 29, 11, 59, tzinfo=UTC),
            mode=mode,
            schema_version="DATEX II 3",
            sequence_number=sequence,
        )

    assert (
        make(10, PublicationMode.DELTA).idempotency_key
        == make(10, PublicationMode.DELTA).idempotency_key
    )
    assert (
        make(10, PublicationMode.DELTA).idempotency_key
        != make(11, PublicationMode.DELTA).idempotency_key
    )
    assert (
        make(10, PublicationMode.DELTA).idempotency_key
        != make(10, PublicationMode.FULL).idempotency_key
    )


def test_retry_policy_honors_retry_after_and_bounds_backoff() -> None:
    policy = RetryPolicy(
        maximum_attempts=5,
        base_delay_seconds=2,
        maximum_delay_seconds=30,
    )
    assert retry_delay_seconds(1, policy, jitter_fraction=1) == 2
    assert retry_delay_seconds(4, policy, jitter_fraction=1) == 16
    assert (
        retry_delay_seconds(
            2,
            policy,
            retry_after_seconds=20,
            jitter_fraction=0,
        )
        == 20
    )
    assert retry_delay_seconds(9, policy, jitter_fraction=1) == 30
    assert (
        retry_delay_seconds(
            2,
            policy,
            retry_after_seconds=60,
            jitter_fraction=0,
        )
        == 60
    )


def test_invalid_schedule_fails_during_adapter_configuration() -> None:
    with pytest.raises(ValueError, match="poll interval"):
        SchedulePolicy(
            poll_interval_seconds=0,
            minimum_request_interval_seconds=0,
        )
