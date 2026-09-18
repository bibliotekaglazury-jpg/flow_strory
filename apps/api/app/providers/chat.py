"""Local single-account conversation boundary. No video submission or billing."""

from typing import Protocol
from app.creative_audit import ChatProviderResult
from uuid import uuid4

from app.video_recipe import RecipeAnswer, VideoRecipe, RecipeScene, SpokenContent
from app.creative_direction import DirectorAnswer


class ChatProvider(Protocol):
    key: str

    async def create_thread(self) -> str | None: ...
    async def send_message(
        self, session_id: str, thread_id: str | None, messages: list[dict], context: dict
    ) -> ChatProviderResult: ...
    async def resume_thread(self, thread_id: str) -> str: ...
    async def cancel(self, session_id: str) -> None: ...
    async def health(self) -> bool: ...


class MockChatProvider:
    key = "mock"

    async def create_thread(self):
        return str(uuid4())

    async def resume_thread(self, thread_id):
        return thread_id

    async def cancel(self, session_id):
        return None

    async def health(self):
        return True

    async def send_message(self, session_id, thread_id, messages, context):
        text = messages[-1]["text"]
        duration = context.get("duration", 15)
        language = (
            "de"
            if any(v in text.lower() for v in ("niemieck", "german", "deutsch"))
            else "pl"
            if any(v in text.lower() for v in ("zrób", "polsk", "dziewczyna", "krem"))
            else "en"
        )
        dialogue = {
            "pl": "Spójrz na ten produkt. Zobacz, jak wygląda z bliska. Poznaj naszą kolekcję.",
            "de": "Schau dir dieses Produkt an. Entdecke unsere Kollektion.",
            "en": "Take a closer look at this product. Explore our collection.",
        }[language]
        recipe = VideoRecipe(
            language=language,
            spokenContent=SpokenContent(required=True, language=language, dialogue=dialogue),
            intent="Product showcase",
            concept=text[:1500],
            duration=duration,
            aspectRatio=context.get("aspectRatio", "9:16"),
            qualityTier="auto",
            subject="A scripted creator",
            product="The supplied product",
            visualStyle="Natural daylight",
            camera="Handheld medium shot with product close-up",
            performance="Conversational delivery",
            scenes=[RecipeScene(duration=duration, description=text[:1500])],
            audio="Natural voice, no background music",
            constraints=["Keep product identity faithful"],
            negativeRules=[],
        )
        answer = RecipeAnswer(
            assistantMessage="Demo recipe ready. Review it and apply it to your video brief.",
            needsMoreInformation=False,
            clarificationQuestion=None,
            recipe=recipe,
        )

        if "contextBundle" in context:
            from app.creative_direction import DirectorAnswer

            if text.strip() in {"?", "nbnb", "hello"}:
                return ChatProviderResult(
                    thread_id or str(uuid4()),
                    DirectorAnswer(
                        assistantMessage="What offer should this video promote?",
                        assessment="clarification_needed",
                        clarificationQuestion="What offer should this video promote?",
                        creativePlan=None,
                        videoPlan=None,
                    ),
                )
            return ChatProviderResult(thread_id or str(uuid4()), mock_director(recipe, context["templateId"]))
        return ChatProviderResult(thread_id or str(uuid4()), answer)


def mock_director(recipe, selected="auto"):
    """Explicit test fixture, never a production creative decision engine."""

    return DirectorAnswer.model_validate(
        {
            "assistantMessage": "Demo concept ready. Review it before generating.",
            "assessment": "enough_to_plan",
            "clarificationQuestion": None,
            "creativePlan": {
                "objective": recipe.intent,
                "audience": "Interested customers",
                "offer": recipe.product,
                "coreTension": "Seeing how the offer fits everyday life",
                "creativeAngle": recipe.concept,
                "selectedFormat": "ugc_review" if selected == "auto" else selected,
                "hookStrategy": "demonstration",
                "tone": "Conversational",
                "visualMode": recipe.visualStyle,
                "language": recipe.language,
                "spokenLanguage": recipe.language,
                "characterConcepts": [recipe.subject],
                "productPresentation": recipe.product,
                "audioDirection": recipe.audio,
                "confidence": 0.8,
            },
            "videoPlan": {
                "duration": 15,
                "aspectRatio": recipe.aspectRatio,
                "language": recipe.language,
                "spokenLanguage": recipe.language,
                "continuity": "One continuous shot",
                "characters": [recipe.subject],
                "productRules": recipe.constraints,
                "constraints": [],
                "negativeRules": [],
                "clips": [
                    {
                        "start": 0,
                        "end": 15,
                        "role": "main",
                        "narrativePurpose": recipe.intent,
                        "visualDirection": recipe.concept,
                        "spokenScript": recipe.spokenContent.dialogue,
                        "camera": recipe.camera,
                        "performance": recipe.performance,
                        "audio": {
                            "native": True,
                            "speechRequired": True,
                            "voiceTone": "Natural",
                            "ambience": "Quiet room",
                            "music": None,
                        },
                        "beats": [],
                    }
                ],
            },
        }
    )
