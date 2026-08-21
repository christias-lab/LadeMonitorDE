from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class StateMessage:
    observed_at: datetime
    state: str


@dataclass(frozen=True)
class DerivedStatusEvent:
    from_state: str | None
    to_state: str
    started_at: datetime
    ended_at: datetime | None


def derive_status_events(messages: Iterable[StateMessage]) -> tuple[DerivedStatusEvent, ...]:
    """Collapse observations into time-weighted state intervals.

    Exact duplicate messages are ignored. Conflicting states for one source
    timestamp fail closed because selecting one would invent source ordering.
    """

    unique_by_time: dict[datetime, str] = {}
    for message in messages:
        if message.observed_at.tzinfo is None:
            raise ValueError("status observation timestamps must be timezone-aware")
        existing = unique_by_time.get(message.observed_at)
        if existing is not None and existing != message.state:
            raise ValueError("conflicting statuses share one source timestamp")
        unique_by_time[message.observed_at] = message.state

    transitions: list[tuple[str | None, str, datetime]] = []
    previous_state: str | None = None
    for observed_at, state in sorted(unique_by_time.items()):
        if state == previous_state:
            continue
        transitions.append((previous_state, state, observed_at))
        previous_state = state

    return tuple(
        DerivedStatusEvent(
            from_state=from_state,
            to_state=to_state,
            started_at=started_at,
            ended_at=(transitions[index + 1][2] if index + 1 < len(transitions) else None),
        )
        for index, (from_state, to_state, started_at) in enumerate(transitions)
    )
