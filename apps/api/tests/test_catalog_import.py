"""Bulk CSV catalog import: populates the try-on product library, one row at a time,
without letting a single bad row fail the whole batch."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Asset, Base
from app.errors import DomainError
from app.services import assets as assets_service
from app.services.assets import CATALOG_IMPORT_MAX_ROWS, import_catalog_csv, library
from app.services.storage import Storage


def png():
    from io import BytesIO

    from PIL import Image

    data = BytesIO()
    Image.new("RGB", (8, 8), "white").save(data, format="PNG")
    return data.getvalue()


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_PATH", str(tmp_path))
    monkeypatch.setenv("STORAGE_MODE", "local")
    from app.config import settings

    settings.cache_clear()
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    settings.cache_clear()


@pytest.fixture
def storage():
    return Storage()


@pytest.mark.asyncio
async def test_a_good_row_and_a_bad_row_both_get_reported_without_failing_the_batch(
    db, storage, monkeypatch
):
    async def resolve(url):
        if "dead" in url:
            return {"url": url, "title": "", "description": "", "imageUrl": None}
        return {"url": url, "title": "Shirt", "description": "", "imageUrl": "https://shop.example/shirt.png"}

    async def download(url, limit, accept):
        return png(), "image/png", url

    monkeypatch.setattr(assets_service, "resolve_product", resolve)
    monkeypatch.setattr(assets_service, "download_public", download)

    rows = [
        {"url": "https://shop.example/shirt", "name": "Blue shirt"},
        {"url": "https://shop.example/dead-link"},
    ]
    created, errors = await import_catalog_csv(db, storage, "alice", rows)

    assert len(created) == 1
    assert created[0].role == "product" and created[0].source == "try_on"
    assert errors == [{"row": 2, "message": "No product image could be found at this URL."}]
    # It actually landed in the library the picker reads from.
    assert [a.id for a in library(db, "alice", "product", "try_on")] == [created[0].id]


@pytest.mark.asyncio
async def test_an_imageurl_row_skips_the_page_scrape(db, storage, monkeypatch):
    calls = []

    async def resolve(url):
        calls.append(url)
        raise AssertionError("resolve_product should not run when imageUrl is given directly")

    async def download(url, limit, accept):
        assert url == "https://cdn.example/hat.png"
        return png(), "image/png", url

    monkeypatch.setattr(assets_service, "resolve_product", resolve)
    monkeypatch.setattr(assets_service, "download_public", download)

    created, errors = await import_catalog_csv(
        db, storage, "alice", [{"imageUrl": "https://cdn.example/hat.png"}]
    )
    assert len(created) == 1 and errors == []
    assert calls == []


@pytest.mark.asyncio
async def test_a_row_with_neither_url_nor_imageurl_is_a_clean_per_row_error(db, storage):
    created, errors = await import_catalog_csv(db, storage, "alice", [{"name": "Mystery item"}])
    assert created == []
    assert errors == [{"row": 1, "message": "Each row needs a url or an imageUrl."}]


@pytest.mark.asyncio
async def test_importing_more_than_the_row_cap_is_rejected_before_any_network_call(db, storage, monkeypatch):
    async def must_not_run(*args, **kwargs):
        raise AssertionError("no row should be processed once the batch is rejected")

    monkeypatch.setattr(assets_service, "resolve_product", must_not_run)
    monkeypatch.setattr(assets_service, "download_public", must_not_run)

    rows = [{"imageUrl": f"https://cdn.example/{i}.png"} for i in range(CATALOG_IMPORT_MAX_ROWS + 1)]
    with pytest.raises(DomainError) as exc:
        await import_catalog_csv(db, storage, "alice", rows)
    assert exc.value.code == "CATALOG_IMPORT_TOO_LARGE"


@pytest.mark.asyncio
async def test_a_download_failure_is_reported_as_a_row_error_not_a_crash(db, storage, monkeypatch):
    async def resolve(url):
        return {"url": url, "title": "", "description": "", "imageUrl": "https://shop.example/broken.png"}

    async def download(url, limit, accept):
        raise DomainError("PRODUCT_UNAVAILABLE", "Remote content could not be retrieved.", 503, True)

    monkeypatch.setattr(assets_service, "resolve_product", resolve)
    monkeypatch.setattr(assets_service, "download_public", download)

    created, errors = await import_catalog_csv(db, storage, "alice", [{"url": "https://shop.example/x"}])
    assert created == []
    assert errors == [{"row": 1, "message": "Remote content could not be retrieved."}]


def test_the_product_library_route_only_returns_this_users_try_on_products(db):
    for identifier, owner, role, source in [
        ("shirt", "alice", "product", "try_on"),
        ("hat", "alice", "product", "try_on"),
        ("bobs-shoe", "bob", "product", "try_on"),
        ("create-product", "alice", "product", None),
    ]:
        db.add(
            Asset(
                id=identifier,
                user_id=owner,
                role=role,
                source=source,
                mime_type="image/png",
                file_name=f"{identifier}.png",
                size_bytes=1,
                storage_key=f"{owner}/{identifier}",
            )
        )
    db.flush()
    assert {a.id for a in library(db, "alice", "product", "try_on")} == {"shirt", "hat"}
    assert [a.id for a in library(db, "bob", "product", "try_on")] == ["bobs-shoe"]
