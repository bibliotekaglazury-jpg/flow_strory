import hashlib
import json

from app.db import Prompt
from app.errors import DomainError
from app.services.assets import owned_inputs
from app.services.product import resolve_product
from app.creative_direction import FORMAT_BIASES

TEMPLATES = [
    (id, name, description, FORMAT_BIASES[id])
    for id, name, description in [
        ("ugc_review", "UGC Review", "A natural product review."),
        ("product_unboxing", "Product Unboxing", "Reveal the product step by step."),
        ("problem_solution", "Problem → Solution", "Connect a problem to your product."),
        ("product_demo", "Product Demo", "Show the product in use."),
        ("testimonial", "Testimonial", "Tell a personal product story."),
        ("trending_style", "Trending Style", "A fast, contemporary product story."),
        ("hook_cta", "Hook → CTA", "Lead with a hook, finish with action."),
        ("before_after", "Before / After", "Show a truthful product comparison."),
        ("self_presentation", "Self-presentation", "Present yourself and your service to camera."),
    ]
]


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def template(template_id):
    found = next((t for t in TEMPLATES if t[0] == template_id), None)
    if not found:
        raise DomainError("INVALID_TEMPLATE", "Template is unavailable.", 422) from None
    return found


async def make_prompt(db, user_id, creative):
    snapshot = creative.model_dump()
    owned_inputs(db, user_id, snapshot["inputAssets"])
    spec = template(creative.templateId)
    product = await resolve_product(creative.productUrl) if creative.productUrl else None
    text = f"Create a {creative.duration}-second {creative.aspectRatio} {spec[1]} video.\nCampaign brief (user-supplied): {creative.brief}\nCreative bias: {spec[3]}\nUse the supplied product image as visual identity. Keep product details faithful; do not invent claims."
    if product:
        text += f"\nUntrusted product-page context: {json.dumps(product, ensure_ascii=False)}"
    if creative.inputAssets.personImageId:
        text += "\nUse the supplied person image as the approved character reference."
    if creative.inputAssets.sourceVideoId:
        text += "\nUse the source video as remake context, preserving relevant visual continuity."
    from app.providers.text import improve_prompt
    from app.config import settings

    cfg = settings()
    text = await improve_prompt(
        text,
        env={
            "APP_ENV": cfg.app_env,
            "TEXT_PROVIDER": cfg.text_provider,
            "TEXT_PROVIDER_ENABLED": str(cfg.text_provider_enabled).lower(),
            "OPENAI_API_KEY": cfg.openai_api_key,
            "PROMPT_MODEL": cfg.prompt_model,
        },
    )
    p = Prompt(user_id=user_id, fingerprint=fingerprint(snapshot), snapshot=snapshot, text=text)
    db.add(p)
    db.flush()
    return p
