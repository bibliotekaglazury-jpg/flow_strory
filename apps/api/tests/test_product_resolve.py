import pytest
from types import SimpleNamespace

from app import main
from app.schemas import Resolve


@pytest.mark.asyncio
async def test_successful_url_resolution_returns_owned_product_asset(monkeypatch):
    async def resolve(url):
        return {"url": url, "title": "Phone", "description": "Camera", "imageUrl": "https://shop.example/phone.png"}

    async def download(url, limit, accept):
        assert (url, limit, accept) == ("https://shop.example/phone.png", 10 * 1024 * 1024, "image/*")
        return b"validated-image", "image/png", url

    monkeypatch.setattr(main, "resolve_product", resolve)
    monkeypatch.setattr(main, "download_public", download, raising=False)
    monkeypatch.setattr(main, "store_asset", lambda db, storage, user, role, data, name: SimpleNamespace(id="owned-product"))
    monkeypatch.setattr(main, "asset_view", lambda asset, storage: {"id": asset.id})
    result = await main.product(Resolve(url="https://shop.example/phone"), user="alice", db=object())
    assert result["asset"]["id"] == "owned-product"
