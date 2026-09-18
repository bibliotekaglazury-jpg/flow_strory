from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select

from app.db import Asset, uid
from app.errors import DomainError
from app.services.product import download_public, resolve_product

ROLES = {"productImageId": "product", "personImageId": "person", "sourceVideoId": "source_video"}


def input_asset_ids(inputs) -> set[str]:
    """Every asset id in an inputAssets payload, items included.

    Callers used to read the payload's scalar values directly, which broke as soon as
    items (a list) joined the same dict.
    """
    ids = {inputs.get(field) for field in ROLES}
    ids |= {item["assetId"] for item in inputs.get("items") or []}
    return {identifier for identifier in ids if identifier}


LIBRARY_LIMIT = 60


def library(db, user_id, role, source):
    """The user's own earlier uploads of one role from one module, newest first.

    Scoped by source so a module never surfaces photos uploaded somewhere else (the
    Create screen's uploads stay part of its own history, not this list).
    """
    return list(
        db.scalars(
            select(Asset)
            .where(Asset.user_id == user_id, Asset.role == role, Asset.source == source)
            .order_by(Asset.created_at.desc())
            .limit(LIBRARY_LIMIT)
        )
    )


def owned_inputs(db, user_id, inputs):
    result = []
    for field, role in ROLES.items():
        value = inputs.get(field)
        if not value:
            continue
        asset = db.scalar(select(Asset).where(Asset.id == value, Asset.user_id == user_id))
        if not asset or asset.role != role:
            raise DomainError("INVALID_ASSET", "Input asset is unavailable.", 404) from None
        result.append(asset)
    # Look items are ordinary product images, so they pass the same ownership and role
    # check; only their count and per-request label differ.
    for item in inputs.get("items") or []:
        asset = db.scalar(
            select(Asset).where(Asset.id == item["assetId"], Asset.user_id == user_id)
        )
        if not asset or asset.role != "product":
            raise DomainError("INVALID_ASSET", "Input asset is unavailable.", 404) from None
        result.append(asset)
    return result


def inspect_media(data, role):
    if role in {"product", "person", "thumbnail", "tryon_photo"}:
        if len(data) > 10 * 1024 * 1024:
            raise DomainError("UPLOAD_TOO_LARGE", "Image limit is 10 MB.", 413) from None
        try:
            with Image.open(BytesIO(data)) as im:
                if im.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError()
                mime = Image.MIME[im.format]
                width, height = im.size
                im.verify()
            return mime, width, height, None
        except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError):
            raise DomainError("INVALID_MEDIA", "Upload a valid PNG, JPEG, or WebP image.", 415) from None
    if role not in {"source_video", "output_video"}:
        raise DomainError("INVALID_ROLE", "Unsupported asset role.", 422) from None
    if len(data) > 500 * 1024 * 1024:
        raise DomainError("UPLOAD_TOO_LARGE", "Video limit is 500 MB.", 413) from None
    import json
    import subprocess
    import tempfile
    from app.config import settings

    with tempfile.NamedTemporaryFile(suffix=".media") as file:
        file.write(data)
        file.flush()
        try:
            probe = subprocess.run(
                [
                    settings().ffprobe_path,
                    "-v",
                    "error",
                    "-count_frames",
                    "-show_format",
                    "-show_streams",
                    "-of",
                    "json",
                    file.name,
                ],
                capture_output=True,
                timeout=60,
                check=True,
            )
            info = json.loads(probe.stdout)
            stream = next(s for s in info["streams"] if s["codec_type"] == "video")
            if int(stream.get("nb_read_frames", "0")) < 1:
                raise ValueError()
            fmt = info["format"]["format_name"]
            mime = "video/webm" if "webm" in fmt else "video/mp4" if "mp4" in fmt or "mov" in fmt else None
            if not mime:
                raise ValueError()
            return mime, int(stream["width"]), int(stream["height"]), float(info["format"]["duration"])
        except FileNotFoundError:
            return inspect_with_ffmpeg(file.name)
        except (subprocess.SubprocessError, ValueError, KeyError, StopIteration):
            raise DomainError("INVALID_MEDIA", "Upload a valid MP4, MOV, or WebM video.", 415) from None


def inspect_with_ffmpeg(path):
    """Decode one actual frame using an explicitly installed external FFmpeg."""
    import re
    import subprocess
    from app.config import settings

    try:
        result = subprocess.run(
            [
                settings().ffmpeg_path,
                "-nostdin",
                "-protocol_whitelist",
                "file,pipe",
                "-i",
                path,
                "-map",
                "0:v:0",
                "-frames:v",
                "1",
                "-an",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        output = result.stderr
        format_match = re.search(r"Input #0, ([^\n]+), from", output)
        duration = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", output)
        size = re.search(r"Video:[^\n]*?\b(\d{2,5})x(\d{2,5})\b", output)
        if not format_match or not duration or not size:
            raise ValueError()
        fmt = format_match.group(1)
        mime = "video/webm" if "webm" in fmt else "video/mp4" if "mp4" in fmt or "mov" in fmt else None
        if not mime:
            raise ValueError()
        seconds = int(duration[1]) * 3600 + int(duration[2]) * 60 + float(duration[3])
        return mime, int(size[1]), int(size[2]), seconds
    except FileNotFoundError:
        raise DomainError(
            "MEDIA_VALIDATION_UNAVAILABLE", "Video validation is not configured.", 503, True
        ) from None
    except (subprocess.SubprocessError, ValueError, KeyError, StopIteration):
        raise DomainError("INVALID_MEDIA", "Upload a valid MP4, MOV, or WebM video.", 415) from None


def store_rendered_asset(
    db, storage, user_id, role, data, file_name, key, mime, width, height, duration
):
    """A server-rendered output whose media facts are already known and whose storage key
    the caller chose (for example users/{userId}/subtitle-projects/.../exports/{exportId}/)."""
    storage.put(key, data, mime)
    asset = Asset(
        user_id=user_id,
        role=role,
        mime_type=mime,
        file_name=Path(file_name or "asset").name[:255],
        size_bytes=len(data),
        storage_key=key,
        width=width,
        height=height,
        duration_seconds=duration,
    )
    db.add(asset)
    db.flush()
    return asset


CATALOG_IMPORT_MAX_ROWS = 30


async def import_catalog_csv(db, storage, user_id, rows):
    """Bulk-populates the try-on product library from a CSV of product pages or direct
    image URLs. Each row is independent: a bad URL is recorded as an error and does not
    fail the rest of the batch, since a real catalog export always has a few dead links.
    Reuses the exact resolve -> download -> store_asset chain the single-URL
    /api/product/resolve route already uses (app/main.py:278-293), just looped."""
    if len(rows) > CATALOG_IMPORT_MAX_ROWS:
        raise DomainError(
            "CATALOG_IMPORT_TOO_LARGE",
            f"Import up to {CATALOG_IMPORT_MAX_ROWS} rows at a time.",
            422,
        )
    created, errors = [], []
    for index, row in enumerate(rows):
        url = (row.get("url") or "").strip()
        image_url = (row.get("imageUrl") or "").strip()
        try:
            if not url and not image_url:
                raise DomainError("CATALOG_ROW_INVALID", "Each row needs a url or an imageUrl.", 422)
            if not image_url:
                resolved = await resolve_product(url)
                image_url = resolved.get("imageUrl")
                if not image_url:
                    raise DomainError(
                        "CATALOG_ROW_INVALID", "No product image could be found at this URL.", 422
                    )
            data, _, _ = await download_public(image_url, 10 * 1024 * 1024, "image/*")
            asset = store_asset(db, storage, user_id, "product", data, row.get("name") or "catalog-product")
            asset.source = "try_on"
            db.flush()
            created.append(asset)
        except DomainError as exc:
            errors.append({"row": index + 1, "message": exc.message})
    return created, errors


def store_asset(db, storage, user_id, role, data, file_name, idempotency_key=None):
    mime, width, height, duration = inspect_media(data, role)
    key = f"{user_id}/{uid()}"
    storage.put(key, data, mime)
    a = Asset(
        user_id=user_id,
        role=role,
        mime_type=mime,
        file_name=Path(file_name or "asset").name[:255],
        size_bytes=len(data),
        storage_key=key,
        width=width,
        height=height,
        duration_seconds=duration,
        idempotency_key=idempotency_key,
    )
    db.add(a)
    db.flush()
    return a
