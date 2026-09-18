"""Creative Director planning eval over real offers. Never generates video or spends video credits.

Runs the real context pipeline (URL fetch, page evidence, image attachments, Claude
planning) without the HTTP layer or database, then records everything needed to judge
offer understanding, role handling, factual discipline and spoken register.

    cd apps/api && .venv/bin/python ../../scripts/chat/eval-creative-director.py --preflight
    cd apps/api && .venv/bin/python ../../scripts/chat/eval-creative-director.py --case 1
    cd apps/api && .venv/bin/python ../../scripts/chat/eval-creative-director.py --all
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "apps/api"))

from app.config import Settings  # noqa: E402
from app.creative_direction import FORMAT_BIASES, DirectorAnswer  # noqa: E402
from app.errors import DomainError  # noqa: E402
from app.providers.claude import ClaudeCreativeDirectorAdapter  # noqa: E402
from app.services.chat_context import bundle, enrich, image_attachment  # noqa: E402

OUTPUT = REPO / ".local/creative-director-eval"

CASES = [
    {
        "id": 1,
        "name": "Ecommerce product",
        "url": "https://medivon.pl/produkt/masazer-limfatyczny-medivon-lumina-do-nog/",
        "brief": "wypromuj ten produkt po polsku, szukam nowych klientów",
        "format": "auto",
        "expected": "Lymphatic leg massager, not generic wellness. Only page-backed claims.",
    },
    {
        "id": 2,
        "name": "Professional medical B2B product",
        "url": (
            "https://air-essence.store/produkt/"
            "air-essence-ultralite-l4-aparat-usg-profesjonalny-przenosny-ultrasonograf/"
        ),
        "brief": "wypromuj produkt dla lekarzy i gabinetów, szukam nowych klientów",
        "format": "auto",
        "expected": "Sell the device, never ultrasound examination services.",
    },
    {
        "id": 3,
        "name": "Course",
        "url": "https://www.britishcouncil.pl/angielski/online",
        "brief": "stwórz reklamę kursu angielskiego online dla dorosłych w Polsce",
        "format": "auto",
        "expected": "Course logic, speaking confidence. No invented discounts or guarantees.",
    },
    {
        "id": 4,
        "name": "Local specialist",
        "url": (
            "https://booksy.com/pl-pl/"
            "324027_grzegorz-masuje-gabinet-warszawa-ursus_masaz_3_warszawa"
        ),
        "brief": "jestem masażystą, chcę więcej klientów lokalnie",
        "format": "auto",
        "expected": "Local service booking ad: trust, relief, appointment CTA.",
    },
    {
        "id": 5,
        "name": "SaaS B2B",
        "url": "https://www.getnextflow.pl/",
        "brief": "wypromuj CRM dla małych firm w Polsce",
        "format": "auto",
        "expected": "B2B SaaS: Excel chaos, follow-up pain, Polish business context.",
    },
    {
        "id": 6,
        "name": "Tourism experience",
        "url": "https://foodtourkrakow.com/tours",
        "brief": "promote this Krakow food tour to tourists",
        "format": "auto",
        "expected": "Tourism experience: local tasting, storytelling, booking CTA.",
    },
    {
        "id": 7,
        "name": "Product image only",
        "images": [("product", "https://medivon.pl/wp-content/uploads/2026/02/2-scaled.jpg")],
        "brief": "wypromuj ten produkt, format UGC Review, po polsku",
        "format": "ugc_review",
        "expected": "Infer the visible product; invent no technical specifications.",
    },
    {
        "id": 8,
        "name": "Massage photo only",
        "images": [
            (
                "product",
                "https://images.squarespace-cdn.com/content/v1/5ebdf5dbe0fcab25340140d9/"
                "1602131381393-YRPV1U0T4DPXV18WO3MM/image-asset.jpeg",
            )
        ],
        "brief": "jestem masażystką, chcę krótką reklamę na Instagram",
        "format": "auto",
        "expected": "Service ad, not a product ad.",
    },
    {
        "id": 9,
        "name": "Person image plus device offer",
        "images": [
            (
                "person",
                "https://images.hulilabs.com/huli/doctor/photo/24062019/72110/"
                "e5734007395f09af75bc9ebb117762d5.jpg",
            )
        ],
        "brief": "reklamuję przenośny aparat USG dla gabinetów",
        "format": "auto",
        "expected": "Person is actor reference only; the offer stays the device.",
    },
    # New niches, 2026-09-12 second pass: no URL (facts supplied directly, research
    # declined) so these don't depend on inventing or fetching a real external site.
    {
        "id": 10,
        "name": "Apparel — recycled sneakers",
        "brief": (
            "Sprzedaję buty sportowe z recyklingowanego plastiku z oceanu, marka Fale. "
            "Fakty: cena 349 zł, dostępne w 5 kolorach, każda para to około 8 plastikowych "
            "butelek, dostawa 2 dni w Polsce. Nie szukaj, nie badaj, masz już wszystko "
            "czego potrzebujesz. Zrób 15-sekundową reklamę UGC."
        ),
        "format": "auto",
        "expected": "Specific brand/material facts, no invented eco-claims beyond supplied facts.",
    },
    {
        "id": 11,
        "name": "Home goods — custom wardrobe installer",
        "brief": (
            "I run a custom walk-in closet and wardrobe installation business for "
            "apartments in London. Facts: free in-home measurement visit, installation "
            "takes one day, starts at £1200, 5-year warranty on hardware. Do not "
            "research, you already have enough. Make a 15-second ad."
        ),
        "format": "auto",
        "expected": "Before/after or demo logic, real price/warranty facts, no fake reviews.",
    },
    {
        "id": 12,
        "name": "Pet care — mobile dog grooming",
        "brief": (
            "Prowadzę mobilny salon groomerski dla psów, przyjeżdżam do klienta pod dom. "
            "Fakty: cena od 120 zł zależnie od rasy, umawianie przez WhatsApp, obsługuję "
            "Wrocław i okolice. Nie szukaj, nie badaj. Zrób reklamę."
        ),
        "format": "auto",
        "expected": "Local service booking ad, trust/convenience, no fake before/after claims.",
    },
    {
        "id": 13,
        "name": "Fintech — budgeting app",
        "brief": (
            "I market a personal budgeting app called Ledger Lite. Facts: free tier "
            "tracks up to 3 accounts, premium is $4.99/month, no bank credentials "
            "required (manual entry or CSV import), available on iOS and Android. Do "
            "not research, you have enough facts. Make a 15-second ad targeting people "
            "who feel anxious about money."
        ),
        "format": "auto",
        "expected": (
            "Emotional relief framing without fake financial outcomes/savings numbers; "
            "no claim the app connects to banks since it explicitly does not."
        ),
    },
    {
        "id": 14,
        "name": "Automotive — mobile detailing",
        "brief": (
            "Mam firmę detailingową, jeżdżę do klienta i czyszczę auto na miejscu. "
            "Fakty: pakiet podstawowy 250 zł, trwa 2 godziny, używam tylko środków "
            "bezpiecznych dla lakieru, obsługuję Kraków. Nie szukaj, nie badaj. Zrób "
            "krótką reklamę na Instagram."
        ),
        "format": "hook_cta",
        "expected": "Strong single hook, one CTA, real price/duration, explicit format honored.",
    },
    {
        "id": 15,
        "name": "Kids/toys — STEM subscription box (testimonial, no source)",
        "brief": (
            "I sell a monthly educational STEM toy subscription box for kids ages 6-10, "
            "called Curiosity Crate. Facts: $24.99/month, cancel anytime, ships in the "
            "US only, each box has one science experiment kit plus an activity guide. "
            "Do not research. Make a 15-second ad aimed at parents."
        ),
        "format": "testimonial",
        "expected": (
            "Testimonial format requested with no supplied quote/source — must become a "
            "parent/creator impression, never a fabricated customer testimonial."
        ),
    },
    # Phase 1.5 extended eval: narrative/hybrid categories, where the failure mode is
    # selling the wrong value (the artefact instead of the story) rather than bad craft.
    {
        "id": 16,
        "name": "Book — illustrated edition (the Alice case)",
        "brief": (
            "wypromuj ksiazke w nowej niezwyklej kolorowej edycji alicja w krainie czarów. "
            "Nie szukaj, nie badaj."
        ),
        "format": "auto",
        "expected": (
            "Must create desire to read/continue the story; illustrations are secondary "
            "value, never the only payoff. No invented plot or edition details."
        ),
    },
    {
        "id": 17,
        "name": "Book as a gift",
        "brief": (
            "Sprzedaję ilustrowane wydanie baśni w twardej oprawie, głównie kupowane na "
            "prezent dla dzieci. Fakty: 240 stron, twarda oprawa, wstążka-zakładka, cena "
            "89 zł. Nie szukaj, nie badaj. Zrób reklamę."
        ),
        "format": "auto",
        "expected": (
            "Gifting plus narrative value; must land as a gift someone will read, not a "
            "decorative object and not a spec list."
        ),
    },
    {
        "id": 18,
        "name": "Collector's edition",
        "brief": (
            "I sell a numbered collector's edition of a cult sci-fi novel: 500 copies, "
            "signed by the illustrator, foil-stamped slipcase, £75. Do not research. "
            "Make a 15-second ad."
        ),
        "format": "auto",
        "expected": (
            "Collectible aesthetic and narrative value together; scarcity is real (500 "
            "copies) so it may be used, but the story must still be the reason to own it."
        ),
    },
    {
        "id": 19,
        "name": "Content subscription — audio drama",
        "brief": (
            "Promuję subskrypcję z audiobookami i słuchowiskami: nowy odcinek co tydzień, "
            "29 zł miesięcznie, można anulować w każdej chwili, słucha się w aplikacji. "
            "Nie szukaj, nie badaj. Zrób reklamę."
        ),
        "format": "auto",
        "expected": (
            "Recurring discovery plus narrative immersion; must give a reason to come "
            "back weekly, not explain the tariff."
        ),
    },
]


async def fetch_image(url):
    from app.services.product import download_public

    data, _, _ = await download_public(url, 10 * 1024 * 1024, "image/*")
    return data


async def build_context(case):
    """Real pipeline: page fetch and evidence extraction, or real downloaded imagery."""
    context = {
        "templateId": case["format"],
        "aspectRatio": "9:16",
        "brief": case["brief"],
        "productUrl": case.get("url"),
        "priorConcepts": [],
        "excludedMechanisms": [],
    }
    notes = []
    if case.get("url"):
        context = await enrich(context, [], allow_research=True)
    else:
        context = {**context, "page": None, "images": [], "pageStatus": "not_requested"}
    assets = []
    for role, image_url in case.get("images", []):
        try:
            data = await fetch_image(image_url)
        except DomainError as exc:
            notes.append(f"image {role} unavailable: {exc.code}")
            continue
        context["images"] = context.get("images", []) + [image_attachment(data, role)]
        assets.append(
            {
                "id": f"eval-{role}",
                "role": role,
                "mimeType": "image/png",
                "width": None,
                "height": None,
                "durationSeconds": None,
            }
        )
    messages = [{"role": "user", "text": case["brief"]}]
    context_bundle = bundle(context, messages, assets)
    context["contextBundle"] = context_bundle.model_dump()
    context["formatBias"] = FORMAT_BIASES[context_bundle.selectedFormat]
    return context, messages, context_bundle, notes


def observation(case, context, context_bundle, result, notes):
    record = {
        "case": case["id"],
        "name": case["name"],
        "brief": case["brief"],
        "expected": case["expected"],
        "requestedFormat": case["format"],
        "pageStatus": context.get("pageStatus"),
        "pageFailure": context.get("pageFailure"),
        "pageTitle": (context.get("page") or {}).get("title"),
        "sourceFactChars": sum(len(f.text) for f in context_bundle.sourceFacts),
        "imagesSent": len(context.get("images", [])),
        "notes": notes,
    }
    if result is None:
        return record
    answer = result.answer
    audit = result.audit or {}
    record["clarificationRequested"] = answer.assessment == "clarification_needed"
    record["clarificationQuestion"] = answer.clarificationQuestion
    record["researchUsed"] = audit.get("researchUsed")
    record["sourceDomains"] = audit.get("sourceDomains")
    record["playbookFormat"] = audit.get("playbookFormat")
    record["referenceStructureIds"] = audit.get("referenceStructureIds")
    record["qualityGatePassed"] = audit.get("qualityGatePassed")
    record["usage"] = result.usage
    creative = audit.get("creative") or {}
    if creative.get("candidates"):
        selected = next(
            (c for c in creative["candidates"] if c["id"] == creative.get("selectedId")), None
        )
        record["candidateMechanisms"] = [c["mechanism"] for c in creative["candidates"]]
        record["scores"] = selected["scores"] if selected else None
        record["selectedSummary"] = selected["summary"] if selected else None
    if isinstance(answer, DirectorAnswer) and answer.creativePlan:
        plan = answer.creativePlan
        clip = answer.videoPlan.clips[0]
        record.update(
            {
                "offer": plan.offer,
                "audience": plan.audience,
                "objective": plan.objective,
                "selectedFormat": plan.selectedFormat,
                "creativeMechanism": plan.creativeMechanism,
                "hookStrategy": plan.hookStrategy,
                "coreTension": plan.coreTension,
                "concept": plan.creativeAngle,
                "productPresentation": plan.productPresentation,
                "language": plan.language,
                "spokenLanguage": plan.spokenLanguage,
                "characters": answer.videoPlan.characters,
                "story": clip.narrativePurpose,
                "spokenScript": clip.spokenScript,
                "visualDirection": clip.visualDirection,
                "beats": [f"{b.start:g}-{b.end:g}s {b.action}" for b in clip.beats],
                "productRules": answer.videoPlan.productRules,
                "negativeRules": answer.videoPlan.negativeRules,
            }
        )
    record["assistantMessage"] = answer.assistantMessage
    return record


async def run_case(case, timeout):
    cfg = Settings().model_copy(update={"claude_timeout_seconds": timeout})
    adapter = ClaudeCreativeDirectorAdapter(cfg)
    context, messages, context_bundle, notes = await build_context(case)
    result, error = None, None
    try:
        result = await adapter.send_message(f"eval-{case['id']}", None, messages, context)
    except DomainError as exc:
        error = {"code": exc.code, "message": exc.message}
    record = observation(case, context, context_bundle, result, notes)
    if error:
        record["error"] = error
    return record


async def preflight():
    """Free check: does the real pipeline resolve every source before any paid planning?"""
    for case in CASES:
        line = {"case": case["id"], "name": case["name"]}
        if case.get("url"):
            try:
                context = await enrich(
                    {"productUrl": case["url"], "templateId": case["format"], "aspectRatio": "9:16"},
                    [],
                    allow_research=True,
                )
                page = context.get("page") or {}
                line["pageStatus"] = context.get("pageStatus")
                line["pageFailure"] = context.get("pageFailure")
                line["title"] = (page.get("title") or "")[:90]
                line["textChars"] = len(page.get("text") or "")
                line["structuredBlocks"] = len(page.get("structuredData") or [])
                line["pageImages"] = len(context.get("images") or [])
            except DomainError as exc:
                line["pageStatus"] = "error"
                line["pageFailure"] = exc.code
        for role, url in case.get("images", []):
            try:
                data = await fetch_image(url)
                line[f"image_{role}"] = f"{len(data)} bytes"
            except DomainError as exc:
                line[f"image_{role}"] = f"FAILED {exc.code}"
        print(json.dumps(line, ensure_ascii=False))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--case", type=int, action="append")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--timeout", type=int, default=280)
    args = parser.parse_args()
    if args.preflight:
        await preflight()
        return
    selected = [c for c in CASES if args.all or (args.case and c["id"] in args.case)]
    if not selected:
        raise SystemExit("Choose --preflight, --case N or --all")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for case in selected:
        record = await run_case(case, args.timeout)
        path = OUTPUT / f"case-{case['id']}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        summary = {
            key: record.get(key)
            for key in (
                "case",
                "pageStatus",
                "clarificationRequested",
                "selectedFormat",
                "creativeMechanism",
                "error",
            )
        }
        print(json.dumps(summary, ensure_ascii=False))


asyncio.run(main())
