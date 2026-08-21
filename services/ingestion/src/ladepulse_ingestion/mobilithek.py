from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from ladepulse_core.config import Settings


class MobilithekConfigurationError(RuntimeError):
    """Raised when an AFIR consumer subscription is not fully configured."""


@dataclass(frozen=True)
class MobilithekSubscription:
    publication_url: str
    client_certificate: Path
    client_key: Path

    @classmethod
    def from_settings(cls, settings: Settings) -> MobilithekSubscription:
        configured = {
            "MOBILITHEK_PUBLICATION_URL": settings.mobilithek_publication_url,
            "MOBILITHEK_CLIENT_CERTIFICATE_PATH": (settings.mobilithek_client_certificate_path),
            "MOBILITHEK_CLIENT_KEY_PATH": settings.mobilithek_client_key_path,
        }
        missing = [name for name, value in configured.items() if not value]
        if missing:
            raise MobilithekConfigurationError(
                "Mobilithek AFIR dynamic data is disabled; configure "
                + ", ".join(missing)
                + " from an approved technical-consumer subscription."
            )
        publication_url = str(settings.mobilithek_publication_url)
        if urlparse(publication_url).scheme != "https":
            raise MobilithekConfigurationError("MOBILITHEK_PUBLICATION_URL must use HTTPS.")
        certificate = Path(str(settings.mobilithek_client_certificate_path))
        key = Path(str(settings.mobilithek_client_key_path))
        for label, path in (
            ("MOBILITHEK_CLIENT_CERTIFICATE_PATH", certificate),
            ("MOBILITHEK_CLIENT_KEY_PATH", key),
        ):
            if not path.is_file():
                raise MobilithekConfigurationError(f"{label} does not identify a file.")
        return cls(
            publication_url=publication_url,
            client_certificate=certificate,
            client_key=key,
        )
