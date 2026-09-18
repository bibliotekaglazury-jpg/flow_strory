"""Instructions for the still look preview. Reference data only; never user-supplied."""

VERSION = "tryon-v2"

# Canonical catalogue angles. Labels are ours, not free text from the request, so a
# follow-up shot can be asked for without letting a caller write the instruction.
ANGLES = {
    "front": "Shoot the look straight on, facing the camera, full length.",
    "three_quarter": "Turn the person about 45 degrees from the camera, full length.",
    "back": "Show the look from behind, full length, so the back of every piece reads.",
    "detail": "Move in close on the pieces themselves — fabric, fastenings and finish.",
}

# "One complete outfit" used to open this block: the model read it as licence to finish the
# outfit itself, turning a model's trousers into a dress and swapping her own bag.
INSTRUCTIONS = """Put the product photos that follow onto the person from the first photo, in a
single realistic full-length image. Change only what is supplied: keep every garment, shoe, bag
and accessory the person already wears exactly as in their photo, unless a supplied product is
the same kind of item, and then that one item alone is replaced by it. Anything without a
supplied counterpart stays untouched — never swap trousers for a dress, restyle or replace a bag,
or add a garment or accessory that was not supplied.

Each product must appear exactly as photographed: same shape, proportions, colour, material
and finish, with any logo, brand name or marking reproduced only at the size, position and
prominence it actually has in its own photo. Never add, enlarge, restyle, translate or invent
branding, text, hardware or decoration that is not visible in that photo.

Keep the person's face, hair, body proportions and skin tone exactly as in their photo. Do not
slim, retouch or age them, and do not substitute a different person.

Every supplied piece has to be visible and identifiable in the result. Where one garment layers
over another, wear the outer piece open, pushed aside or carried so the piece underneath still
reads. Do not silently drop a piece that is hard to place.

Use clean, even studio lighting on a plain uncluttered background suitable for an e-commerce
catalogue, unless the person's own photo already has such a background, in which case keep it.
Add no text, watermark, logo or graphic overlay of your own."""


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
