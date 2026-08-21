from datetime import UTC, datetime, timedelta

import pytest
from ladepulse_core.events import StateMessage, derive_status_events


def at(minutes: int) -> datetime:
    return datetime(2026, 7, 29, 12, tzinfo=UTC) + timedelta(minutes=minutes)


def test_duplicate_messages_do_not_create_duplicate_transitions() -> None:
    events = derive_status_events(
        [
            StateMessage(at(0), "available"),
            StateMessage(at(0), "available"),
            StateMessage(at(10), "available"),
            StateMessage(at(20), "in_use"),
            StateMessage(at(20), "in_use"),
            StateMessage(at(30), "available"),
        ]
    )

    assert [(event.from_state, event.to_state) for event in events] == [
        (None, "available"),
        ("available", "in_use"),
        ("in_use", "available"),
    ]
    assert [event.ended_at for event in events] == [at(20), at(30), None]


def test_out_of_order_messages_are_ordered_by_source_time() -> None:
    events = derive_status_events(
        [
            StateMessage(at(20), "out_of_service"),
            StateMessage(at(0), "available"),
            StateMessage(at(40), "available"),
        ]
    )
    assert [event.started_at for event in events] == [at(0), at(20), at(40)]
    assert events[1].ended_at == at(40)


def test_conflicting_duplicate_timestamp_fails_closed() -> None:
    with pytest.raises(ValueError, match="conflicting statuses"):
        derive_status_events(
            [
                StateMessage(at(0), "available"),
                StateMessage(at(0), "out_of_service"),
            ]
        )
