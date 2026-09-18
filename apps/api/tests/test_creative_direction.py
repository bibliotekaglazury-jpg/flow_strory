import copy
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.creative_direction import ContextBundle, DirectorAnswer, compile_plan, normalize_answer
from app.providers.chat import MockChatProvider, mock_director
from app.services.chat_context import bundle
from app.video_recipe import compile_recipe
from test_chat import store, message  # noqa: F401


@pytest.fixture
async def planned():
    _, answer = await MockChatProvider().send_message(
        "s", None, [{"text": "Zrób reklamę kremu po polsku"}], {"duration": 15}
    )
    return mock_director(answer.recipe)


def context(**changes):
    return ContextBundle(
        userText="Kurs angielskiego dla dorosłych",
        brief="",
        productUrl=None,
        selectedFormat="auto",
        aspectRatio="9:16",
        availableAssets=[],
        sourceFacts=[],
        conversation=[],
        **changes,
    )


def test_context_without_url_or_industry_form():
    value = bundle(
        {"templateId": "auto", "aspectRatio": "1:1"},
        [{"role": "user", "text": "Kurs angielskiego dla dorosłych"}],
        [],
    )
    assert value.product is None and value.service is None
    assert value.userText.startswith("Kurs") and value.aspectRatio == "1:1"
    assert value.sourceFacts == []


def test_context_reuses_page_evidence_and_asset_metadata():
    value = bundle(
        {
            "templateId": "ugc_review",
            "aspectRatio": "9:16",
            "productUrl": "https://example.com",
            "page": {"url": "https://example.com", "text": "Offer details"},
        },
        [{"role": "user", "text": "Promote this offer"}],
        [
            {
                "id": "owned-id",
                "role": "person",
                "mimeType": "image/png",
                "width": 100,
                "height": 100,
                "durationSeconds": None,
            }
        ],
    )
    assert value.sourceFacts[0].text == "Offer details"
    assert value.availableAssets[0].role == "person"
    assert "storage_key" not in value.model_dump_json()


async def test_auto_compile_language_script_separation_native_audio(planned):
    recipe = compile_plan(context(), planned.creativePlan, planned.videoPlan)
    assert recipe.duration == 15 and recipe.language == "pl"
    assert recipe.spokenContent.dialogue == planned.videoPlan.clips[0].spokenScript
    assert recipe.scenes[0].description == planned.videoPlan.clips[0].visualDirection
    text = compile_recipe(recipe)
    assert "Native audio" in text and "Spójrz" in text
    assert "openrouter" not in text.lower()
    assert normalize_answer(planned, context()).creativePlan.selectedFormat == "ugc_review"


async def test_music_carries_its_level_or_is_refused_outright(planned):
    # Of four live videos only one had music and it was barely audible: the generator
    # mixes everything in one pass, so the level has to be words in the prompt.
    scored = planned.model_copy(deep=True)
    scored.videoPlan.clips[0].audio.music = "quiet warm synth pad"
    text = compile_recipe(compile_plan(context(), scored.creativePlan, scored.videoPlan))
    assert "quiet warm synth pad" in text
    assert "clearly quieter than the dialogue" in text and "never masking a word" in text

    silent = planned.model_copy(deep=True)
    silent.videoPlan.clips[0].audio.music = None
    quiet = compile_recipe(compile_plan(context(), silent.creativePlan, silent.videoPlan))
    assert "Music: none. Do not add any music track." in quiet
    assert "quieter than the dialogue" not in quiet


async def test_music_leads_the_mix_when_the_concept_has_no_dialogue(planned):
    # A silent fashion lookbook asked for music and came back with footsteps only: the
    # mix line still told the generator to keep the track under a voice that never spoke.
    scored = planned.model_copy(deep=True)
    clip = scored.videoPlan.clips[0]
    clip.audio.music = "quiet modern fashion beat"
    clip.audio.speechRequired = False
    clip.spokenScript = ""
    text = compile_recipe(compile_plan(context(), scored.creativePlan, scored.videoPlan))
    assert "quiet modern fashion beat" in text
    assert "the music is the main audio layer" in text
    assert "quieter than the dialogue" not in text


async def test_product_fidelity_is_stated_only_when_a_product_image_exists(planned):
    # Live case: the generator enlarged "DOLCE&GABBANA" onto glasses whose real branding
    # is a small marking, so the product no longer matched the reference photo.
    recipe = compile_plan(context(), planned.creativePlan, planned.videoPlan)
    with_product = compile_recipe(recipe, {"references": ["productImageId", "personImageId"]})
    assert "must match the supplied product image exactly" in with_product
    assert "add, enlarge, restyle" in with_product
    without_product = compile_recipe(recipe, {"references": ["personImageId"]})
    assert "must match the supplied product image exactly" not in without_product
    assert "must match the supplied product image exactly" not in compile_recipe(recipe)


async def test_manual_format_must_be_preserved(planned):
    ctx = context().model_copy(update={"selectedFormat": "product_demo"})
    with pytest.raises(ValueError, match="selected format"):
        compile_plan(ctx, planned.creativePlan, planned.videoPlan)
    planned.creativePlan.selectedFormat = "product_demo"
    assert compile_plan(ctx, planned.creativePlan, planned.videoPlan).duration == 15


@pytest.mark.parametrize(
    "mutation", ["duration", "clips", "beats", "language", "native", "hook", "reasoning"]
)
async def test_invalid_plans_are_rejected(planned, mutation):
    data = copy.deepcopy(planned.model_dump())
    if mutation == "duration":
        data["videoPlan"]["duration"] = 30
    if mutation == "clips":
        data["videoPlan"]["clips"] *= 2
    if mutation == "beats":
        data["videoPlan"]["clips"][0]["beats"] = [
            {"start": 4.0, "end": 2.0, "purpose": "hook", "action": "reveal"}
        ]
    if mutation == "language":
        data["videoPlan"]["spokenLanguage"] = "de"
    if mutation == "native":
        data["videoPlan"]["clips"][0]["audio"]["native"] = False
    if mutation == "hook":
        data["creativePlan"]["hookStrategy"] = "random"
    if mutation == "reasoning":
        data["reasoning"] = "private"
    with pytest.raises(ValidationError):
        DirectorAnswer.model_validate(data)


async def test_beats_survive_compilation_without_fixed_timings(planned):
    data = planned.model_dump()
    data["videoPlan"]["clips"][0]["beats"] = [
        {"start": 0.0, "end": 6.0, "purpose": "hook", "action": "Show the bottle"},
        {"start": 9.0, "end": 15.0, "purpose": "CTA", "action": "Look at the camera"},
    ]
    answer = DirectorAnswer.model_validate(data)
    recipe = compile_plan(context(), answer.creativePlan, answer.videoPlan)
    assert "9–15s: Look at the camera" in recipe.scenes[0].description


async def test_clarification_and_saved_plan_apply_without_assets(store):  # noqa: F811
    from app.services import chat
    from app.chat_api import ApplyRecipe
    from app.schemas import Creative
    from app.db import ChatRecipeVersion, Prompt

    session = await chat.create("alice")
    unclear = await chat.send("alice", session["id"], message("?"))
    assert unclear["answer"]["needsMoreInformation"] and unclear["answer"]["recipe"] is None
    body = message("Zrób reklamę kursu po polsku")
    body.context.templateId = "auto"
    ready = await chat.send("alice", session["id"], body)
    applied = chat.apply(
        "alice",
        session["id"],
        ApplyRecipe(
            revision=ready["revision"],
            creative=Creative(
                templateId="auto", inputAssets={}, brief="Kurs", duration=15, aspectRatio="9:16"
            ),
        ),
    )
    assert applied["creative"]["templateId"] == "ugc_review"
    with store() as db:
        version = db.scalar(select(ChatRecipeVersion))
        saved = db.get(Prompt, applied["prompt"]["promptId"])
        assert version.recipe["planning"]["contextBundle"]["userText"] == body.text
        assert saved.snapshot["creativePlanning"]["videoPlan"]["duration"] == 15
        assert "reasoning" not in json.dumps(saved.snapshot)
