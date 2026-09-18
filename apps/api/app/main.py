from app import responses
import csv
import io
import logging
from uuid import uuid4
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy import text

from app.auth import identity
from app.config import settings
from app.chat_api import router as chat_router
from app.subtitles.routes import public_router as subtitle_public_router
from app.subtitles.routes import router as subtitle_router
from app.db import Subscription, engine, session
from app.errors import DomainError
from app.providers import ProviderError, public_models
from app.schemas import (
    LOOK_SIZE,
    Checkout,
    CreateGeneration,
    Creative,
    Estimate,
    LookProjectCreate,
    Resolve,
    TryOn,
)
from app.services import billing, generations, look_projects, try_on
from app.services import profile as profile_service
from app.services.assets import import_catalog_csv, store_asset
from app.services.credits import TERMINAL, account
from app.services.product import download_public, resolve_product
from app.services.prompts import make_prompt
from app.services.templates import public_catalog
from app.services.storage import Storage, asset_view

app = FastAPI(title="UGC API", version="0.1.0")
app.include_router(chat_router)
app.include_router(subtitle_router)
app.include_router(subtitle_public_router)
log = logging.getLogger("ugc.api")
# Default access logging includes signed media query strings; application events omit them.
logging.getLogger("uvicorn.access").disabled = True


def stored_media_type(path: Path) -> str:
    """Detect media stored under opaque keys so provider URLs carry a usable MIME type."""
    try:
        with path.open("rb") as source:
            header = source.read(16)
    except OSError:
        return "application/octet-stream"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "video/mp4"
    return "application/octet-stream"


@app.middleware("http")
async def request_context(request, call_next):
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "private, no-store"
    return response


@app.exception_handler(DomainError)
async def domain_error(request, exc):
    return JSONResponse(
        {"error": exc.public(), "requestId": getattr(request.state, "request_id", str(uuid4()))},
        status_code=exc.status,
    )


@app.exception_handler(ProviderError)
async def provider_error(request, exc):
    return await domain_error(
        request, DomainError(exc.code, exc.message, 503 if exc.retryable else 422, exc.retryable)
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return await domain_error(request, DomainError("INVALID_INPUT", "Request fields are invalid.", 422))


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    log.error(
        "request_failed",
        extra={"request_id": getattr(request.state, "request_id", ""), "exception_type": type(exc).__name__},
    )
    return await domain_error(
        request, DomainError("INTERNAL_ERROR", "The request could not be completed.", 500, True)
    )


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        raise DomainError("DATABASE_UNAVAILABLE", "Database unavailable.", 503, True) from None
    return {"status": "ok"}


@app.get("/api/templates", response_model=responses.TemplatesResponse)
def templates(
    search: str | None = None,
    category: str | None = None,
    templateType: str | None = None,
    aspectRatio: str | None = None,
    duration: str | None = None,
    inputType: str | None = None,
    useCase: str | None = None,
    featured: bool | None = None,
    enabled: bool | None = None,
    user=Depends(identity),
):
    return {
        "templates": public_catalog(
            search=search,
            category=category,
            templateType=templateType,
            aspectRatio=aspectRatio,
            duration=duration,
            inputType=inputType,
            useCase=useCase,
            featured=featured,
            enabled=enabled,
        )
    }


@app.get("/api/models", response_model=responses.ModelsResponse)
def models(user=Depends(identity)):
    return {"models": public_models(generations.registry())}


async def read_upload(file: UploadFile, limit: int) -> bytes:
    data = bytearray()
    while chunk := await file.read(1024 * 1024):
        data.extend(chunk)
        if len(data) > limit:
            raise DomainError("UPLOAD_TOO_LARGE", "Upload exceeds the size limit.", 413) from None
    return bytes(data)


ASSET_SOURCES = {"try_on"}


@app.get("/api/assets", response_model=responses.AssetsResponse)
def asset_library(
    role: str = Query(pattern="^(person|product)$"),
    source: str = Query(pattern="^try_on$"),
    user=Depends(identity),
    db=Depends(session),
):
    """Model photos and catalog-imported product photos this user uploaded in the
    Try-On module, so a new look can reuse one instead of re-uploading it."""
    from app.services.assets import library

    storage = Storage()
    return {"assets": [asset_view(a, storage) for a in library(db, user, role, source)]}


@app.post("/api/assets", response_model=responses.AssetResponse, status_code=201)
async def upload(
    file: UploadFile = File(),
    role: str = Form(),
    source: str | None = Form(default=None),
    user=Depends(identity),
    db=Depends(session),
):
    if role not in {"product", "person", "source_video"}:
        raise DomainError("INVALID_ROLE", "Unsupported upload role.", 422) from None
    if source is not None and source not in ASSET_SOURCES:
        raise DomainError("INVALID_SOURCE", "Unsupported upload source.", 422) from None
    data = await read_upload(file, (500 if role == "source_video" else 10) * 1024 * 1024)
    storage = Storage()
    asset = await run_in_threadpool(store_asset, db, storage, user, role, data, file.filename)
    if source:
        asset.source = source
        await run_in_threadpool(db.flush)
    return {"asset": asset_view(asset, storage)}


@app.post("/api/assets/bulk", response_model=responses.AssetsResponse, status_code=201)
async def upload_many(
    files: list[UploadFile] = File(),
    source: str | None = Form(default=None),
    user=Depends(identity),
    db=Depends(session),
):
    """Several product photos of one look in a single request.

    Product-only: a look is the one case where a user picks many files at once, and
    person/source_video are single-slot by nature.
    """
    if not files or len(files) > LOOK_SIZE:
        raise DomainError("INVALID_UPLOAD", f"Upload 1 to {LOOK_SIZE} product images.", 422) from None
    storage = Storage()
    assets = []
    for file in files:
        data = await read_upload(file, 10 * 1024 * 1024)
        asset = await run_in_threadpool(store_asset, db, storage, user, "product", data, file.filename)
        if source:
            asset.source = source
            await run_in_threadpool(db.flush)
        assets.append(asset)
    return {"assets": [asset_view(a, storage) for a in assets]}


@app.post("/api/assets/catalog-import", response_model=responses.CatalogImportResponse, status_code=201)
async def catalog_import(file: UploadFile = File(), user=Depends(identity), db=Depends(session)):
    """Bulk-populates the Try-On product library from a CSV of product pages or direct
    image URLs (columns: url and/or imageUrl, optional name). A bad row is reported, not
    fatal — a real store export always has a few dead links."""
    data = await read_upload(file, 1024 * 1024)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise DomainError("CATALOG_IMPORT_INVALID", "The CSV file could not be read.", 422) from None
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise DomainError("CATALOG_IMPORT_INVALID", "The CSV file has no rows.", 422) from None
    storage = Storage()
    created, errors = await import_catalog_csv(db, storage, user, rows)
    return {"created": [asset_view(a, storage) for a in created], "errors": errors}


@app.post("/api/try-on", response_model=responses.TryOnResponse, status_code=201)
async def look_preview(body: TryOn, user=Depends(identity), db=Depends(session)):
    return await try_on.preview(db, user, body)


@app.post("/api/look-projects", response_model=responses.LookProjectResponse, status_code=201)
def create_look_project(body: LookProjectCreate, user=Depends(identity), db=Depends(session)):
    return {"project": look_projects.create(db, user, body)}


@app.get("/api/look-projects", response_model=responses.LookProjectsResponse)
def list_look_projects(user=Depends(identity), db=Depends(session)):
    return {"projects": look_projects.summaries(db, user)}


@app.get("/api/look-projects/{project_id}", response_model=responses.LookProjectResponse)
def get_look_project(project_id: str, user=Depends(identity), db=Depends(session)):
    return {"project": look_projects.detail(db, look_projects.owned(db, user, project_id))}


@app.delete("/api/look-projects/{project_id}", status_code=204)
def delete_look_project(project_id: str, user=Depends(identity), db=Depends(session)):
    look_projects.delete(db, user, project_id)
    return Response(status_code=204)


@app.api_route("/api/media/{key:path}", methods=["GET", "HEAD"])
def media(key: str, expires: int, signature: str):
    path = Storage().verify(key, expires, signature)
    if not path.is_file():
        raise DomainError("NOT_FOUND", "Asset is unavailable.", 404) from None
    media_type = stored_media_type(path)
    filename = "generated-video.mp4" if media_type == "video/mp4" else None
    return FileResponse(path, media_type=media_type, filename=filename, content_disposition_type="inline")


@app.api_route("/api/provider-media/{resource:path}", methods=["GET", "HEAD"])
def provider_media(resource: str, expires: int, signature: str):
    key, separator, filename = resource.rpartition("/")
    if not separator or filename not in {
        "reference.png",
        "reference.jpg",
        "reference.webp",
        "reference.gif",
        "reference.mp4",
        "reference.bin",
    }:
        raise DomainError("NOT_FOUND", "Asset is unavailable.", 404) from None
    path = Storage().verify(key, expires, signature)
    if not path.is_file():
        raise DomainError("NOT_FOUND", "Asset is unavailable.", 404) from None
    return FileResponse(path, media_type=stored_media_type(path))


@app.post("/api/product/resolve", response_model=responses.ProductResponse)
async def product(body: Resolve, user=Depends(identity), db=Depends(session)):
    resolved = await resolve_product(body.url)
    asset = None
    if resolved.get("imageUrl"):
        try:
            data, _, _ = await download_public(resolved["imageUrl"], 10 * 1024 * 1024, "image/*")
            storage = Storage()
            item = await run_in_threadpool(
                store_asset, db, storage, user, "product", data, "product-page-image"
            )
            asset = asset_view(item, storage)
        except DomainError:
            # Page metadata remains useful when its preview image blocks retrieval.
            asset = None
    return {"product": resolved, "asset": asset}


@app.post("/api/prompts/generate", response_model=responses.PromptResponse)
async def prompt(body: Creative, user=Depends(identity), db=Depends(session)):
    p = await make_prompt(db, user, body)
    return {
        "promptId": p.id,
        "prompt": p.text,
        "inputFingerprint": p.fingerprint,
        "createdAt": p.created_at.isoformat(),
    }


@app.get("/api/credits", response_model=responses.CreditsResponse)
def credits(estimate: str | None = None, user=Depends(identity), db=Depends(session)):
    q = None
    if estimate:
        try:
            parsed = Estimate.model_validate_json(estimate)
        except ValidationError:
            raise DomainError("INVALID_INPUT", "Credit estimate fields are invalid.", 422) from None
        q = generations.quote(db, user, parsed)
    a = account(db, user)
    return {
        "balance": a.available,
        "quote": {"id": q.id, "creditsEstimated": q.amount, "expiresAt": q.expires_at.isoformat()}
        if q
        else None,
        "updatedAt": a.updated_at.isoformat(),
    }


@app.get("/api/profile", response_model=responses.ProfileResponse)
def profile(user=Depends(identity), db=Depends(session)):
    """One systematized view of everything under this account: imports, generations,
    try-on projects, subtitle projects and the credit ledger. Same user_id scoping every
    other route already enforces - this just totals it in one place."""
    return profile_service.summary(db, user)


@app.post("/api/generations", response_model=responses.GenerationResponse, status_code=202)
def create(
    body: CreateGeneration, idempotency_key: str = Header(), user=Depends(identity), db=Depends(session)
):
    return {"generation": generations.view(db, generations.create(db, user, body, idempotency_key))}


@app.get("/api/generations", response_model=responses.HistoryResponse)
def history(
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user=Depends(identity),
    db=Depends(session),
):
    return generations.history(db, user, limit, cursor)


@app.get("/api/generations/{generation_id}", response_model=responses.PollResponse)
def get_generation(generation_id: str, user=Depends(identity), db=Depends(session)):
    g = generations.owned_generation(db, user, generation_id)
    return {"generation": generations.view(db, g), "pollAfterMs": None if g.status in TERMINAL else 2000}


@app.post("/api/generations/{generation_id}/cancel", response_model=responses.GenerationResponse)
def cancel(generation_id: str, user=Depends(identity), db=Depends(session)):
    return {"generation": generations.view(db, generations.cancel(db, user, generation_id))}


@app.delete("/api/generations/{generation_id}", status_code=204)
def delete_generation(generation_id: str, user=Depends(identity), db=Depends(session)):
    generations.delete(db, user, generation_id)
    return Response(status_code=204)


@app.get("/api/billing/summary", response_model=responses.BillingSummary)
def billing_summary(user=Depends(identity), db=Depends(session)):
    sub = db.get(Subscription, user)
    return {
        "plan": sub.plan if sub else "free",
        "status": sub.status if sub else "inactive",
        "renewalDate": sub.renewal_at.isoformat() if sub and sub.renewal_at else None,
        "prices": [{"id": k, "label": v.get("label", k)} for k, v in billing.catalog().items()],
        "available": bool(settings().stripe_secret_key),
    }


@app.post("/api/billing/checkout", response_model=responses.CheckoutResponse, status_code=201)
def checkout(body: Checkout, user=Depends(identity), db=Depends(session)):
    return billing.checkout(db, user, body.priceId)


@app.post("/api/billing/portal", response_model=responses.PortalResponse, status_code=201)
def portal(user=Depends(identity), db=Depends(session)):
    return billing.portal(db, user)


@app.post("/api/webhooks/stripe", response_model=responses.WebhookResponse)
async def webhook(request: Request, stripe_signature: str | None = Header(default=None), db=Depends(session)):
    body = await request.body()
    if len(body) > 1024 * 1024:
        raise DomainError("PAYLOAD_TOO_LARGE", "Webhook exceeds size limit.", 413) from None
    event = billing.verify_event(body, stripe_signature)
    billing.apply_event(db, event, body)
    return {"received": True}
