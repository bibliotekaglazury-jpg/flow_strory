"""Direct upload: the client PUTs a file straight to storage, never through Karma or this API.

upload-url hands out a signed upload id bound to the subject, role, content type, declared
size and a staging key. upload-complete re-checks all of it against the stored bytes (owner,
exact size, real format by magic bytes, then the same media inspection as a form upload)
and only then moves the file to its permanent key and records the asset. Nothing is kept
in the database until completion, so an abandoned upload leaves only a staging object.
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.db import Asset, uid
from app.errors import DomainError
from app.services.assets import inspect_media
from app.services.credits import account

MB = 1024 * 1024
LIMITS = {"person": 10 * MB, "product": 10 * MB, "source_video": 500 * MB}
CONTENT_TYPES = {
    "person": {"image/png", "image/jpeg", "image/webp"},
    "product": {"image/png", "image/jpeg", "image/webp"},
    "source_video": {"video/mp4", "video/quicktime", "video/webm"},
}
# MP4 and QuickTime share the ISO base media container; browsers label the same file either way.
FAMILIES = {"video/quicktime": "video/mp4"}
TTL_SECONDS = 15 * 60
# A large video may finish its PUT right at expiry; completion stays possible a little longer.
COMPLETE_GRACE_SECONDS = 15 * 60
STAGING_PREFIX = "uploads"


def _signature(payload):
    secret = settings().storage_signing_secret.encode()
    return hmac.new(secret, b"direct-upload:" + payload, hashlib.sha256).hexdigest()


def _encode(claims):
    payload = base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode()).rstrip(b"=")
    return f"{payload.decode()}.{_signature(payload)}"


def decode(upload_id):
    """The claims of a genuine upload id; anything else reads as an unknown upload."""
    payload, _, signature = (upload_id or "").partition(".")
    if not payload or not hmac.compare_digest(_signature(payload.encode()), signature):
        raise DomainError("UPLOAD_NOT_FOUND", "That upload is unavailable.", 404) from None
    try:
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except ValueError:
        raise DomainError("UPLOAD_NOT_FOUND", "That upload is unavailable.", 404) from None


def owned(upload_id, user_id):
    claims = decode(upload_id)
    # Another subject's upload id is indistinguishable from one that never existed.
    if claims.get("u") != user_id:
        raise DomainError("UPLOAD_NOT_FOUND", "That upload is unavailable.", 404) from None
    return claims


def sniff(header):
    """The real format from the first bytes, independent of name or declared type."""
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "video/quicktime" if header[8:12] == b"qt  " else "video/mp4"
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    return None


def issue(storage, user_id, role, content_type, size, filename):
    if role not in LIMITS:
        raise DomainError("INVALID_ROLE", "Unsupported upload role.", 422) from None
    if content_type not in CONTENT_TYPES[role]:
        raise DomainError("UNSUPPORTED_MEDIA_TYPE", "This file type cannot be uploaded here.", 415) from None
    if size > LIMITS[role]:
        limit = "Video limit is 500 MB." if role == "source_video" else "Image limit is 10 MB."
        raise DomainError("UPLOAD_TOO_LARGE", limit, 413) from None
    identifier = uid()
    expires = int(time.time()) + TTL_SECONDS
    upload_id = _encode(
        {
            "u": user_id,
            "r": role,
            "c": content_type,
            "s": size,
            "i": identifier,
            "f": Path(filename or "upload").name[:255],
            "e": expires,
        }
    )
    url, headers = storage.upload_url(staging_key(user_id, identifier), content_type, upload_id, TTL_SECONDS)
    return {
        "uploadId": upload_id,
        "uploadUrl": url,
        "method": "PUT",
        "headers": headers,
        "expiresAt": datetime.fromtimestamp(expires, UTC).isoformat(),
    }


def staging_key(user_id, identifier):
    return f"{STAGING_PREFIX}/{user_id}/{identifier}"


async def receive(storage, upload_id, content_type, chunks):
    """The local-storage PUT target. S3 mode never reaches this: the client PUTs to S3."""
    claims = decode(upload_id)
    if claims["e"] < time.time():
        raise DomainError("UPLOAD_EXPIRED", "This upload link has expired. Request a new one.", 410) from None
    if content_type != claims["c"]:
        raise DomainError("UNSUPPORTED_MEDIA_TYPE", "Content-Type does not match the upload.", 415) from None
    data = bytearray()
    async for chunk in chunks:
        data.extend(chunk)
        if len(data) > claims["s"]:
            raise DomainError("UPLOAD_TOO_LARGE", "The file is larger than declared.", 413) from None
    storage.put(staging_key(claims["u"], claims["i"]), bytes(data), claims["c"])


def complete(db, storage, user_id, upload_id, source):
    claims = owned(upload_id, user_id)
    final_key = f"{user_id}/{claims['i']}"
    # Serializes completion per subject, so a double submit records the asset once.
    account(db, user_id)
    existing = db.scalar(select(Asset).where(Asset.user_id == user_id, Asset.storage_key == final_key))
    if existing:
        return existing
    staged = staging_key(user_id, claims["i"])
    if claims["e"] + COMPLETE_GRACE_SECONDS < time.time():
        storage.delete(staged)
        raise DomainError("UPLOAD_EXPIRED", "This upload has expired. Upload the file again.", 410) from None
    data = storage.get(staged)
    if data is None:
        raise DomainError("UPLOAD_MISSING", "Upload the file before completing it.", 409) from None
    try:
        if len(data) != claims["s"]:
            raise DomainError("UPLOAD_SIZE_MISMATCH", "The uploaded file does not match its size.", 422)
        detected = sniff(data[:16])
        if not detected or FAMILIES.get(detected, detected) != FAMILIES.get(claims["c"], claims["c"]):
            raise DomainError("INVALID_MEDIA", "The file content does not match its type.", 415)
        mime, width, height, duration = inspect_media(data, claims["r"])
    except DomainError:
        storage.delete(staged)
        raise
    storage.promote(staged, final_key)
    asset = Asset(
        user_id=user_id,
        role=claims["r"],
        source=source,
        mime_type=mime,
        file_name=claims["f"],
        size_bytes=len(data),
        storage_key=final_key,
        width=width,
        height=height,
        duration_seconds=duration,
    )
    db.add(asset)
    db.flush()
    return asset
