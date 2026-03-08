"""
Podcast assembly — stitches TTS segments into episodes and manages RSS feed.
"""

import hashlib
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import indent

from podcastbot.config import (
    EPISODES_DIR, ASSETS_DIR, RSS_PATH,
    PODCAST_NAME, PODCAST_DESC, PODCAST_AUTHOR,
)
from podcastbot.matrix import log


def _ensure_dirs():
    EPISODES_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def _generate_intro_music():
    """Generate a simple intro jingle using ffmpeg if no intro.mp3 exists."""
    intro_path = ASSETS_DIR / "intro.mp3"
    if intro_path.exists():
        return intro_path

    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            "sine=frequency=440:duration=0.3,afade=t=out:st=0.2:d=0.1[a1];"
            "sine=frequency=554:duration=0.3,afade=t=out:st=0.2:d=0.1[a2];"
            "sine=frequency=659:duration=0.3,afade=t=out:st=0.2:d=0.1[a3];"
            "sine=frequency=880:duration=0.5,afade=t=out:st=0.3:d=0.2[a4];"
            "[a1][a2][a3][a4]concat=n=4:v=0:a=1,volume=0.3",
            "-t", "1.5", str(intro_path)
        ], capture_output=True, timeout=10)
        log("Generated placeholder intro jingle")
    except Exception as e:
        log(f"Intro generation failed: {e}")
        return None

    return intro_path if intro_path.exists() else None


def _generate_silence(duration: float, output: Path) -> Path | None:
    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            f"anullsrc=r=24000:cl=mono",
            "-t", str(duration), "-c:a", "libmp3lame", "-q:a", "5",
            str(output)
        ], capture_output=True, timeout=10)
        return output if output.exists() else None
    except Exception:
        return None


def assemble_episode(segment_files: list[Path], episode_date: str | None = None) -> Path | None:
    """Stitch intro + segments into a single MP3 episode."""
    _ensure_dirs()

    date_str = episode_date or datetime.now().strftime("%Y-%m-%d")
    episode_path = EPISODES_DIR / f"episode_{date_str}.mp3"

    if not segment_files:
        log("No segments to assemble")
        return None

    segments_dir = segment_files[0].parent
    pause_path = segments_dir / "pause.mp3"
    _generate_silence(0.4, pause_path)

    concat_list = segments_dir / "concat.txt"
    lines = []

    intro = _generate_intro_music()
    if intro:
        lines.append(f"file '{intro}'")
        if pause_path.exists():
            lines.append(f"file '{pause_path}'")

    prev_speaker = None
    for f in segment_files:
        speaker = f.stem.split("_")[-1]
        if prev_speaker and speaker != prev_speaker and pause_path.exists():
            lines.append(f"file '{pause_path}'")
        lines.append(f"file '{f}'")
        prev_speaker = speaker

    if pause_path.exists():
        lines.append(f"file '{pause_path}'")

    concat_list.write_text("\n".join(lines))

    try:
        result = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:a", "libmp3lame", "-b:a", "128k",
            "-ar", "24000", "-ac", "1",
            str(episode_path)
        ], capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            log(f"ffmpeg concat failed: {result.stderr[:500]}")
            return None

        size_mb = episode_path.stat().st_size / (1024 * 1024)
        log(f"Episode assembled: {episode_path.name} ({size_mb:.1f} MB)")
        return episode_path

    except Exception as e:
        log(f"Episode assembly failed: {e}")
        return None
    finally:
        for f in segment_files:
            f.unlink(missing_ok=True)
        pause_path.unlink(missing_ok=True)
        concat_list.unlink(missing_ok=True)


def _xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def update_rss(episode_path: Path, title: str, description: str, base_url: str):
    """Update the podcast RSS feed with a new episode."""
    _ensure_dirs()

    episode_url = f"{base_url.rstrip('/')}/episodes/{episode_path.name}"
    guid = hashlib.md5(episode_path.name.encode()).hexdigest()
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    size = episode_path.stat().st_size
    duration_secs = int(size / 16000)
    mins, secs = divmod(duration_secs, 60)

    new_item = (
        f"    <item>\n"
        f"      <title>{_xml_escape(title)}</title>\n"
        f"      <description>{_xml_escape(description)}</description>\n"
        f'      <enclosure url="{_xml_escape(episode_url)}" length="{size}" type="audio/mpeg" />\n'
        f'      <guid isPermaLink="false">{guid}</guid>\n'
        f"      <pubDate>{pub_date}</pubDate>\n"
        f"      <itunes:duration>{mins}:{secs:02d}</itunes:duration>\n"
        f"    </item>\n"
    )

    if RSS_PATH.exists():
        content = RSS_PATH.read_text()
        if "<item>" in content:
            content = content.replace("<item>", new_item + "    <item>", 1)
        else:
            content = content.replace("</channel>", new_item + "  </channel>")
    else:
        content = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">\n'
            "  <channel>\n"
            f"    <title>{PODCAST_NAME}</title>\n"
            f"    <description>{PODCAST_DESC}</description>\n"
            f"    <link>{base_url}</link>\n"
            "    <language>en-us</language>\n"
            f"    <itunes:author>{PODCAST_AUTHOR}</itunes:author>\n"
            '    <itunes:category text="Technology" />\n'
            "    <itunes:explicit>false</itunes:explicit>\n"
            + new_item +
            "  </channel>\n"
            "</rss>\n"
        )

    RSS_PATH.write_text(content)
    log(f"RSS feed updated with: {title}")


def get_episode_count() -> int:
    _ensure_dirs()
    return len(list(EPISODES_DIR.glob("episode_*.mp3")))


def cleanup_old_episodes(max_age_days: int = 30, max_episodes: int = 20):
    """Delete episodes older than max_age_days or beyond max_episodes count."""
    _ensure_dirs()
    episodes = sorted(EPISODES_DIR.glob("episode_*.mp3"), key=lambda f: f.stat().st_mtime)
    now = time.time()
    deleted = 0

    for ep in episodes:
        age_days = (now - ep.stat().st_mtime) / 86400
        remaining = len(episodes) - deleted
        if age_days > max_age_days or remaining > max_episodes:
            ep.unlink()
            deleted += 1
            log(f"Cleaned up old episode: {ep.name}")

    if deleted > 0 and RSS_PATH.exists():
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(RSS_PATH)
            channel = tree.getroot().find("channel")
            for item in channel.findall("item"):
                enclosure = item.find("enclosure")
                if enclosure is not None:
                    url = enclosure.get("url", "")
                    filename = url.rsplit("/", 1)[-1] if "/" in url else ""
                    if filename and not (EPISODES_DIR / filename).exists():
                        channel.remove(item)
            indent(tree.getroot(), space="  ")
            tree.write(str(RSS_PATH), encoding="unicode", xml_declaration=True)
        except Exception as e:
            log(f"RSS rebuild failed: {e}")

    return deleted
