"""Several product photos of one look arrive in a single request."""

from io import BytesIO

import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.auth import identity
from app.config import settings
from app.db import Base, session
from app.main import app
from app.schemas import LOOK_SIZE


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    monkeypatch.setenv("STORAGE_MODE", "local")
    settings.cache_clear()
    # One shared in-memory connection: store_asset runs in a worker thread.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)

    def db():
        with factory() as item, item.begin():
            yield item

    app.dependency_overrides[identity] = lambda: "alice"
    app.dependency_overrides[session] = db
    try:
        with TestClient(app) as value:
            yield value
    finally:
        app.dependency_overrides.pop(identity, None)
        app.dependency_overrides.pop(session, None)
        settings.cache_clear()


def image(name):
    data = BytesIO()
    Image.new("RGB", (16, 16), "blue").save(data, format="PNG")
    return ("files", (name, data.getvalue(), "image/png"))


def test_a_whole_look_uploads_in_one_request(client):
    response = client.post(
        "/api/assets/bulk", files=[image(f"item{i}.png") for i in range(LOOK_SIZE)]
    )
    assert response.status_code == 201, response.text
    assets = response.json()["assets"]
    # Every piece comes back as an ordinary product image, in the order it was sent.
    assert len(assets) == LOOK_SIZE
    assert {a["role"] for a in assets} == {"product"}
    assert [a["fileName"] for a in assets] == [f"item{i}.png" for i in range(LOOK_SIZE)]
    assert len({a["id"] for a in assets}) == LOOK_SIZE


def test_more_pieces_than_a_look_holds_are_refused(client):
    response = client.post(
        "/api/assets/bulk", files=[image(f"item{i}.png") for i in range(LOOK_SIZE + 1)]
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_UPLOAD"


def test_one_unreadable_file_fails_the_request(client):
    response = client.post(
        "/api/assets/bulk",
        files=[image("good.png"), ("files", ("bad.png", b"not an image", "image/png"))],
    )
    assert response.status_code == 415


def csv_file(text):
    return {"file": ("catalog.csv", text.encode(), "text/csv")}


def _mock_download(monkeypatch):
    from app.services import assets as assets_service

    async def download(url, limit, accept):
        data = BytesIO()
        Image.new("RGB", (8, 8), "white").save(data, format="PNG")
        return data.getvalue(), "image/png", url

    monkeypatch.setattr(assets_service, "download_public", download)


def test_catalog_import_stores_each_direct_image_url_as_a_try_on_product(client, monkeypatch):
    _mock_download(monkeypatch)
    csv_text = "imageUrl,name\nhttps://cdn.example/shirt.png,Shirt\nhttps://cdn.example/hat.png,Hat\n"
    response = client.post("/api/assets/catalog-import", files=csv_file(csv_text))
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["created"]) == 2 and body["errors"] == []
    assert {a["role"] for a in body["created"]} == {"product"}


def test_catalog_import_reports_a_bad_row_without_failing_the_batch(client, monkeypatch):
    _mock_download(monkeypatch)
    csv_text = "imageUrl,name\nhttps://cdn.example/shirt.png,Shirt\n,Broken\n"
    response = client.post("/api/assets/catalog-import", files=csv_file(csv_text))
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["created"]) == 1
    assert body["errors"] == [{"row": 2, "message": "Each row needs a url or an imageUrl."}]


def test_an_empty_csv_is_a_clean_422(client):
    response = client.post("/api/assets/catalog-import", files=csv_file("imageUrl\n"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATALOG_IMPORT_INVALID"


def test_the_product_library_route_serves_catalog_imports_alongside_model_photos(client, monkeypatch):
    _mock_download(monkeypatch)
    client.post(
        "/api/assets/catalog-import", files=csv_file("imageUrl\nhttps://cdn.example/shirt.png\n")
    )
    response = client.get("/api/assets", params={"role": "product", "source": "try_on"})
    assert response.status_code == 200
    assert len(response.json()["assets"]) == 1

    rejected = client.get("/api/assets", params={"role": "source_video", "source": "try_on"})
    assert rejected.status_code == 422
