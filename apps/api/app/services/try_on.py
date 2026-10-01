"""Still look preview: one synchronous provider call, no job, quote or worker.

The video route is deliberately untouched. That pipeline exists because a render takes
minutes and has to survive restarts; a preview answers within one request, so reserving
credits and polling a job would only make a fast thing feel slow.
"""

from sqlalchemy import select

from app.config import settings
from app.db import Asset, uid
from app.errors import DomainError
from app.prompts.tryon import compose
from app.providers.mock import MockImageProvider
from app.providers.openrouter_image import OpenRouterImageProvider
from app.services import karma
from app.services.assets import owned_inputs, store_asset
from app.services.credits import account, change
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


class Failed:
    """A service try-on whose provider call failed. The route answers with the error but
    still commits, so the reservation's failure is recorded rather than rolled back."""

    def __init__(self, error):
        self.error = error


async def preview(db, user_id, body, reservation=None):
    """Charge only for an image that actually came back.

    Retry-safe end to end, not just on the credit ledger: a repeated request with the
    same idempotencyKey (e.g. the client never saw the first response) returns the photo
    already generated instead of paying the provider again and creating a duplicate asset.
    The account row lock (same one credits.change() takes) serializes this per user, the
    same way generations.create() already does - a second request for this account blocks
    until the first commits, then sees its result via the idempotency_key lookup below
    instead of racing it into the paid provider call. The normal 4-angle shoot is already
    sequential from the client, so this costs real concurrency only on an actual double-submit.

    The price is reserved before the provider is called and refunded if the call raises,
    so an account that cannot pay never reaches the paid provider. A Karma service request
    (reservation set) was already paid for in Karma: it is recorded, never debited here.
    """
    from app.services import look_projects

    account(db, user_id)
    key = f"try-on:{body.idempotencyKey}"
    storage = Storage()
    existing = db.scalar(select(Asset).where(Asset.user_id == user_id, Asset.idempotency_key == key))
    if existing:
        return {"asset": asset_view(existing, storage), "creditsCharged": 0}
    # Checked before the paid call: a photo can never be generated into another user's project.
    project = look_projects.owned(db, user_id, body.projectId) if body.projectId else None
    image_urls = references(db, user_id, body, storage)
    # Ledger keys are global, so they carry the user: two accounts may reuse a client key.
    ledger_key = f"try-on:{user_id}:{body.idempotencyKey}"
    attempt = uid()
    price = 0
    if reservation is not None:
        karma.claim(db, user_id, reservation)
    else:
        config = settings()
        price = config.image_credits_per_generation
        if not price and config.app_env != "development":
            raise DomainError("PREVIEW_UNAVAILABLE", "Look previews are not priced yet.", 503)
        if price:
            change(db, user_id, -price, price, f"{ledger_key}:reserve:{attempt}", "look_preview_reserve")
    try:
        data = await provider().generate(
            image_urls, compose(body.angle, bool(body.baseAssetId)), body.aspectRatio
        )
    except Exception as exc:
        if reservation is not None:
            # Committed with the claim, so Karma's reconciliation reads "failed" and refunds.
            karma.photo_failed(db, user_id, reservation)
            return Failed(exc)
        if price:
            change(db, user_id, price, -price, f"{ledger_key}:refund:{attempt}", "look_preview_refund")
        raise
    except BaseException:
        if price:
            change(db, user_id, price, -price, f"{ledger_key}:refund:{attempt}", "look_preview_refund")
        raise
    if price:
        change(db, user_id, 0, -price, ledger_key, "look_preview")
    asset = store_asset(db, storage, user_id, ROLE, data, "look-preview.png", idempotency_key=key)
    if reservation is not None:
        karma.photo_result(db, user_id, reservation, asset.id)
    if project:
        look_projects.record(db, project, asset, body.angle)
    return {"asset": asset_view(asset, storage), "creditsCharged": price}
