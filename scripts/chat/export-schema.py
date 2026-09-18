"""Run with apps/api/.venv/bin/python scripts/chat/export-schema.py."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "apps/api"))
from app.video_recipe import RecipeAnswer  # noqa: E402

(root / "packages/contracts/video-recipe.schema.json").write_text(
    json.dumps(RecipeAnswer.model_json_schema(), indent=2) + "\n", encoding="utf-8"
)

from app.creative_direction import DirectorAnswer, ContextBundle, PlannedAnswer  # noqa: E402
for name, model in [("creative-director", DirectorAnswer), ("context-bundle", ContextBundle), ("chat-answer", PlannedAnswer)]:
    (root / f"packages/contracts/{name}.schema.json").write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
