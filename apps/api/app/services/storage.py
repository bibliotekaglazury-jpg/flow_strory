import hashlib
import hmac
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

import boto3

from app.config import settings
from app.db import now
from app.errors import DomainError


class Storage:
    def __init__(self, cfg=None):
        self.cfg = cfg or settings()
        self.root = Path(self.cfg.storage_path).resolve()
        self.s3 = None
        if self.cfg.storage_mode != "local":
            self.s3 = boto3.client(
                "s3",
                endpoint_url=self.cfg.s3_endpoint_url,
                region_name=self.cfg.s3_region,
                aws_access_key_id=self.cfg.s3_access_key_id,
                aws_secret_access_key=self.cfg.s3_secret_access_key,
            )

    def put(self, key, data, mime):
        if self.s3:
            self.s3.put_object(Bucket=self.cfg.s3_bucket, Key=key, Body=data, ContentType=mime)
        else:
            path = self.path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def get(self, key):
        """The stored bytes, or None when nothing was uploaded under this key."""
        if self.s3:
            try:
                return self.s3.get_object(Bucket=self.cfg.s3_bucket, Key=key)["Body"].read()
            except self.s3.exceptions.NoSuchKey:
                return None
        path = self.path(key)
        return path.read_bytes() if path.is_file() else None

    def delete(self, key):
        if self.s3:
            self.s3.delete_object(Bucket=self.cfg.s3_bucket, Key=key)
        else:
            self.path(key).unlink(missing_ok=True)

    def promote(self, source, target):
        """Moves a verified staging upload to its permanent key; the staging URL can no
        longer change what the asset points at."""
        if self.s3:
            self.s3.copy_object(
                Bucket=self.cfg.s3_bucket,
                Key=target,
                CopySource={"Bucket": self.cfg.s3_bucket, "Key": source},
            )
            self.s3.delete_object(Bucket=self.cfg.s3_bucket, Key=source)
        else:
            destination = self.path(target)
            destination.parent.mkdir(parents=True, exist_ok=True)
            self.path(source).replace(destination)

    def upload_url(self, key, content_type, upload_id, expires_in):
        """A short-lived PUT target for one staging key: S3 presigned, or the local signed
        endpoint, whose capability is the signed upload id itself."""
        if self.s3:
            url = self.s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": self.cfg.s3_bucket, "Key": key, "ContentType": content_type},
                ExpiresIn=expires_in,
            )
        else:
            url = f"{self.cfg.public_api_url}/api/uploads/{quote(upload_id)}"
        return url, {"Content-Type": content_type}

    def path(self, key):
        result = (self.root / key).resolve()
        if not result.is_relative_to(self.root):
            raise DomainError("NOT_FOUND", "Asset unavailable.", 404) from None
        return result

    def signature(self, key, expires):
        return hmac.new(
            self.cfg.storage_signing_secret.encode(), f"{key}:{expires}".encode(), hashlib.sha256
        ).hexdigest()

    def url(self, key):
        expiry = now() + timedelta(minutes=15)
        if self.s3:
            url = self.s3.generate_presigned_url(
                "get_object", Params={"Bucket": self.cfg.s3_bucket, "Key": key}, ExpiresIn=900
            )
        else:
            expires = int(expiry.timestamp())
            url = f"{self.cfg.public_api_url}/api/media/{quote(key)}?expires={expires}&signature={self.signature(key, expires)}"
        return url, expiry.isoformat()

    def provider_url(self, key, mime_type=None):
        if self.s3:
            return self.url(key)
        # Provider fetchers can reject opaque, short-lived URLs even when their MIME header is correct.
        # Give them a conventional filename and enough time for asynchronous ingestion.
        expiry = now() + timedelta(hours=2)
        expires = int(expiry.timestamp())
        extension = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/webp": "webp",
            "image/gif": "gif",
            "video/mp4": "mp4",
        }.get(mime_type, "bin")
        origin = (self.cfg.provider_asset_origin or self.cfg.public_api_url).rstrip("/")
        url = (
            f"{origin}/api/provider-media/{quote(key)}/reference.{extension}"
            f"?expires={expires}&signature={self.signature(key, expires)}"
        )
        return url, expiry.isoformat()

    def verify(self, key, expires, signature):
        if (
            self.cfg.app_env != "development"
            or self.cfg.storage_mode != "local"
            or expires < time.time()
            or not hmac.compare_digest(self.signature(key, expires), signature)
        ):
            raise DomainError("FORBIDDEN", "Asset link is invalid or expired.", 403) from None
        return self.path(key)


def asset_view(asset, storage):
    url, expires = storage.url(asset.storage_key)
    return {
        "id": asset.id,
        "role": asset.role,
        "kind": "image" if asset.mime_type.startswith("image/") else "video",
        "mimeType": asset.mime_type,
        "fileName": asset.file_name,
        "sizeBytes": asset.size_bytes,
        "url": url,
        "urlExpiresAt": expires,
        "width": asset.width,
        "height": asset.height,
        "durationSeconds": asset.duration_seconds,
        "createdAt": asset.created_at.isoformat(),
    }
