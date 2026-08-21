from pathlib import Path

import pytest
from ladepulse_core.config import Settings
from ladepulse_ingestion.mobilithek import (
    MobilithekConfigurationError,
    MobilithekSubscription,
)


def test_dynamic_feed_is_disabled_without_subscription_details() -> None:
    with pytest.raises(MobilithekConfigurationError, match="is disabled"):
        MobilithekSubscription.from_settings(Settings())


def test_dynamic_feed_requires_https_and_existing_certificate_files(
    tmp_path: Path,
) -> None:
    certificate = tmp_path / "client.pem"
    key = tmp_path / "client-key.pem"
    certificate.touch()
    key.touch()
    settings = Settings(
        mobilithek_publication_url="http://example.invalid/feed",
        mobilithek_client_certificate_path=str(certificate),
        mobilithek_client_key_path=str(key),
    )
    with pytest.raises(MobilithekConfigurationError, match="must use HTTPS"):
        MobilithekSubscription.from_settings(settings)


def test_dynamic_feed_accepts_only_explicit_subscription_configuration(
    tmp_path: Path,
) -> None:
    certificate = tmp_path / "client.pem"
    key = tmp_path / "client-key.pem"
    certificate.touch()
    key.touch()
    settings = Settings(
        mobilithek_publication_url="https://example.invalid/assigned-publication",
        mobilithek_client_certificate_path=str(certificate),
        mobilithek_client_key_path=str(key),
    )
    subscription = MobilithekSubscription.from_settings(settings)
    assert subscription.publication_url.endswith("/assigned-publication")
    assert subscription.client_certificate == certificate
