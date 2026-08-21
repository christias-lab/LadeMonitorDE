from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from ladepulse_ingestion.adapters.base import NormalizedBatch, PayloadEnvelope


class DatexValidationError(ValueError):
    pass


def parse_dynamic_json(envelope: PayloadEnvelope) -> NormalizedBatch:
    """Parse the supported AFIR DATEX II v3 dynamic subset.

    The complete live adapter will validate against the publication schema. This parser keeps
    Phase 1 fixtures close to that hierarchy and fails closed for missing IDs or timestamps.
    """

    try:
        payload = json.loads(envelope.content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DatexValidationError("payload is not valid UTF-8 JSON") from exc

    publication = _find_publication(payload)
    statuses = publication.get("energyInfrastructureStatus", [])
    if not isinstance(statuses, list):
        raise DatexValidationError("energyInfrastructureStatus must be a list")

    normalized: list[dict[str, Any]] = []
    for item in statuses:
        if not isinstance(item, dict):
            raise DatexValidationError("status entry must be an object")
        connector_id = item.get("connectorId")
        status = item.get("status")
        observed_at = item.get("lastUpdated") or publication.get("publicationTime")
        if not connector_id or not status or not observed_at:
            raise DatexValidationError("status entry requires connectorId, status, and timestamp")
        normalized.append(
            {
                "connector_external_id": str(connector_id),
                "state": normalize_datex_state(str(status)),
                "source_observed_at": _parse_timestamp(str(observed_at)),
            }
        )
    return NormalizedBatch(status_records=tuple(normalized))


def normalize_datex_state(value: str) -> str:
    compact = value.replace("-", "").replace("_", "").lower()
    mapping = {
        "available": "available",
        "occupied": "in_use",
        "charging": "in_use",
        "outofservice": "out_of_service",
        "faulted": "out_of_service",
        "unknown": "unknown",
    }
    try:
        return mapping[compact]
    except KeyError as exc:
        raise DatexValidationError(f"unsupported DATEX status: {value}") from exc


def _find_publication(payload: dict[str, Any]) -> dict[str, Any]:
    candidates = (
        payload.get("payloadPublication"),
        payload.get("d2LogicalModel", {}).get("payloadPublication"),
        payload.get("messageContainer", {}).get("payloadPublication"),
    )
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    raise DatexValidationError("missing DATEX II payloadPublication")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DatexValidationError("invalid source timestamp") from exc
    if parsed.tzinfo is None:
        raise DatexValidationError("source timestamp must include an offset")
    return parsed
