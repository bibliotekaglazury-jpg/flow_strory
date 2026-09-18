"""Technical native-video gate; never synthesizes or adds audio."""

import json
import re
import subprocess
import tempfile
from app.config import settings


def validate_native_video(data, duration=15):
    with tempfile.NamedTemporaryFile(suffix=".mp4") as file:
        file.write(data)
        file.flush()
        try:
            probe = subprocess.run(
                [
                    settings().ffprobe_path,
                    "-protocol_whitelist",
                    "file,pipe",
                    "-v",
                    "error",
                    "-show_streams",
                    "-show_format",
                    "-of",
                    "json",
                    file.name,
                ],
                capture_output=True,
                check=True,
                timeout=60,
            )
            info = json.loads(probe.stdout)
            types = {s["codec_type"] for s in info["streams"]}
            return (
                {"video", "audio"} <= types
                and "mp4" in info["format"]["format_name"]
                and abs(float(info["format"]["duration"]) - duration) <= 0.75
            )
        except FileNotFoundError:
            result = subprocess.run(
                [
                    settings().ffmpeg_path,
                    "-nostdin",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-i",
                    file.name,
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a:0",
                    "-t",
                    "1",
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
            seconds = int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3]) if match else 0
            return (
                result.returncode == 0
                and abs(seconds - duration) <= 0.75
                and "mp4" in result.stderr
                and "Audio:" in result.stderr
            )
        except (subprocess.SubprocessError, ValueError, KeyError):
            return False
