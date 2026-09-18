"""Owned, bounded conversations. DB transactions never span model execution."""

import asyncio
import math
import time
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from sqlalchemy import select

from app.config import settings
from app.db import ChatRecipeVersion, ChatSession, Prompt, SessionLocal, now, uid
from app.errors import DomainError
from app.providers.chat import MockChatProvider
from app.services.assets import ROLES, input_asset_ids, owned_inputs
from app.services.prompts import fingerprint, template
from app.video_recipe import compile_recipe
from app.creative_direction import DirectorAnswer, PlannedAnswer, FORMAT_BIASES, normalize_answer
from app.services.chat_context import bundle


@lru_cache
def provider():
    cfg = settings()
    if cfg.app_env != "development":
        raise DomainError("CHAT_UNAVAILABLE", "Local conversation is unavailable here.", 503)
    if cfg.chat_provider == "mock":
        return MockChatProvider()
    if cfg.chat_provider == "claude":
        from app.providers.claude import ClaudeCreativeDirectorAdapter

        return ClaudeCreativeDirectorAdapter(cfg)
    if cfg.chat_provider == "deepseek":
        from app.providers.deepseek import DeepSeekCreativeDirectorAdapter

        return DeepSeekCreativeDirectorAdapter(cfg)
    raise DomainError("CHAT_UNAVAILABLE", "Conversation is not configured.", 503)


def owned(db, user, id):
    item = db.scalar(
        select(ChatSession).where(ChatSession.id == id, ChatSession.user_id == user).with_for_update()
    )
    if not item:
        raise DomainError("CHAT_NOT_FOUND", "Conversation is unavailable.", 404)
    return item


def prior_concepts(db, session_id, scope):
    versions = db.scalars(
        select(ChatRecipeVersion)
        .where(ChatRecipeVersion.session_id == session_id)
        .order_by(ChatRecipeVersion.revision.desc())
        .limit(24)
    ).all()
    concepts = []
    for version in reversed(versions):
        planning = version.recipe.get("planning") or {}
        plan = planning.get("creativePlan") or {}
        previous_scope = planning.get("contextFingerprint", "")
        if previous_scope != scope or not plan:
            continue
        concepts.append(
            {
                "revision": version.revision,
                "contextFingerprint": previous_scope,
                "mechanism": plan.get("creativeMechanism"),
                "summary": plan.get("creativeAngle") or version.recipe["concept"],
                "status": "selected",
            }
        )
    return concepts


def usage_charger(user, session_id, revision):
    """Commit each reservation before I/O; unknown costs survive failed turns/restarts."""
    reservation_key = f"{revision}:{uid()}"

    async def charge(reserved_cents, actual_cents=None):
        if (
            not math.isfinite(reserved_cents)
            or reserved_cents < 0
            or (actual_cents is not None and (not math.isfinite(actual_cents) or actual_cents < 0))
        ):
            raise DomainError("CHAT_BUDGET_EXCEEDED", "Invalid planning cost.", 503)
        with SessionLocal.begin() as db:
            item = owned(db, user, session_id)
            if item.revision != revision or item.status != "responding":
                raise DomainError("CHAT_CHANGED", "The conversation changed. Please reload it.", 409)
            usage = dict(item.planning_usage or {})
            reservations = dict(usage.get("reservations", {}))
            spent = float(usage.get("spentCents", 0))
            if actual_cents is not None:
                if reservation_key not in reservations:
                    raise DomainError("CHAT_FAILED", "Planning cost could not be reconciled.", 503)
                reservations.pop(reservation_key)
                spent += actual_cents
            else:
                if (
                    reservation_key in reservations
                    or spent + sum(reservations.values()) + reserved_cents
                    > settings().claude_session_budget_cents
                ):
                    raise DomainError("CHAT_BUDGET_EXCEEDED", "Conversation planning budget reached.", 409)
                reservations[reservation_key] = reserved_cents
            item.planning_usage = {"spentCents": spent, "reservations": reservations}

    return charge


def view(item):
    return {
        "id": item.id,
        "messages": item.messages,
        "answer": item.answer,
        "revision": item.revision,
        "status": item.status,
        "simulated": item.provider == "mock",
        "createdAt": item.created_at.isoformat(),
        "updatedAt": item.updated_at.isoformat(),
    }


async def create(user):
    adapter = provider()
    if not await adapter.health():
        raise DomainError("CHAT_UNAVAILABLE", "Local conversation is not ready. Check the local setup.", 503)
    thread = await adapter.create_thread()
    with SessionLocal.begin() as db:
        item = ChatSession(user_id=user, provider=adapter.key, provider_thread_id=thread)
        db.add(item)
        db.flush()
        return view(item)


def get(user, id):
    with SessionLocal.begin() as db:
        item = owned(db, user, id)
        if item.provider != provider().key:
            raise DomainError(
                "CHAT_PROVIDER_CHANGED", "Start a new conversation after changing local setup.", 409
            )
        stamp = item.updated_at.replace(tzinfo=UTC) if item.updated_at.tzinfo is None else item.updated_at
        if item.status == "responding" and stamp < datetime.now(UTC) - timedelta(
            seconds=settings().claude_timeout_seconds + 90 if item.provider == "claude" else 390
        ):
            item.status = "idle"
            item.revision += 1
        return view(item)


def with_enrich_timing(usage, enrich_ms):
    if enrich_ms is None or not isinstance(usage, dict):
        return usage
    return {**usage, "timingsMs": {**usage.get("timingsMs", {}), "enrich": enrich_ms}}


async def send(user, id, body):
    adapter = provider()
    with SessionLocal.begin() as db:
        item = owned(db, user, id)
        if item.provider != adapter.key:
            raise DomainError(
                "CHAT_PROVIDER_CHANGED", "Start a new conversation after changing local setup.", 409
            )
        if item.status == "responding":
            raise DomainError("CHAT_BUSY", "Wait for the current reply or reset the conversation.", 409)
        if len(item.messages) >= 40:
            raise DomainError("CHAT_LIMIT", "Start a new conversation to continue.", 409)
        if body.context.templateId != "auto":
            template(body.context.templateId)
        assets = owned_inputs(db, user, body.context.inputAssets.model_dump())
        labels = {item.assetId: item.label for item in body.context.inputAssets.items}
        references = [
            {
                "key": a.storage_key,
                "role": a.role,
                "mime": a.mime_type,
                "label": labels.get(a.id),
            }
            for a in assets
        ]
        context = body.context.model_dump()
        from app.services.templates import get_template

        context["templateName"] = (
            "Auto" if body.context.templateId == "auto" else get_template(body.context.templateId)["name"]
        )
        context["changeConcept"] = getattr(body, "intent", "message") == "change_concept"
        context["contextFingerprint"] = fingerprint(
            {key: context.get(key) for key in ("templateId", "productUrl", "brief", "inputAssets")}
        )
        context["priorConcepts"] = prior_concepts(db, id, context["contextFingerprint"])
        context["excludedMechanisms"] = (
            list(dict.fromkeys(p["mechanism"] for p in context["priorConcepts"] if p["mechanism"]))
            if context["changeConcept"]
            else []
        )
        asset_context = [
            {
                "id": a.id,
                "role": a.role,
                "mimeType": a.mime_type,
                "width": a.width,
                "height": a.height,
                "durationSeconds": a.duration_seconds,
                "label": labels.get(a.id),
            }
            for a in assets
        ]
        messages = item.messages + [
            {"id": uid(), "role": "user", "text": body.text, "createdAt": now().isoformat()}
        ]
        item.messages = messages
        item.status = "responding"
        item.updated_at = now()
        item.revision += 1
        revision, thread = item.revision, item.provider_thread_id
    enrich_ms = None
    try:
        if adapter.key != "mock":
            from app.services.chat_context import enrich

            options = {"allow_research": True} if adapter.key == "claude" else {}
            started = time.monotonic()
            context = await asyncio.wait_for(enrich(context, references, **options), timeout=60)
            enrich_ms = round((time.monotonic() - started) * 1000)
        context_bundle = bundle(context, messages, asset_context)
        context["contextBundle"] = context_bundle.model_dump()
        context["formatBias"] = FORMAT_BIASES[context_bundle.selectedFormat]
        if adapter.key in ("claude", "deepseek"):
            context["chargeUsage"] = usage_charger(user, id, revision)
        result = await asyncio.wait_for(
            adapter.send_message(id, thread, messages, context),
            # Provider-specific cap when the adapter has one (DeepSeek runs much slower
            # per call than Claude); falls back to the Claude default for mock/unknown.
            timeout=getattr(settings(), f"{adapter.key}_timeout_seconds", settings().claude_timeout_seconds),
        )
        thread, answer = result
        answer = (
            normalize_answer(answer, context_bundle)
            if isinstance(answer, DirectorAnswer)
            else PlannedAnswer.model_validate(answer.model_dump())
        )
        if answer.recipe:
            compile_recipe(answer.recipe)
        with SessionLocal.begin() as db:
            item = owned(db, user, id)
            if item.revision != revision:
                raise DomainError("CHAT_CHANGED", "The conversation changed. Please reload it.", 409)
            item.provider_thread_id = thread
            item.answer = answer.model_dump()
            if answer.recipe:
                db.add(
                    ChatRecipeVersion(
                        session_id=id,
                        revision=revision,
                        recipe={
                            **answer.recipe.model_dump(),
                            "planning": {
                                "version": "2",
                                "contextFingerprint": context["contextFingerprint"],
                                "creativeAudit": getattr(result, "audit", None),
                                "usage": with_enrich_timing(getattr(result, "usage", {}), enrich_ms),
                                "contextBundle": context_bundle.model_dump(),
                                "creativePlan": answer.creativePlan.model_dump()
                                if answer.creativePlan
                                else None,
                                "videoPlan": answer.videoPlan.model_dump() if answer.videoPlan else None,
                            },
                        },
                    )
                )
            item.messages = messages + [
                {
                    "id": uid(),
                    "role": "assistant",
                    "text": answer.assistantMessage,
                    "createdAt": now().isoformat(),
                }
            ]
            item.status = "idle"
            item.updated_at = now()
            return view(item)
    except BaseException as exc:
        await adapter.cancel(id)
        with SessionLocal.begin() as db:
            item = db.get(ChatSession, id)
            if item and item.user_id == user and item.revision == revision:
                item.status = "idle"
                item.updated_at = now()
        if isinstance(exc, TimeoutError):
            raise DomainError(
                "CHAT_TIMEOUT", "The creative director took too long. Please retry.", 504, True
            ) from None
        if isinstance(exc, (DomainError, asyncio.CancelledError)):
            raise
        raise DomainError(
            "CHAT_FAILED", "The reply could not be completed. Your message is saved.", 503, True
        ) from None


async def delete(user, id):
    with SessionLocal.begin() as db:
        item = owned(db, user, id)
        from sqlalchemy import delete as delete_rows

        db.execute(delete_rows(ChatRecipeVersion).where(ChatRecipeVersion.session_id == id))
        db.delete(item)
    await provider().cancel(id)
    return {"deleted": True}


def apply(user, id, body):
    with SessionLocal.begin() as db:
        item = owned(db, user, id)
        if item.status != "idle" or item.revision != body.revision or not item.answer:
            raise DomainError("STALE_RECIPE", "Review the latest recipe before applying.", 409)
        answer = PlannedAnswer.model_validate(item.answer)
        if answer.needsMoreInformation or not answer.recipe:
            raise DomainError("INCOMPLETE_RECIPE", "Answer the clarification first.", 409)
        version = db.scalar(
            select(ChatRecipeVersion).where(
                ChatRecipeVersion.session_id == id, ChatRecipeVersion.revision == body.revision
            )
        )
        if version is None:
            raise DomainError("STALE_RECIPE", "Review the latest recipe before applying.", 409)
        planning = version.recipe.get("planning")
        if planning and answer.creativePlan:
            selected = planning["contextBundle"]["selectedFormat"]
            if body.creative.templateId not in {selected, answer.creativePlan.selectedFormat}:
                raise DomainError(
                    "STALE_RECIPE", "The format changed. Ask the director to update the concept.", 409
                )
            planned_ids = {a["id"] for a in planning["contextBundle"]["availableAssets"]}
            current_ids = input_asset_ids(body.creative.inputAssets.model_dump())
            if planned_ids != current_ids:
                raise DomainError(
                    "STALE_RECIPE", "The images changed. Ask the director to update the concept.", 409
                )
        recipe = answer.recipe
        if settings().video_provider == "openrouter" and recipe.duration != 15:
            raise DomainError("UNSUPPORTED_DURATION", "Create a new 15-second plan.", 422)
        draft = body.creative.model_copy(
            update={
                "brief": recipe.concept,
                "templateId": answer.creativePlan.selectedFormat
                if answer.creativePlan
                else body.creative.templateId,
                "duration": recipe.duration,
                "aspectRatio": recipe.aspectRatio,
                "language": recipe.language,
            }
        )
        template(draft.templateId)
        owned_inputs(db, user, draft.inputAssets.model_dump())
        snapshot = draft.model_dump()
        prompt = Prompt(
            user_id=user,
            snapshot=snapshot,
            fingerprint=fingerprint(snapshot),
            recipe=recipe.model_dump(),
            text=compile_recipe(
                recipe,
                {"references": [k for k in ROLES if snapshot["inputAssets"].get(k)]},
            ),
        )
        if version and version.recipe.get("planning"):
            prompt.snapshot = {**snapshot, "creativePlanning": version.recipe["planning"]}
        db.add(prompt)
        db.flush()
        return {
            "creative": snapshot,
            "prompt": {
                "promptId": prompt.id,
                "prompt": prompt.text,
                "inputFingerprint": prompt.fingerprint,
                "createdAt": prompt.created_at.isoformat(),
            },
        }


async def apply_with_references(user, id, body):
    """Apply validated chat state without making the external product page a second time."""
    return apply(user, id, body)
