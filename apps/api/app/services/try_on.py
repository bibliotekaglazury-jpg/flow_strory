"""Still look preview: one synchronous provider call, no job, quote or worker.

The video route is deliberately untouched. That pipeline exists because a render takes
minutes and has to survive restarts; a preview answers within one request, so reserving
credits and polling a job would only make a fast thing feel slow.
"""

from sqlalchemy import select

from app.config import settings
from app.db import Asset
from app.errors import DomainError
from app.prompts.tryon import compose
from app.providers.mock import MockImageProvider
from app.providers.openrouter_image import OpenRouterImageProvider
from app.services.assets import owned_inputs, store_asset
from app.services.credits import change
from app.services.storage import Storage, asset_view

ROLE = "tryon_photo"


def provider():
    config = settings()
    if config.image_provider == "mock":
        return MockImageProvider()
    if not config.openrouter_api_key:
        raise DomainError("PREVIEW_UNAVAILABLE", "Look previews are not configured.", 503, True)
    return OpenRouterImageProvider(config.openrouter_api_key, config.openrouter_image_model)


def media_url(storage, asset):
    if hasattr(storage, "provider_url"):
        return storage.provider_url(asset.storage_key, asset.mime_type)[0]
    return storage.url(asset.storage_key)[0]


def references(db, user_id, body, storage):
    """Person (or an approved earlier preview) first, then the pieces of the look."""
    assets = owned_inputs(db, user_id, body.inputAssets.model_dump())
    products = [a for a in assets if a.role == "product"]
    if not products:
        raise DomainError("PREVIEW_INPUT_MISSING", "Add at least one product photo.", 422)
    if body.baseAssetId:
        base = db.scalar(
            select(Asset).where(
                Asset.id == body.baseAssetId, Asset.user_id == user_id, Asset.role == ROLE
            )
        )
        if not base:
            raise DomainError("INVALID_ASSET", "That preview is unavailable.", 404)
        return [media_url(storage, base), *[media_url(storage, a) for a in products]]
    person = [a for a in assets if a.role == "person"]
    if not person:
        raise DomainError("PREVIEW_INPUT_MISSING", "Add a photo of the model.", 422)
    return [media_url(storage, person[0]), *[media_url(storage, a) for a in products]]


async def preview(db, user_id, body):
    """Charge only for an image that actually came back."""
    from app.services import look_projects

    storage = Storage()
    # Checked before the paid call: a photo can never be generated into another user's project.
    project = look_projects.owned(db, user_id, body.projectId) if body.projectId else None
    image_urls = references(db, user_id, body, storage)
    data = await provider().generate(
        image_urls, compose(body.angle, bool(body.baseAssetId)), body.aspectRatio
    )
    price = settings().image_credits_per_generation
    if price:
        change(db, user_id, -price, 0, f"try-on:{body.idempotencyKey}", "look_preview")
    asset = store_asset(db, storage, user_id, ROLE, data, "look-preview.png")
    if project:
        look_projects.record(db, project, asset, body.angle)
    return {"asset": asset_view(asset, storage), "creditsCharged": price}
