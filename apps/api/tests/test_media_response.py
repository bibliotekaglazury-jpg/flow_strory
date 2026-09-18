from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.main import stored_media_type
from app.services.storage import Storage


def test_stored_media_type_detects_reference_images_without_filename_extension(tmp_path):
    png = tmp_path / "opaque-storage-key"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"payload")

    assert stored_media_type(png) == "image/png"


def test_stored_media_type_falls_back_for_unknown_content(tmp_path):
    item = tmp_path / "opaque-storage-key"
    item.write_bytes(b"unknown")

    assert stored_media_type(item) == "application/octet-stream"


def test_signed_media_supports_head_for_external_provider_preflight(tmp_path, monkeypatch):
    image = tmp_path / "opaque-storage-key"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"payload")
    monkeypatch.setattr("app.main.Storage.verify", lambda self, key, expires, signature: image)

    from app.main import app

    with TestClient(app) as client:
        response = client.head("/api/media/owned/reference?expires=9999999999&signature=test")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-length"] == str(image.stat().st_size)


def test_provider_media_url_has_image_extension_and_long_lived_signature(tmp_path):
    storage = Storage(
        SimpleNamespace(
            storage_path=str(tmp_path),
            storage_mode="local",
            s3_endpoint_url="",
            s3_region="",
            s3_access_key_id="",
            s3_secret_access_key="",
            s3_bucket="",
            public_api_url="https://app.example",
            provider_asset_origin="https://media.example",
            storage_signing_secret="secret",
            app_env="development",
        )
    )

    url, _ = storage.provider_url("owner/opaque-key", "image/png")

    assert url.startswith("https://media.example/api/provider-media/owner/opaque-key/reference.png?")


def test_provider_media_route_strips_display_filename(tmp_path, monkeypatch):
    image = tmp_path / "opaque-storage-key"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"payload")
    seen = []

    def verify(self, key, expires, signature):
        seen.append(key)
        return image

    monkeypatch.setattr("app.main.Storage.verify", verify)
    from app.main import app

    with TestClient(app) as client:
        response = client.head(
            "/api/provider-media/owned/opaque-storage-key/reference.png"
            "?expires=9999999999&signature=test"
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert seen == ["owned/opaque-storage-key"]
