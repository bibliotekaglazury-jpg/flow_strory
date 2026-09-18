"""SubRip (.srt) formatting: pure text transform over an export's already-frozen cues.

No new state, no job, no worker: an export's cues never change once created (see
service.create_export), so this can run synchronously in the request that asks for it.
"""


def _timestamp(ms: int) -> str:
    ms = max(0, int(ms))
    hours, rest = divmod(ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def render_srt(cues: list[dict]) -> str:
    blocks = [
        f"{index}\n{_timestamp(cue['startMs'])} --> {_timestamp(cue['endMs'])}\n{cue['text']}\n"
        for index, cue in enumerate(cues, start=1)
    ]
    return "\n".join(blocks)
