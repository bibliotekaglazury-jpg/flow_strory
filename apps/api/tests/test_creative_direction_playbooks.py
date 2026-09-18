import re
from collections import Counter

import pytest

from app.creative_direction import FORMAT_BIASES, CreativePlan, Format
from app.creative_direction_playbooks import (
    CATEGORY_OVERLAYS,
    CONSUMPTION_MODELS,
    FORMAT_PLAYBOOKS,
    NICHE_KEYWORDS,
    WINNING_AD_STRUCTURES,
    _fit_score,
    as_reference,
    category_overlay,
    evidence_available,
    format_index,
    matched_niches,
    retrieval_limit,
    select_structures,
)

MECHANISM_PATTERN = r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
FORMATS = set(Format.__args__)


def bundle(**changes):
    return {
        "product": None,
        "service": None,
        "offer": None,
        "userText": "",
        "brief": "",
        "availableAssets": [],
        "sourceFacts": [],
        **changes,
    }


def test_playbooks_cover_every_selectable_format_exactly():
    assert set(FORMAT_PLAYBOOKS) == FORMATS
    assert set(FORMAT_PLAYBOOKS) | {"auto"} == set(FORMAT_BIASES)


def test_seed_size_and_per_format_coverage():
    # Upper bound raised from 40 in Phase 1.5 for the narrative_media family; the
    # 80-150 expansion is still a separate, later content task.
    assert 32 <= len(WINNING_AD_STRUCTURES) <= 48
    per_format = Counter(f for s in WINNING_AD_STRUCTURES for f in s["formatBias"])
    assert set(per_format) == FORMATS
    assert all(4 <= count for count in per_format.values())


def test_structures_are_schema_compatible_and_uniquely_identified():
    hook_strategies = set(CreativePlan.model_fields["hookStrategy"].annotation.__args__)
    ids = [s["id"] for s in WINNING_AD_STRUCTURES]
    assert len(set(ids)) == len(ids)
    for structure in WINNING_AD_STRUCTURES:
        assert re.fullmatch(MECHANISM_PATTERN, structure["mechanism"]), structure["id"]
        assert structure["hookType"] in hook_strategies, structure["id"]
        assert set(structure["niche"]) <= set(NICHE_KEYWORDS), structure["id"]
        assert set(structure["formatBias"]) <= FORMATS, structure["id"]
        assert set(structure["assetRequirements"]) <= {"product_image", "person_image", "source_fact"}
        assert structure["forbidden"], structure["id"]


def test_silent_hooks_only_where_the_opening_is_visual():
    for structure in WINNING_AD_STRUCTURES:
        if not structure["hook"]:
            assert structure["hookType"] in {"visual", "pattern_interrupt"}, structure["id"]


def test_cta_style_states_outcome_not_a_pointer_to_specs():
    # Regression: 2026-09-12 live eval found half of ctaStyle fields matched the
    # "weak CTA" pattern our own approved hook-method.md explicitly names ("Learn more"
    # class) — pointing at a page/description/photo instead of stating the felt result.
    weak_markers = (
        "invite a look",
        "check the",
        "point to",
        "send them to",
        "suggest checking",
        "suggest looking",
        "tell them where",
        "check it themselves",
        "look at the detail on the page",
        "look at the product page",
    )
    offenders = [
        s["id"]
        for s in WINNING_AD_STRUCTURES
        if any(marker in s["ctaStyle"].lower() for marker in weak_markers)
    ]
    assert offenders == []


def test_hooks_avoid_the_slogan_registers_the_prompt_forbids():
    for structure in WINNING_AD_STRUCTURES:
        hook = structure["hook"].lower()
        assert "it is not about" not in hook and "it's not about" not in hook, structure["id"]
        assert len(structure["hook"]) <= 90, structure["id"]


def test_reference_rendering_hides_slugs_without_mutating_the_seed():
    # Regression: raw slugs like "no_invented_specs" were copied into plan negativeRules.
    structure = next(s for s in WINNING_AD_STRUCTURES if "_" in s["forbidden"][0])
    rendered = as_reference(structure)
    assert all("_" not in rule for rule in rendered["forbidden"])
    assert rendered["forbidden"] != structure["forbidden"]
    assert "_" in structure["forbidden"][0], "source seed must stay machine-readable"
    assert {k: v for k, v in rendered.items() if k != "forbidden"} == {
        k: v for k, v in structure.items() if k != "forbidden"
    }


def test_format_index_stays_compact_and_omits_full_playbooks():
    index = format_index()
    assert [entry["formatId"] for entry in index] == list(FORMAT_PLAYBOOKS)
    assert all(set(entry) == {"formatId", "label", "userIntent", "bestFor"} for entry in index)


def test_selection_restricted_to_the_chosen_format():
    selected = select_structures(bundle(), "product_demo")
    assert selected
    assert all("product_demo" in s["formatBias"] for s in selected)


def test_auto_selection_spans_formats():
    selected = select_structures(bundle(), None, limit=10)
    assert len({f for s in selected for f in s["formatBias"]}) > 1


def test_excluded_mechanisms_are_never_offered_again():
    first = select_structures(bundle(), "ugc_review")
    excluded = [first[0]["mechanism"]]
    again = select_structures(bundle(), "ugc_review", excluded)
    assert all(s["mechanism"] not in excluded for s in again)


def test_niche_keywords_rank_matching_structures_first():
    professional = select_structures(
        bundle(service="Gabinet kosmetyczny, sprzęt dla firmy", userText="business equipment"),
        "problem_solution",
        limit=2,
    )
    assert any("b2b_professional" in s["niche"] for s in professional)


@pytest.mark.parametrize("format_id", sorted(FORMATS))
def test_a_formats_own_structures_outrank_cross_listed_ones(format_id):
    # Regression: an asset-less brief used to crowd core structures out of the offered set.
    offered = select_structures(bundle(), format_id, limit=6)
    assert any(s["formatBias"][0] == format_id for s in offered), format_id
    assert offered[0]["formatBias"][0] == format_id, format_id


def test_page_imagery_counts_as_a_product_image():
    # Regression: URL-only briefs send a page photo that never becomes an owned asset,
    # so product-visual structures used to be penalised on the most common real flow.
    without = select_structures(bundle(userText="wypromuj ten produkt"), "ugc_review", limit=3)
    with_page_image = select_structures(
        bundle(userText="wypromuj ten produkt"),
        "ugc_review",
        limit=3,
        image_roles=["product page image"],
    )
    assert any("product_image" in s["assetRequirements"] for s in with_page_image)
    assert [s["id"] for s in with_page_image] != [s["id"] for s in without]


def test_uploaded_person_image_satisfies_person_requirements():
    offered = select_structures(
        bundle(availableAssets=[{"role": "person"}], sourceFacts=[{"source": "x", "text": "y"}]),
        "testimonial",
        limit=len(WINNING_AD_STRUCTURES),
    )
    professional = next(s for s in offered if "person_image" in s["assetRequirements"])
    assert offered.index(professional) < len(offered)


def test_unmet_asset_requirements_rank_lower_without_disappearing():
    ranked = select_structures(bundle(), "testimonial", limit=len(WINNING_AD_STRUCTURES))
    source_backed = next(s for s in ranked if "source_fact" in s["assetRequirements"])
    assert source_backed in ranked
    with_source = select_structures(
        bundle(sourceFacts=[{"source": "https://example.com", "text": "Question"}]),
        "testimonial",
        limit=len(WINNING_AD_STRUCTURES),
    )
    assert with_source.index(source_backed) <= ranked.index(source_backed)


def test_selection_is_deterministic_and_bounded():
    first = select_structures(bundle(userText="coffee"), None, limit=5)
    assert first == select_structures(bundle(userText="coffee"), None, limit=5)
    assert len(first) == 5


@pytest.mark.parametrize("format_id", sorted(FORMATS))
def test_every_format_yields_candidates_for_an_empty_brief(format_id):
    assert select_structures(bundle(), format_id)


# --- Phase 1.5: offer understanding before mechanism selection ---


def test_alice_case_resolves_to_narrative_media_with_its_own_overlay():
    alice = bundle(userText="wypromuj ksiazke w nowej niezwyklej kolorowej edycji alicja")
    assert matched_niches(alice) == ["narrative_media"]
    overlay = category_overlay(alice)
    assert overlay["niche"] == "narrative_media"
    assert "story" in overlay["requiredPayoff"].lower()
    assert any("illustrat" in rule.lower() for rule in overlay["forbiddenReductions"])


def test_narrative_structures_are_retrievable_and_reject_visual_only_payoff():
    offered = select_structures(
        bundle(userText="reklama nowego wydania powieści"), None, (), limit=10
    )
    narrative = [s for s in offered if "narrative_media" in s["niche"]]
    assert narrative, "narrative briefs must surface narrative structures"
    assert all("story" in s["id"] or "page" in s["id"] for s in narrative)


@pytest.mark.parametrize(
    "text,should_match",
    [
        ("program lojalnościowy dla klientów", False),
        ("fotografia produktu w studio", False),
        ("integracja z systemem GUS", False),
        ("nowa gra planszowa dla rodziny", True),
        ("audiobook z nowym lektorem", True),
        ("komiks w twardej oprawie", True),
    ],
)
def test_short_narrative_keywords_do_not_match_inside_other_words(text, should_match):
    # "gra" must not fire inside "program"/"fotografia"/"integracja".
    assert ("narrative_media" in matched_niches(bundle(userText=text))) is should_match


def test_only_one_category_overlay_is_ever_returned():
    # Instruction load must stay flat no matter how many categories exist.
    for text in ("książka o gotowaniu", "krem do skóry", "aparat USG do gabinetu"):
        overlay = category_overlay(bundle(userText=text))
        if overlay:
            assert set(overlay) == {"niche", "requiredPayoff", "forbiddenReductions"}
            assert 2 <= len(overlay["forbiddenReductions"]) <= 4


def test_every_overlay_stays_within_the_declared_rule_budget():
    for niche, overlay in CATEGORY_OVERLAYS.items():
        assert niche in NICHE_KEYWORDS, niche
        assert overlay["requiredPayoff"]
        assert 2 <= len(overlay["forbiddenReductions"]) <= 4, niche


def test_retrieval_widens_only_for_hybrid_or_ambiguous_offers():
    precise = bundle(userText="nowa powieść kryminalna")
    assert retrieval_limit(precise, ["narrative_immersion"]) == 6
    assert retrieval_limit(precise, ["narrative_immersion", "collectible_aesthetic"]) == 10
    ambiguous = bundle(userText="coś dla firmy i do domu, sklep i usługa")
    assert retrieval_limit(ambiguous, ["physical_use"]) == 10


def test_evidence_inventory_is_computed_from_real_material_only():
    assert evidence_available(bundle()) == []
    full = evidence_available(
        bundle(
            brief="Sprzedaję książkę",
            availableAssets=[{"role": "person"}],
            sourceFacts=[{"source": "https://x", "text": "y"}],
        ),
        image_roles=["product page image"],
        page_status="resolved",
    )
    assert set(full) == {"product_image", "person_image", "source_facts", "offer_page", "written_brief"}


# --- Retrieval quality: ties must not be decided by authoring order ---


def test_common_tag_briefs_no_longer_collapse_into_one_big_tie():
    # Measured 2026-09-12: "produkt" matched ecommerce_physical on 22 of 45 cards, all
    # scoring identically, so the offered set was decided by position in the list.
    text = "wypromuj ten produkt po polsku, szukam nowych klientow"
    scores = [_fit_score(s, text) for s in WINNING_AD_STRUCTURES]
    top = max(scores)
    assert top > 0
    assert sum(1 for s in scores if s == top) <= 3, "a common tag must not tie half the library"


def test_rare_tags_outscore_ubiquitous_ones():
    # narrative_media sits on 5 cards, ecommerce_physical on 22; a book brief must not
    # be answered primarily by generic ecommerce cards.
    book = _fit_score(
        next(s for s in WINNING_AD_STRUCTURES if s["niche"] == ["narrative_media"]),
        "nowa kolorowa edycja ksiazki",
    )
    generic = max(
        _fit_score(s, "nowa kolorowa edycja ksiazki")
        for s in WINNING_AD_STRUCTURES
        if "narrative_media" not in s["niche"]
    )
    assert book > generic


def test_specialist_cards_outrank_generalists_on_the_same_hit():
    text = "ksiazka"
    specialist = next(s for s in WINNING_AD_STRUCTURES if s["niche"] == ["narrative_media"])
    generalist = next(
        s for s in WINNING_AD_STRUCTURES if "narrative_media" in s["niche"] and len(s["niche"]) > 1
    )
    assert _fit_score(specialist, text) > _fit_score(generalist, text)


def test_zero_signal_briefs_still_reach_different_cards_but_stay_deterministic():
    first = [s["id"] for s in select_structures(bundle(userText="zrob reklame"), None, (), limit=6)]
    other = [s["id"] for s in select_structures(bundle(userText="potrzebuje spot"), None, (), limit=6)]
    repeat = [s["id"] for s in select_structures(bundle(userText="zrob reklame"), None, (), limit=6)]
    assert first == repeat, "same brief must be reproducible"
    assert set(first) != set(other), "authoring order must not decide every no-signal brief"


def test_auto_offered_set_spans_several_format_families():
    # Regression: all four narrative cases picked hook_cta, and a no-signal brief used to
    # return whatever sat earliest in the list.
    for text in ("zrob reklame", "nowa kolorowa edycja ksiazki", "wypromuj ten produkt"):
        offered = select_structures(bundle(userText=text), None, (), limit=10)
        assert len({s["formatBias"][0] for s in offered}) >= 4, text


def test_explicit_format_still_leads_with_its_own_family():
    # The format bonus must stay decisive over any fit score.
    for format_id in sorted(FORMATS):
        offered = select_structures(
            bundle(userText="produkt sklep dostawa gadzet kuchnia"), format_id, (), limit=6
        )
        assert offered[0]["formatBias"][0] == format_id, format_id


def test_uploaded_video_counts_as_evidence():
    # source_video matched neither the "product" nor "person" substring check, so a video
    # the director now actually sees in frames was invisible to its evidence inventory.
    assert "source_video" in evidence_available(
        bundle(availableAssets=[{"role": "source_video"}])
    )
    assert "source_video" in evidence_available(bundle(), image_roles=["source video frame"])
    assert "source_video" not in evidence_available(bundle(availableAssets=[{"role": "product"}]))


def test_consumption_models_are_a_closed_vocabulary():
    assert "narrative_immersion" in CONSUMPTION_MODELS
    assert "collectible_aesthetic" in CONSUMPTION_MODELS
    assert len(set(CONSUMPTION_MODELS)) == len(CONSUMPTION_MODELS)
