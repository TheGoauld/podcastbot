"""
Text-to-speech — converts script segments to audio files using OpenAI TTS.
"""

from pathlib import Path

import requests

from podcastbot.config import OPENAI_API_KEY, PODCAST_DIR
from podcastbot.matrix import log

VOICES = {
    "HOST1": "onyx",    # deep, authoritative
    "HOST2": "nova",    # bright, energetic
}

SEGMENTS_DIR = PODCAST_DIR / "segments"


def synthesize_segment(text: str, speaker: str, index: int,
                       output_dir: Path | None = None) -> Path | None:
    """Convert a single text segment to an MP3 file."""
    out_dir = output_dir or SEGMENTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    voice = VOICES.get(speaker, "onyx")
    output_path = out_dir / f"segment_{index:03d}_{speaker.lower()}.mp3"

    if not OPENAI_API_KEY:
        log("OPENAI_API_KEY not set — cannot generate audio")
        return None

    try:
        r = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "tts-1-hd",
                "voice": voice,
                "input": text,
                "response_format": "mp3",
                "speed": 1.05,
            },
            timeout=120,
        )
        r.raise_for_status()

        output_path.write_bytes(r.content)
        log(f"TTS segment {index} ({speaker}): {len(r.content)} bytes")
        return output_path

    except Exception as e:
        log(f"TTS failed for segment {index}: {e}")
        return None


def synthesize_script(segments: list[dict], output_dir: Path | None = None) -> list[Path]:
    """Convert all script segments to audio files."""
    audio_files = []
    for i, seg in enumerate(segments):
        path = synthesize_segment(seg["text"], seg["speaker"], i, output_dir)
        if path:
            audio_files.append(path)
    return audio_files
