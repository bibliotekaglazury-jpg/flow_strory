"""Instructions for the still look preview. Reference data only; never user-supplied."""

VERSION = "tryon-v3"

# Canonical catalogue angles. Labels are ours, not free text from the request, so a
# follow-up shot can be asked for without letting a caller write the instruction.
ANGLES = {
    "front": "Shoot the look straight on, facing the camera, full length.",
    "three_quarter": "Turn the person about 45 degrees from the camera, full length.",
    "back": "Show the look from behind, full length, so the back of every piece reads.",
    "detail": "Move in close on the pieces themselves — fabric, fastenings and finish.",
}

# tryon-v3 (Stan 2026-10-02): the short prompt that won the Meta Muse Image test — image 1 is the
# person, every further image is a product; one person, one full-body photo, exact product details.
INSTRUCTIONS = """Create ONE full-body photo of the person from image 1 (same face, hair and body; only this one person) wearing or carrying every product from the other images, on the same background as image 1.

Do not copy any other person from the product photos.

Keep every product detail exactly: shape, colour, texture, logos, prints, buttons, hardware and heels."""


def compose(angle: str | None = None, has_base: bool = False) -> str:
    """One instruction block; `has_base` re-shoots an existing preview from a new angle."""
    parts = [INSTRUCTIONS]
    if has_base:
        parts.append(
            "The first photo is an approved preview of this exact look. Keep the same person, "
            "the same garments and the same styling, and change only the camera position."
        )
    if angle in ANGLES:
        parts.append(ANGLES[angle])
    return "\n\n".join(parts)
