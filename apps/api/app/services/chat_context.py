"""Read owned references and public page content for the existing conversation."""

import asyncio
import json
import logging
import re
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from app.config import settings

from bs4 import BeautifulSoup
from PIL import Image, ImageOps

from app.errors import DomainError
from urllib.parse import urljoin

from app.services.product import download_public
from app.services.storage import Storage

log = logging.getLogger(__name__)


MAX_PAGE_EVIDENCE_CHARS = 12_000
# Vision analysis only; stored originals stay untouched and remain the generation inputs.
VISION_MAX_EDGE = 1024


# The Messages API has no video content block, so sampled frames are the only way the
# director can actually look at an uploaded video instead of just knowing one exists.
VIDEO_FRAMES = 3
FRAME_ROLE = "source video frame"


def _video_seconds(path):
    try:
        probe = subprocess.run(
            [settings().ffprobe_path, "-v", "error", "-show_format", "-of", "json", str(path)],
            capture_output=True,
            check=True,
            timeout=30,
        )
        return float(json.loads(probe.stdout)["format"]["duration"])
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        pass
    # ffprobe is not guaranteed to sit beside ffmpeg; read the duration ffmpeg itself prints.
    try:
        report = subprocess.run(
            [settings().ffmpeg_path, "-nostdin", "-i", str(path), "-f", "null", "-"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    found = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", report.stderr)
    if not found:
        return None
    return int(found[1]) * 3600 + int(found[2]) * 60 + float(found[3])


def video_frames(path, count=VIDEO_FRAMES):
    """Evenly spaced stills, skipping the very start and end where black frames live.

    Extraction failure never fails the turn: the video still reaches generation as a
    reference, the director simply plans without having seen it.
    """
    seconds = _video_seconds(path)
    marks = (
        [seconds * (index + 1) / (count + 1) for index in range(count)] if seconds else [1.0]
    )
    frames = []
    for mark in marks:
        try:
            shot = subprocess.run(
                [
                    settings().ffmpeg_path,
                    "-nostdin",
                    "-ss",
                    f"{mark:g}",
                    "-i",
                    str(path),
                    "-frames:v",
                    "1",
                    "-f",
                    "image2",
                    "-vcodec",
                    "png",
                    "-",
                ],
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            break
        if shot.returncode == 0 and shot.stdout:
            frames.append(shot.stdout)
    return frames


def image_attachment(data, role, label=None):
    from app.services.assets import inspect_media

    inspect_media(data, "product")
    with Image.open(BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((VISION_MAX_EDGE, VISION_MAX_EDGE))
        output = BytesIO()
        image.save(output, format="PNG")
    return {"role": role, "data": output.getvalue(), "label": label}


def _sampled_frames(storage, reference):
    """Frames for one uploaded video; any failure yields nothing rather than raising."""
    try:
        if storage.s3:
            with tempfile.NamedTemporaryFile(suffix=".mp4") as file:
                storage.s3.download_fileobj(storage.cfg.s3_bucket, reference["key"], file)
                file.flush()
                frames = video_frames(file.name)
        else:
            path = Path(storage.path(reference["key"]))
            frames = video_frames(path) if path.exists() else []
        log.info(
            "video_frames_extracted",
            extra={"assetId": reference.get("key"), "framesExtracted": len(frames)},
        )
        return [image_attachment(frame, FRAME_ROLE) for frame in frames]
    except (OSError, DomainError, ValueError):
        log.info(
            "video_frames_extraction_failed", extra={"assetId": reference.get("key")}
        )
        return []


async def enrich(context, references, *, allow_research=False):
    storage = Storage()

    async def still(reference):
        if storage.s3:
            data, _, _ = await download_public(storage.url(reference["key"])[0], 10 * 1024 * 1024, "image/*")
        else:
            try:
                data = await asyncio.to_thread(storage.path(reference["key"]).read_bytes)
            except OSError:
                raise DomainError(
                    "INVALID_ASSET", "Upload this image again; the file is unavailable.", 404
                ) from None
        return await asyncio.to_thread(image_attachment, data, reference["role"], reference.get("label"))

    stills = [r for r in references if r["mime"].startswith("image/")]
    videos = [r for r in references if not r["mime"].startswith("image/") and r["role"] == "source_video"]
    # Stills download together; gather keeps upload order, which the director ranks by.
    attachments = list(await asyncio.gather(*(still(r) for r in stills)))
    # Stills the user uploaded rank above sampled frames, which rank above page imagery.
    for reference in videos:
        attachments.extend(await asyncio.to_thread(_sampled_frames, storage, reference))
    page = None
    if context.get("productUrl"):
        # Fetch the page itself; extraction transports evidence, the model interprets it.
        try:
            data, mime, final = await download_public(context["productUrl"])
        except DomainError as exc:
            # Validation (including private addresses and unsafe redirects) always fails closed.
            if not allow_research or exc.code == "INVALID_PRODUCT_URL":
                raise
            return {
                **context,
                "page": None,
                "images": attachments,
                "pageStatus": "failed",
                "pageFailure": exc.code,
            }
        if "text/html" not in mime:
            raise DomainError("INVALID_PRODUCT_URL", "Use a product or service webpage.", 422)
        soup = BeautifulSoup(data, "html.parser")
        structured = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"})[:8]:
            raw = script.get_text()[:12000]
            try:
                value = json.loads(raw)
            except (ValueError, RecursionError):
                continue
            if isinstance(value, (dict, list)):
                structured.append(value)
        for element in soup(["script", "style", "noscript", "nav", "footer"]):
            element.decompose()
        page = {
            "url": final,
            "structuredData": structured,
            "text": soup.get_text(" ", strip=True)[:24000],
            "title": soup.title.get_text(" ", strip=True)[:1500] if soup.title else None,
        }
        # Main product photography supplies visual identity for URL-only briefs.
        image_meta = soup.find("meta", attrs={"property": "og:image"})
        image_url = urljoin(final, str(image_meta.get("content", ""))) if image_meta else None
        if image_url:
            try:
                image, _, _ = await download_public(image_url, 10 * 1024 * 1024, "image/*")
                attachments.append(await asyncio.to_thread(image_attachment, image, "product page image"))
            except DomainError:
                page["imageUnavailable"] = True
    return {
        **context,
        "page": page,
        "images": attachments,
        "pageStatus": ("partial" if page.get("imageUnavailable") else "resolved")
        if page
        else "not_requested",
    }


def page_evidence(page):
    """Keep the highest-value page evidence within one bounded model payload."""
    if not page.get("title") and not page.get("structuredData"):
        return page.get("text", "")[:MAX_PAGE_EVIDENCE_CHARS]
    parts = []
    if page.get("title"):
        parts.append("Page title: " + page["title"])
    if page.get("structuredData"):
        parts.append(
            "Structured page data: "
            + json.dumps(page["structuredData"], ensure_ascii=False)[:6_000]
        )
    if page.get("text"):
        parts.append("Page text: " + page["text"])
    return "\n".join(parts)[:MAX_PAGE_EVIDENCE_CHARS]


def bundle(context, messages, assets):
    """Normalize existing resolver evidence, without keyword/industry classification."""
    from app.creative_direction import ContextBundle

    page = context.get("page")
    return ContextBundle(
        userText=messages[-1]["text"],
        brief=context.get("brief", ""),
        productUrl=context.get("productUrl"),
        selectedFormat=context["templateId"],
        aspectRatio=context["aspectRatio"],
        requestedLanguage=context.get("language") or None,
        preferredMechanism=context.get("preferredMechanism") or None,
        availableAssets=assets,
        offer=page.get("title") if page else None,
        sourceFacts=[
            {
                "source": page["url"],
                "text": page_evidence(page),
            }
        ]
        if page
        else [],
        missingFacts=["Product page could not be retrieved."]
        if context.get("pageStatus") == "failed"
        else [],
        priorConcepts=context.get("priorConcepts", []),
        conversation=[{"role": m["role"], "text": m["text"]} for m in messages[-12:]],
    )
