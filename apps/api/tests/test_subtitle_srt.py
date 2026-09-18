"""SubRip (.srt) export: the "Video and SRT ready" promise on the entry screen needs a
real file behind it, not just the rendered MP4."""

from app.subtitles.srt import render_srt


def test_formats_a_standard_two_cue_transcript():
    cues = [
        {"startMs": 0, "endMs": 1500, "text": "Hello there."},
        {"startMs": 1600, "endMs": 4000, "text": "Welcome to the show."},
    ]
    assert render_srt(cues) == (
        "1\n00:00:00,000 --> 00:00:01,500\nHello there.\n"
        "\n"
        "2\n00:00:01,600 --> 00:00:04,000\nWelcome to the show.\n"
    )


def test_formats_timestamps_past_an_hour():
    cues = [{"startMs": 3_661_250, "endMs": 3_662_000, "text": "One hour in."}]
    assert render_srt(cues) == "1\n01:01:01,250 --> 01:01:02,000\nOne hour in.\n"


def test_an_empty_transcript_is_an_empty_file():
    assert render_srt([]) == ""
