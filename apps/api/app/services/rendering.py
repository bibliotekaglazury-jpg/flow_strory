"""Safe owned-input boundary and deterministic renderer invocation."""

import asyncio
import json
import tempfile
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.db import Asset
from app.errors import DomainError
from app.services.templates import ROOT, get_template, media_kind


def validate_inputs(db, user_id, template, values):
    values = values or {}
    schema = template["inputSchema"]
    props = schema.get("properties", {})
    if (
        not isinstance(values, dict)
        or set(values) - set(props)
        or any(k not in values for k in schema.get("required", []))
    ):
        raise DomainError("INVALID_TEMPLATE_INPUT", "Complete the template input fields.", 422)
    assets = {}
    for key, value in values.items():
        prop = props[key]
        if (
            prop.get("type") != "string"
            or not isinstance(value, str)
            or len(value) > prop.get("maxLength", 4000)
            or len(value) < prop.get("minLength", 0)
        ):
            raise DomainError("INVALID_TEMPLATE_INPUT", "Template input is invalid.", 422)
        if prop.get("enum") and value not in prop["enum"]:
            raise DomainError("INVALID_TEMPLATE_INPUT", "Template input is invalid.", 422)
        kind = media_kind(key, prop)
        if kind:
            asset = db.scalar(select(Asset).where(Asset.id == value, Asset.user_id == user_id))
            if (
                not asset
                or not asset.mime_type.startswith(kind + "/")
                or asset.role not in {"product", "person", "source_video"}
            ):
                raise DomainError("INVALID_ASSET", "Input asset is unavailable.", 404)
            assets[key] = asset
    return assets


def validate_render(db, user_id, estimate):
    template = get_template(estimate.templateId)
    if (
        estimate.duration not in template["supportedDurations"]
        or estimate.aspectRatio not in template["supportedAspectRatios"]
    ):
        raise DomainError("UNSUPPORTED_CONFIGURATION", "Template does not support these settings.", 422)
    if (
        estimate.model != "auto"
        or estimate.voice != "auto"
        or estimate.quality not in (None, "auto")
        or estimate.resolution
    ):
        raise DomainError(
            "UNSUPPORTED_CONFIGURATION", "Advanced generation settings do not apply to this template.", 422
        )
    validate_inputs(db, user_id, template, estimate.normalizedInputs)
    return template


async def render(snapshot, assets, storage):
    cfg = settings()
    with tempfile.TemporaryDirectory(prefix="ugc-render-") as directory:
        folder = Path(directory)
        values = dict(snapshot.get("normalizedInputs") or {})
        for key, asset in assets.items():
            suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(
                asset.mime_type, ".mp4"
            )
            target = folder / (key + suffix)
            if storage.s3:
                storage.s3.download_file(storage.cfg.s3_bucket, asset.storage_key, str(target))
            else:
                target.write_bytes(storage.path(asset.storage_key).read_bytes())
            values[key] = str(target)
        inputs, output = folder / "inputs.json", folder / "output.mp4"
        inputs.write_text(json.dumps(values))
        process = await asyncio.create_subprocess_exec(
            cfg.render_node_path,
            "--import",
            "tsx",
            "scripts/templates/render-rve.ts",
            "--template",
            snapshot["templateId"],
            "--input",
            str(inputs),
            "--output",
            str(output),
            "--duration",
            str(snapshot["duration"]),
            "--aspect-ratio",
            snapshot["aspectRatio"],
            cwd=ROOT,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            await asyncio.wait_for(process.wait(), timeout=cfg.render_timeout_seconds)
            if process.returncode != 0:
                raise RuntimeError("Renderer failed")
            return output.read_bytes(), output.with_suffix(".webp").read_bytes()
        finally:
            if process.returncode is None:
                import os
                import signal

                os.killpg(process.pid, signal.SIGKILL)
                await process.wait()
