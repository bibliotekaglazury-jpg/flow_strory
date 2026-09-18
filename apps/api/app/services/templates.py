"""Current generative product-template catalog."""

import re
from pathlib import Path

from app.errors import DomainError

ROOT = Path(__file__).resolve().parents[4]
PUBLIC_FIELDS = (
    "id",
    "slug",
    "version",
    "name",
    "description",
    "category",
    "templateType",
    "thumbnail",
    "previewVideo",
    "enabled",
    "featured",
    "tags",
    "supportedAspectRatios",
    "supportedDurations",
    "inputSchema",
    "useCases",
)


def records():
    from app.services.prompts import TEMPLATES

    categories = [
        "UGC",
        "Product",
        "Explainers",
        "Product",
        "Testimonials",
        "Social Ads",
        "Hooks",
        "Before / After",
        "Social Ads",
    ]
    use_cases = [
        ["ugc", "organic-social"],
        ["product-showcase"],
        ["paid-ads"],
        ["product-showcase"],
        ["ugc", "paid-ads"],
        ["organic-social", "paid-ads"],
        ["paid-ads"],
        ["product-showcase"],
        ["paid-ads", "organic-social"],
    ]
    legacy = [
        dict(
            id=t[0],
            slug=t[0].replace("_", "-"),
            version="1",
            name=t[1],
            description=t[2],
            category=categories[index],
            templateType="generative",
            thumbnail=f"/templates/style-{index + 1}.svg",
            previewVideo=None,
            enabled=True,
            featured=True,
            tags=["ugc"],
            supportedAspectRatios=["9:16", "1:1", "16:9"],
            supportedDurations=[15, 20, 30],
            useCases=use_cases[index],
            inputSchema={
                "type": "object",
                "properties": {
                    "productImage": {"type": "string", "format": "asset-id", "mediaType": "image"},
                    "productUrl": {"type": "string", "format": "uri"},
                    "personImage": {"type": "string", "format": "asset-id", "mediaType": "image"},
                    "sourceVideo": {"type": "string", "format": "asset-id", "mediaType": "video"},
                },
                "additionalProperties": False,
            },
        )
        for index, t in enumerate(TEMPLATES)
    ]
    return legacy


def get_template(template_id):
    found = next((t for t in records() if t["id"] == template_id and t["enabled"]), None)
    if not found:
        raise DomainError("INVALID_TEMPLATE", "Template is unavailable.", 422)
    return found


def is_remotion(template_id):
    return get_template(template_id)["templateType"] == "remotion"


def alias(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")


def media_kind(field, schema):
    value = str(schema.get("mediaType", "")) + " " + str(schema.get("format", "")) + " " + field.lower()
    if "image" in value:
        return "image"
    if "video" in value:
        return "video"
    return None


def input_types(record):
    kinds = set()
    for field, prop in record.get("inputSchema", {}).get("properties", {}).items():
        name = field.lower()
        if name in {"producturl", "product_url"}:
            kinds.add("product-url")
        elif name in {"productimage", "productimageid", "product_image"}:
            kinds.add("product-image")
        elif name in {"personimage", "personimageid", "avatar", "person", "avatarimage"}:
            kinds.add("person-image")
        elif media_kind(field, prop) == "video":
            kinds.add("existing-video")
        elif media_kind(field, prop) == "image":
            kinds.add("images")
    return kinds or {"text-only"}


def matches(record, filters):
    filters = dict(filters)
    if filters.get("enabled") is None:
        filters["enabled"] = True
    for key, value in filters.items():
        if value is None or value == "":
            continue
        if key == "search":
            haystack = " ".join([record["name"], record["description"], *record.get("tags", [])]).lower()
            if str(value).lower() not in haystack:
                return False
        elif key in {"category", "templateType"}:
            if alias(record.get(key, "")) != alias(value):
                return False
        elif key == "aspectRatio" and value not in record["supportedAspectRatios"]:
            return False
        elif key == "duration":
            durations = record["supportedDurations"]
            if not any(
                (
                    d <= 15
                    if value == "up-to-15"
                    else d == 20
                    if value == "20"
                    else d >= 30
                    if value == "30-plus"
                    else str(d) == str(value)
                )
                for d in durations
            ):
                return False
        elif key == "inputType":
            if value not in input_types(record):
                return False
        elif key == "useCase" and alias(value) not in {alias(v) for v in record.get("useCases", [])}:
            return False
        elif key in {"featured", "enabled"} and record.get(key, False) != (
            value is True or str(value).lower() == "true"
        ):
            return False
    return True


def public_catalog(**filters):
    return [
        {
            **{k: t.get(k) for k in PUBLIC_FIELDS},
            "thumbnailUrl": t.get("thumbnail"),
            "available": t["enabled"],
            "unavailableReason": None if t["enabled"] else "Template verification pending.",
        }
        for t in records()
        if matches(t, filters)
    ]


def definition_fingerprint(record):
    from app.services.prompts import fingerprint

    source = record.get("source", {})
    return fingerprint(
        {
            "id": record["id"],
            "version": record.get("version"),
            "sourceHash": source.get("adaptedSha256") or source.get("sha256"),
            "inputSchema": record.get("inputSchema"),
            "remotion": record.get("remotion"),
            "supportedDurations": record.get("supportedDurations"),
            "supportedAspectRatios": record.get("supportedAspectRatios"),
        }
    )
