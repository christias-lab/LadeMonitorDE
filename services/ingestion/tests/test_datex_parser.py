from datetime import UTC, datetime
from pathlib import Path

import pytest
from ladepulse_ingestion.adapters.base import PayloadEnvelope, PublicationMode
from ladepulse_ingestion.parsers.datex_v3 import (
    DatexValidationError,
    normalize_datex_state,
    parse_dynamic_json,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "datex_ii"


def envelope(name: str) -> PayloadEnvelope:
    return PayloadEnvelope(
        publication_external_id="afir-datex-demo",
        content=(FIXTURES / name).read_bytes(),
        content_type="application/json",
        received_at=datetime(2026, 7, 29, 12, 0, tzinfo=UTC),
        source_observed_at=None,
        mode=PublicationMode.FULL,
        schema_version="DATEX II 3",
    )


def test_valid_dynamic_payload_normalizes_states_and_timestamps() -> None:
    payload = envelope("dynamic_valid.json")
    batch = parse_dynamic_json(payload)
    assert [item["state"] for item in batch.status_records] == [
        "available",
        "in_use",
        "out_of_service",
    ]
    assert batch.status_records[0]["source_observed_at"] == datetime(
        2026, 7, 29, 11, 59, 30, tzinfo=UTC
    )
    assert batch.status_records[1]["source_observed_at"] == datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
    assert len(payload.sha256) == 64
    assert payload.sha256 == envelope("dynamic_valid.json").sha256


def test_missing_connector_identifier_fails_closed() -> None:
    with pytest.raises(DatexValidationError, match="requires connectorId"):
        parse_dynamic_json(envelope("dynamic_invalid_missing_id.json"))


@pytest.mark.parametrize(
    ("source", "normalized"),
    [
        ("charging", "in_use"),
        ("faulted", "out_of_service"),
        ("unknown", "unknown"),
    ],
)
def test_supported_status_mapping(source: str, normalized: str) -> None:
    assert normalize_datex_state(source) == normalized


def test_unsupported_status_is_not_silently_coerced() -> None:
    with pytest.raises(DatexValidationError, match="unsupported DATEX status"):
        normalize_datex_state("reservedByWizard")
