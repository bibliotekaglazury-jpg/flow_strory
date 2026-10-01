import base64
import json
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete as sa_delete, or_, select

from app.config import settings
from app.db import Asset, Generation, Job, Output, Prompt, Quote, now, uid
from app.errors import DomainError
from app.providers import GenerationInput, build_registry, route_model
from app.schemas import Creative, Estimate
from app.services import karma
from app.services.assets import owned_inputs
from app.services.credits import TERMINAL, account, finish, reserve
from app.services.prompts import fingerprint
from app.services.templates import get_template, is_remotion, definition_fingerprint
from app.services.rendering import validate_render, validate_inputs
from types import SimpleNamespace
from app.services.storage import Storage, asset_view


def registry():
    env = dict(os.environ)
    env.setdefault("APP_ENV", settings().app_env)
    env.setdefault("VIDEO_PROVIDER", settings().video_provider)
    env.setdefault("OPENROUTER_API_KEY", settings().openrouter_api_key)
    env.setdefault("OPENROUTER_VIDEO_ENABLED", str(settings().openrouter_video_enabled).lower())
    env.setdefault("OPENROUTER_VIDEO_MODEL", settings().openrouter_video_model)
    env.setdefault("VIDEO_CREDITS_PER_SECOND", str(settings().video_credits_per_second))
    return build_registry(env)


def provider_input(snapshot, assets, storage, prompt=None):
    return GenerationInput(
        prompt=prompt or snapshot.get("prompt") or "Capability validation",
        duration_seconds=snapshot["duration"],
        aspect_ratio=snapshot["aspectRatio"],
        reference_image_urls=tuple(
            (
                storage.provider_url(a.storage_key, a.mime_type)
                if hasattr(storage, "provider_url")
                else storage.url(a.storage_key)
            )[0]
            for a in assets
            if a.mime_type.startswith("image/")
        ),
        reference_video_urls=tuple(
            (
                storage.provider_url(a.storage_key, a.mime_type)
                if hasattr(storage, "provider_url")
                else storage.url(a.storage_key)
            )[0]
            for a in assets
            if a.role == "source_video"
        ),
        has_person=bool(snapshot["inputAssets"].get("personImageId")),
        quality=snapshot.get("quality", "auto"),
        resolution=snapshot.get("resolution"),
        voice=snapshot.get("voice", "auto"),
    )


def validate_estimate(db, user_id, estimate):
    spec = get_template(estimate.templateId)
    assets = owned_inputs(db, user_id, estimate.inputAssets.model_dump())
    if spec["templateType"] == "remotion":
        validate_render(db, user_id, estimate)
        return SimpleNamespace(id="render_only"), estimate.duration * max(
            0, settings().render_only_credits_per_second
        )
    prompt = db.scalar(select(Prompt).where(Prompt.id == estimate.promptId, Prompt.user_id == user_id))
    if not prompt:
        raise DomainError("INVALID_PROMPT", "Generate a current prompt first.", 409) from None
    source = prompt.snapshot
    for field in ("templateId", "duration", "aspectRatio", "inputAssets", "productUrl"):
        if source.get(field) != estimate.model_dump().get(field):
            raise DomainError("STALE_PROMPT", "Generate a new prompt after changing inputs.", 409) from None
    request = provider_input(estimate.model_dump(), assets, Storage(), prompt.text)
    model = route_model(registry(), request, estimate.model)
    return model, model.estimate_cost(request)


def estimate_fingerprint(estimate):
    value = estimate.model_dump()
    spec = get_template(estimate.templateId)
    if spec["templateType"] == "remotion":
        value["renderDefinitionFingerprint"] = definition_fingerprint(spec)
    return fingerprint(value)


def quote(db, user_id, estimate):
    selected, cost = validate_estimate(db, user_id, estimate)
    q = Quote(
        user_id=user_id,
        fingerprint=estimate_fingerprint(estimate),
        amount=cost,
        selected_model=selected.id,
        expires_at=now() + timedelta(minutes=10),
    )
    db.add(q)
    db.flush()
    return q


def owned_generation(db, user_id, generation_id, lock=False):
    query = select(Generation).where(Generation.id == generation_id, Generation.user_id == user_id)
    if lock:
        query = query.with_for_update()
    g = db.scalar(query)
    if not g:
        raise DomainError("NOT_FOUND", "Generation is unavailable.", 404) from None
    return g


def create(db, user_id, body, key, reservation=None):
    """Admits a paid video start. A Karma service request (reservation set) was already
    paid for in Karma, so it is recorded against the reservation and reserves nothing here;
    its zero estimate makes the worker's settlement a no-op on UGC credits."""
    if not key or len(key) > 200:
        raise DomainError("INVALID_IDEMPOTENCY_KEY", "Provide a valid Idempotency-Key.", 400) from None
    snapshot = body.model_dump()
    digest = fingerprint(snapshot)
    # Serialize per-user admission before reading idempotency; same-key requests see the committed predecessor.
    account(db, user_id)
    prior = db.scalar(
        select(Generation).where(Generation.user_id == user_id, Generation.idempotency_key == key)
    )
    if prior:
        if prior.request_hash != digest:
            raise DomainError(
                "IDEMPOTENCY_CONFLICT", "This request key was already used for different inputs.", 409
            ) from None
        return prior
    estimate = Estimate.model_validate({k: v for k, v in snapshot.items() if k in Estimate.model_fields})
    selected, cost = validate_estimate(db, user_id, estimate)
    if not is_remotion(body.templateId):
        prompt = db.get(Prompt, body.promptId)
        creative = Creative.model_validate({k: v for k, v in snapshot.items() if k in Creative.model_fields})
        if prompt.fingerprint != fingerprint(creative.model_dump()):
            raise DomainError("STALE_PROMPT", "Generate a new prompt after changing inputs.", 409) from None
    q = db.scalar(select(Quote).where(Quote.id == body.quoteId, Quote.user_id == user_id).with_for_update())
    if (
        not q
        or q.accepted
        or q.expires_at.replace(tzinfo=UTC) < now()
        or q.fingerprint != estimate_fingerprint(estimate)
        or q.amount != cost
        or q.selected_model != selected.id
    ):
        raise DomainError("STALE_QUOTE", "Refresh the credit estimate and submit again.", 409) from None
    if selected.id == "render_only":
        spec = get_template(body.templateId)
        snapshot["renderDefinitionFingerprint"] = definition_fingerprint(spec)
        snapshot["renderInputAssetIds"] = [
            a.id for a in validate_inputs(db, user_id, spec, body.normalizedInputs).values()
        ]
    if selected.id != "render_only" and prompt.recipe:
        snapshot["videoRecipe"] = prompt.recipe
        if prompt.snapshot.get("creativePlanning"):
            snapshot["creativePlanning"] = prompt.snapshot["creativePlanning"]
    g = Generation(
        id=uid(),
        user_id=user_id,
        snapshot=snapshot,
        request_hash=digest,
        idempotency_key=key,
        selected_model=selected.id,
        status="queued",
        estimated=0 if reservation is not None else q.amount,
        charged=0,
    )
    db.add(g)
    db.flush()
    if reservation is not None:
        karma.claim(db, user_id, reservation, g.id)
    else:
        reserve(db, g)
    db.add(Job(generation_id=g.id))
    db.info["wake_worker"] = True
    q.accepted = True
    db.flush()
    return g


def cancel(db, user_id, generation_id):
    # Same lock order as worker: generation then account; admission only holds account for new rows.
    g = owned_generation(db, user_id, generation_id, True)
    if g.status == "cancelled":
        return g
    if g.status in TERMINAL:
        raise DomainError("CANCELLATION_UNAVAILABLE", "This generation has already finished.", 409) from None
    job = db.scalar(select(Job).where(Job.generation_id == g.id).with_for_update())
    if job.submission_state != "pending" and g.selected_model != "render_only":
        raise DomainError(
            "CANCELLATION_UNAVAILABLE",
            "This generation has already been submitted and cannot be cancelled.",
            409,
        ) from None
    finish(db, g, "cancelled")
    job.submission_state = "done"
    return g


def delete(db, user_id, generation_id):
    """Removes one generation from the user's library. Only a terminal generation can be
    deleted — an in-flight one has a worker job actively leasing it, and deleting the row out
    from under that job would leave it working on nothing. Credits already charged are not
    refunded: deleting a library entry is not the same as never having rendered it. The output
    asset is left alone (it is a normal library asset, addressable on its own)."""
    g = owned_generation(db, user_id, generation_id, True)
    if g.status not in TERMINAL:
        raise DomainError("DELETE_UNAVAILABLE", "This generation is still in progress.", 409) from None
    db.execute(sa_delete(Output).where(Output.generation_id == g.id))
    db.execute(sa_delete(Job).where(Job.generation_id == g.id))
    db.delete(g)
    db.flush()


def view(db, g, storage=None):
    storage = storage or Storage()
    inputs = owned_inputs(db, g.user_id, g.snapshot["inputAssets"])
    if g.selected_model == "render_only":
        # Admitted media IDs are immutable history evidence; current schemas may have changed.
        render_assets = list(
            db.scalars(
                select(Asset).where(
                    Asset.user_id == g.user_id, Asset.id.in_(g.snapshot.get("renderInputAssetIds", []))
                )
            )
        )
        inputs = list({a.id: a for a in [*inputs, *render_assets]}.values())
    outputs = list(
        db.scalars(
            select(Asset).join(Output, Output.asset_id == Asset.id).where(Output.generation_id == g.id)
        )
    )
    s = g.snapshot
    return {
        "id": g.id,
        "userId": g.user_id,
        "templateId": s["templateId"],
        "model": s["model"],
        "provider": None,
        "status": g.status,
        "progress": g.progress,
        "prompt": s["prompt"],
        "normalizedInputs": s.get("normalizedInputs"),
        # Lets a finished video be recreated for a different offer with the same mechanism.
        "creativeMechanism": (
            (s.get("creativePlanning") or {}).get("creativePlan") or {}
        ).get("creativeMechanism"),
        "duration": s["duration"],
        "aspectRatio": s["aspectRatio"],
        "inputAssets": [asset_view(a, storage) for a in inputs],
        "outputAssets": [asset_view(a, storage) for a in outputs],
        "creditsEstimated": g.estimated,
        "creditsCharged": g.charged,
        "error": g.error,
        "createdAt": g.created_at.isoformat(),
        "updatedAt": g.updated_at.isoformat(),
    }


def history(db, user_id, limit, cursor):
    query = select(Generation).where(Generation.user_id == user_id)
    if cursor:
        try:
            created, id = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
            created = datetime.fromisoformat(created)
        except (ValueError, TypeError):
            raise DomainError("INVALID_CURSOR", "History cursor is invalid.", 400) from None
        query = query.where(
            or_(Generation.created_at < created, and_(Generation.created_at == created, Generation.id < id))
        )
    rows = list(
        db.scalars(query.order_by(Generation.created_at.desc(), Generation.id.desc()).limit(limit + 1))
    )
    more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        base64.urlsafe_b64encode(json.dumps([rows[-1].created_at.isoformat(), rows[-1].id]).encode())
        .decode()
        .rstrip("=")
        if more
        else None
    )
    return {"generations": [view(db, g) for g in rows], "nextCursor": next_cursor}
