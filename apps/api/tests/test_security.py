import pytest

from app.config import Settings
from app.errors import DomainError
from app.services.product import public_target


def test_private_and_non_https_product_urls_are_rejected():
    for url in [
        "http://example.com",
        "https://127.0.0.1",
        "https://224.0.0.1",
        "https://example.com:invalid",
        "https://169.254.169.254",
        "https://user:pass@example.com",
    ]:
        with pytest.raises(DomainError):
            public_target(url)


def test_production_rejects_development_modes():
    with pytest.raises(ValueError):
        Settings(app_env="production")
