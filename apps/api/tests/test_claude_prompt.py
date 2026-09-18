from app.prompts.video_chat.v3 import SYSTEM_PROMPT, VERSION
from app.creative_audit import MINIMUM_SCORES, MINIMUM_MEAN_SCORE


def test_versioned_prompt_matches_gate_and_separates_plans():
    assert VERSION == "creative-director-v3"
    assert set(MINIMUM_SCORES.values()) == {3}
    assert MINIMUM_MEAN_SCORE == 3.5
    for rule in (
        "three materially different",
        "average at least 3.5",
        "0–15",
        "spokenScript",
        "visualDirection",
        "camera",
        "performance",
        "audio",
        "BCP-47",
        "untrusted",
        "excluded mechanisms",
        "audience",
        "business objective",
        "creative biases",
        "single highest-value question",
    ):
        assert rule in SYSTEM_PROMPT
