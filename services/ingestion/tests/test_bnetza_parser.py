from pathlib import Path

from ladepulse_ingestion.bnetza import (
    _connector_type,
    _maximum_power,
    iter_facilities,
    source_date,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "bnetza" / "register_sample.csv"


def test_bnetza_fixture_preserves_official_identifiers_and_decimal_coordinates() -> None:
    records = list(iter_facilities(FIXTURE))
    assert source_date(FIXTURE).isoformat() == "2026-07-28"
    assert len(records) == 2
    first = records[0]
    assert first.external_id == "1158224"
    assert first.operator_name == "EnBW mobility+ AG und Co.KG"
    assert first.latitude == 48.578533
    assert first.longitude == 9.87484
    assert len(first.points) == 2
    assert first.points[0].evse_external_id == "DE*EBW*E912316*1"
    assert first.points[1].evse_external_id == "BNETZA:1158224:2"
    assert first.points[1].public_key == "PUBLIC2"
    assert first.points[0].current_type == "DC"


def test_bnetza_missing_evse_id_gets_namespaced_stable_fallback() -> None:
    second = list(iter_facilities(FIXTURE))[1]
    assert second.source_status == "In Wartung"
    assert second.address == "Testweg 2 Parkdeck, 10115 Berlin"
    assert second.points[0].evse_external_id == "BNETZA:2000001:1"
    assert second.points[0].current_type == "AC"


def test_multi_connector_fields_are_normalized_without_inflating_point_count() -> None:
    assert _maximum_power("22; 50; 150") == 150
    assert (
        _connector_type("AC Typ 2 Steckdose; AC Typ 2 Steckdose; DC CHAdeMO")
        == "AC Typ 2 Steckdose; DC CHAdeMO"
    )
