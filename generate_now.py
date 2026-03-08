#!/usr/bin/env python3
"""One-shot podcast generator — run directly to generate an episode without Matrix."""

import sys
from datetime import datetime
from pathlib import Path

from podcastbot.config import PODCAST_BASE_URL
from podcastbot.matrix import log
from podcastbot import db
from podcastbot.fetcher import fetch_article
from podcastbot.researcher import research_all
from podcastbot.scriptwriter import write_script
from podcastbot.tts import synthesize_script
from podcastbot.podcast import assemble_episode, update_rss
from podcastbot.config import PODCAST_DIR

db.init_db()
articles = db.get_week_articles()
articles = [a for a in articles if not a.get("digest_included")]
print(f"Articles to podcast: {len(articles)}")

if not articles:
    print("No articles — add some first with: python add_article.py <url>")
    sys.exit(0)

for a in articles:
    fetched = fetch_article(a["url"])
    a["body"] = fetched.get("body", "")
    print(f"  Fetched: {a.get('title', '')[:50]}")

print("Researching...")
articles = research_all(articles)

print("Writing script...")
segments = write_script(articles)
print(f"  {len(segments)} segments")
if not segments:
    print("Script failed")
    sys.exit(1)

print("Generating audio...")
today = datetime.now().strftime("%Y-%m-%d")
seg_dir = PODCAST_DIR / "segments" / today
seg_dir.mkdir(parents=True, exist_ok=True)
audio_files = synthesize_script(segments, seg_dir)
print(f"  {len(audio_files)} audio files")
if not audio_files:
    print("TTS failed")
    sys.exit(1)

print("Assembling episode...")
episode_path = assemble_episode(audio_files, today)
if not episode_path:
    print("Assembly failed")
    sys.exit(1)

titles = [a.get("title", "Untitled") for a in articles]
ep_title = "Morning Brief - " + datetime.now().strftime("%B %d, %Y")
ep_desc = "Today: " + ", ".join(titles)
if PODCAST_BASE_URL:
    update_rss(episode_path, ep_title, ep_desc, PODCAST_BASE_URL)

db.mark_digested(db.current_week_id(), ep_title, len(articles))

size_mb = episode_path.stat().st_size / (1024 * 1024)
dur_secs = int(episode_path.stat().st_size / 16000)
mins, secs = divmod(dur_secs, 60)
print(f"DONE! {episode_path.name} ({size_mb:.1f} MB, ~{mins}:{secs:02d})")
