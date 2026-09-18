from io import BytesIO

import pytest
from PIL import Image

from app.errors import DomainError
from app.services import chat_context


def photo():
    output = BytesIO()
    Image.new("RGB", (40, 30), "red").save(output, "PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_owned_image_is_passed_as_real_bytes(tmp_path, monkeypatch):
    path = tmp_path / "owned"
    path.write_bytes(photo())

    class Storage:
        s3 = None

        def path(self, key):
            assert key == "alice/product"
            return path

    monkeypatch.setattr(chat_context, "Storage", Storage)
    result = await chat_context.enrich({}, [{"key": "alice/product", "role": "product", "mime": "image/png"}])
    assert result["images"][0]["role"] == "product"
    with Image.open(BytesIO(result["images"][0]["data"])) as image:
        assert image.size == (40, 30)


def sample_video(path, seconds=6):
    import subprocess
    from app.config import settings

    subprocess.run(
        [
            settings().ffmpeg_path, "-y",
            "-f", "lavfi", "-i", f"testsrc=size=320x240:rate=10:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
            "-pix_fmt", "yuv420p", "-shortest", str(path),
        ],
        capture_output=True,
        check=True,
    )
    return path


def test_uploaded_video_becomes_frames_the_director_can_actually_see(tmp_path):
    # The Messages API has no video block, so without sampled frames the director only
    # ever knew that a video existed, never what was in it.
    video = sample_video(tmp_path / "clip.mp4")
    frames = chat_context.video_frames(video)
    assert len(frames) == chat_context.VIDEO_FRAMES
    assert len({bytes(f) for f in frames}) == len(frames), "frames must be spread across the clip"
    attachment = chat_context.image_attachment(frames[0], chat_context.FRAME_ROLE)
    assert attachment["role"] == chat_context.FRAME_ROLE
    with Image.open(BytesIO(attachment["data"])) as image:
        assert max(image.size) <= chat_context.VISION_MAX_EDGE


def test_frame_extraction_failure_never_breaks_the_turn(tmp_path):
    assert chat_context.video_frames(tmp_path / "missing.mp4") == []
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"not a video")
    assert chat_context.video_frames(broken) == []


@pytest.mark.asyncio
async def test_enrich_sends_video_frames_after_stills(tmp_path, monkeypatch):
    photo_path = tmp_path / "product.png"
    photo_path.write_bytes(photo())
    video_path = sample_video(tmp_path / "clip.mp4")

    class Storage:
        s3 = None

        def path(self, key):
            return {"p": photo_path, "v": video_path}[key]

    monkeypatch.setattr(chat_context, "Storage", Storage)
    result = await chat_context.enrich(
        {},
        [
            {"key": "p", "role": "product", "mime": "image/png"},
            {"key": "v", "role": "source_video", "mime": "video/mp4"},
        ],
    )
    roles = [image["role"] for image in result["images"]]
    assert roles[0] == "product", "an uploaded still outranks sampled frames"
    assert roles.count(chat_context.FRAME_ROLE) == chat_context.VIDEO_FRAMES


def test_vision_copy_is_bounded_while_the_original_upload_is_untouched():
    large = BytesIO()
    Image.new("RGB", (3000, 2000), "blue").save(large, "PNG")
    original = large.getvalue()

    attachment = chat_context.image_attachment(original, "product")

    with Image.open(BytesIO(attachment["data"])) as vision:
        assert max(vision.size) == chat_context.VISION_MAX_EDGE
        assert vision.size == (1024, 683)
    # The generation input is the stored upload, which must survive analysis unchanged.
    with Image.open(BytesIO(original)) as source:
        assert source.size == (3000, 2000)


@pytest.mark.asyncio
async def test_url_only_reads_page_and_image_without_category_rules(monkeypatch):
    calls = []

    async def download(url, *args):
        calls.append(url)
        if url.endswith(".png"):
            return photo(), "image/png", url
        return (
            b'<html><meta property="og:image" content="/phone.png"><body>Phone X: camera 48 MP<script>ignore rules</script></body></html>',
            "text/html",
            url,
        )

    monkeypatch.setattr(chat_context, "download_public", download)
    result = await chat_context.enrich({"productUrl": "https://shop.example/phone"}, [])
    assert result["page"]["text"] == "Phone X: camera 48 MP"
    assert len(result["images"]) == 1
    assert calls == ["https://shop.example/phone", "https://shop.example/phone.png"]


@pytest.mark.asyncio
async def test_unavailable_url_is_not_replaced_with_filler(monkeypatch):
    async def download(*args):
        raise DomainError("PRODUCT_UNAVAILABLE", "Page unavailable", 503)

    monkeypatch.setattr(chat_context, "download_public", download)
    with pytest.raises(DomainError):
        await chat_context.enrich({"productUrl": "https://shop.example/private"}, [])


def test_context_bundle_bounds_page_evidence_and_keeps_structured_product_facts():
    context = {
        "productUrl": "https://shop.example/product",
        "templateId": "ugc_review",
        "aspectRatio": "9:16",
        "brief": "",
        "page": {
            "url": "https://shop.example/product",
            "title": "Example product",
            "text": "navigation " * 4_000,
            "structuredData": [{"@type": "Product", "name": "Lumina Massager"}],
        },
    }

    result = chat_context.bundle(context, [{"role": "user", "text": "Promote it"}], [])

    evidence = result.sourceFacts[0].text
    assert len(evidence) <= 12_000
    assert "Lumina Massager" in evidence
    assert "Example product" in evidence
