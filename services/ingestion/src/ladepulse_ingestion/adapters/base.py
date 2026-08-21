from __future__ import annotations

import abc
import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class PublicationMode(StrEnum):
    FULL = "full"
    DELTA = "delta"


class DeliveryMode(StrEnum):
    PULL = "pull"
    PUSH = "push"


class AuthenticationKind(StrEnum):
    NONE = "none"
    X509 = "x509"
    BEARER = "bearer"
    BASIC = "basic"
    CUSTOM = "custom"


@dataclass(frozen=True)
class SecretReference:
    """Backend secret-store key; never the secret value."""

    key: str


@dataclass(frozen=True)
class AuthenticationPolicy:
    kind: AuthenticationKind = AuthenticationKind.NONE
    secret_references: tuple[SecretReference, ...] = ()


@dataclass(frozen=True)
class SchedulePolicy:
    poll_interval_seconds: int | None
    minimum_request_interval_seconds: float
    delivery_modes: tuple[DeliveryMode, ...] = (DeliveryMode.PULL,)

    def __post_init__(self) -> None:
        if self.poll_interval_seconds is not None and self.poll_interval_seconds <= 0:
            raise ValueError("poll interval must be positive")
        if self.minimum_request_interval_seconds < 0:
            raise ValueError("minimum request interval cannot be negative")


@dataclass(frozen=True)
class RetryPolicy:
    maximum_attempts: int = 5
    base_delay_seconds: float = 1.0
    maximum_delay_seconds: float = 120.0

    def __post_init__(self) -> None:
        if self.maximum_attempts < 1:
            raise ValueError("maximum attempts must be at least one")
        if self.base_delay_seconds <= 0:
            raise ValueError("base retry delay must be positive")
        if self.maximum_delay_seconds < self.base_delay_seconds:
            raise ValueError("maximum retry delay must not be below the base delay")


@dataclass(frozen=True)
class LicenceMetadata:
    code: str
    url: str | None
    attribution: str | None
    raw_storage_allowed: bool
    redistribution_allowed: bool
    verified_at: datetime


@dataclass(frozen=True)
class PublicationMetadata:
    external_id: str
    name: str
    format: str
    schema_version: str | None
    stale_after_seconds: int
    update_interval_seconds: int
    supports_delta: bool
    licence: LicenceMetadata
    rate_limit_notes: str | None
    authentication: AuthenticationPolicy = AuthenticationPolicy()
    schedule: SchedulePolicy = SchedulePolicy(
        poll_interval_seconds=None,
        minimum_request_interval_seconds=0,
    )
    retry: RetryPolicy = RetryPolicy()


@dataclass(frozen=True)
class PayloadEnvelope:
    publication_external_id: str
    content: bytes
    content_type: str
    received_at: datetime
    source_observed_at: datetime | None
    mode: PublicationMode
    schema_version: str | None
    etag: str | None = None
    last_modified: datetime | None = None
    sequence_number: int | None = None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()

    @property
    def idempotency_key(self) -> str:
        sequence = "" if self.sequence_number is None else str(self.sequence_number)
        value = f"{self.publication_external_id}\0{self.mode.value}\0{sequence}\0{self.sha256}"
        return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class ConditionalRequest:
    etag: str | None = None
    if_modified_since: datetime | None = None


@dataclass(frozen=True)
class NormalizedBatch:
    static_records: tuple[dict[str, Any], ...] = ()
    status_records: tuple[dict[str, Any], ...] = ()
    price_records: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class PushRequest:
    body: bytes
    content_type: str
    received_at: datetime
    headers: dict[str, str]


class SourceRequestError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


def retry_delay_seconds(
    attempt: int,
    policy: RetryPolicy,
    *,
    retry_after_seconds: float | None = None,
    jitter_fraction: float = 0.0,
) -> float:
    """Return bounded exponential delay while honoring Retry-After.

    The caller supplies jitter so tests stay deterministic and production can
    inject a cryptographically unimportant random fraction in ``[0, 1]``.
    """

    if attempt < 1:
        raise ValueError("attempt is one-based")
    if not 0 <= jitter_fraction <= 1:
        raise ValueError("jitter fraction must be between zero and one")
    exponential = min(
        policy.maximum_delay_seconds,
        policy.base_delay_seconds * (2 ** (attempt - 1)),
    )
    jittered = exponential * (0.75 + 0.25 * jitter_fraction)
    if retry_after_seconds is not None:
        return max(jittered, retry_after_seconds)
    return jittered


class SourceAdapter(abc.ABC):
    @abc.abstractmethod
    async def discover(self) -> tuple[PublicationMetadata, ...]:
        """Return verified publications configured for this adapter."""

    @abc.abstractmethod
    async def fetch(
        self,
        publication: PublicationMetadata,
        conditional: ConditionalRequest,
    ) -> PayloadEnvelope | None:
        """Fetch one payload or return None for an unchanged publication."""

    @abc.abstractmethod
    def parse(self, envelope: PayloadEnvelope) -> NormalizedBatch:
        """Validate and normalize an immutable payload envelope."""

    async def accept_push(
        self,
        publication: PublicationMetadata,
        request: PushRequest,
    ) -> PayloadEnvelope:
        """Authenticate and envelope a provider push.

        Pull-only adapters deliberately retain this default. Push-capable
        adapters override it and use only backend secret references.
        """

        raise NotImplementedError(
            f"{type(self).__name__} does not support push for {publication.external_id}"
        )
