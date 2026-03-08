#!/usr/bin/env python3
"""
Main service — watches a Matrix room for article links and commands.
Generates podcasts on demand and weekly digests automatically.
"""

import re
import time
from datetime import datetime
from pathlib import Path

from podcastbot.config import MATRIX_HOMESERVER, MATRIX_ACCESS_TOKEN, MATRIX_USER_ID, MATRIX_ROOM_ID, PODCAST_BASE_URL, PODCAST_DIR
from podcastbot.matrix import MatrixClient, log
from podcastbot import db
from podcastbot.fetcher import fetch_article, summarize_article
from podcastbot.digest import generate_digest

URL_PATTERN = re.compile(r'https?://[^\s<>"\')\]]+')
DIGEST_HOUR = 18  # 6 PM Sunday


class PodcastBotService:
    def __init__(self):
        self.matrix = MatrixClient(MATRIX_HOMESERVER, MATRIX_ACCESS_TOKEN, MATRIX_USER_ID)
        self.room_id = MATRIX_ROOM_ID
        self._last_digest_week = None
        self._sync_token = ""

    def setup(self):
        db.init_db()
        self.matrix.drain_old_messages()
        self._sync_token = self.matrix.get_sync_token()
        self.matrix.send_message(self.room_id,
            "PodcastBot ready. Drop article links and say 'podcast' when ready.\n\n"
            "Commands: podcast, status, list, digest now")
        log("PodcastBot service initialized")

    def run(self):
        while True:
            self._poll_messages()
            self._check_digest_time()
            self._cleanup_old_episodes()
            time.sleep(3)

    def _poll_messages(self):
        messages, self._sync_token = self.matrix.poll_messages(
            self.room_id, self._sync_token, poll_interval=3)
        self.matrix.save_sync_token(self._sync_token)

        for msg in messages:
            body = msg["body"].strip()
            self._handle_message(body)

    def _handle_message(self, text: str):
        lower = text.lower().strip()

        if lower == "status":
            count = db.get_article_count()
            week = db.current_week_id()
            from podcastbot.podcast import get_episode_count
            eps = get_episode_count()
            self.matrix.send_message(self.room_id,
                f"Week {week}: {count} article(s) queued | {eps} episode(s) total")
            return

        if lower == "podcast":
            self._generate_podcast()
            return

        if lower == "digest now":
            self.matrix.send_message(self.room_id, "Generating digest...")
            digest = generate_digest()
            if digest:
                self.matrix.send_message(self.room_id, digest)
            else:
                self.matrix.send_message(self.room_id, "No articles to digest this week.")
            self._last_digest_week = db.current_week_id()
            return

        if lower == "list":
            articles = db.get_week_articles()
            if not articles:
                self.matrix.send_message(self.room_id, "No articles this week yet.")
                return
            lines = []
            for i, a in enumerate(articles, 1):
                title = a["title"] or a["url"]
                lines.append(f"{i}. {title}")
            self.matrix.send_message(self.room_id, "\n".join(lines))
            return

        urls = URL_PATTERN.findall(text)
        if urls:
            for url in urls:
                self._process_url(url)

    def _process_url(self, url: str):
        added = db.add_article(url)
        if not added:
            self.matrix.send_message(self.room_id, "Already have that one.")
            return

        log(f"Fetching article: {url}")
        article = fetch_article(url)
        title = article["title"] or "Untitled"
        domain = article["domain"]

        summary = ""
        if article["body"]:
            summary = summarize_article(title, article["body"])
        if not summary:
            summary = article["description"]

        db.update_article(url, title, summary, domain)

        count = db.get_article_count()
        response = f"Saved: {title} ({domain})\n"
        if summary:
            response += f"{summary}\n"
        response += f"\n{count} article(s) queued for podcast."
        self.matrix.send_message(self.room_id, response)

    def _generate_podcast(self):
        articles = db.get_week_articles()
        articles = [a for a in articles if not a.get("digest_included")]

        if not articles:
            self.matrix.send_message(self.room_id, "No new articles to podcast.")
            return

        count = len(articles)
        self.matrix.send_message(self.room_id,
            f"Generating podcast from {count} article(s)...\n"
            "1/4 Researching articles...")

        from podcastbot.researcher import research_all
        for a in articles:
            if not a.get("body"):
                fetched = fetch_article(a["url"])
                a["body"] = fetched.get("body", "")

        articles = research_all(articles)
        self.matrix.send_message(self.room_id, "2/4 Writing script...")

        from podcastbot.scriptwriter import write_script
        segments = write_script(articles)
        if not segments:
            self.matrix.send_message(self.room_id, "Script generation failed.")
            return

        self.matrix.send_message(self.room_id,
            f"3/4 Generating audio ({len(segments)} segments)...")

        from podcastbot.tts import synthesize_script
        today = datetime.now().strftime("%Y-%m-%d")
        seg_dir = PODCAST_DIR / "segments" / today
        seg_dir.mkdir(parents=True, exist_ok=True)

        audio_files = synthesize_script(segments, seg_dir)
        if not audio_files:
            self.matrix.send_message(self.room_id, "Audio generation failed.")
            return

        self.matrix.send_message(self.room_id, "4/4 Assembling episode...")

        from podcastbot.podcast import assemble_episode, update_rss
        episode_path = assemble_episode(audio_files, today)
        if not episode_path:
            self.matrix.send_message(self.room_id, "Episode assembly failed.")
            return

        titles = [a.get("title", "Untitled") for a in articles]
        ep_title = f"Morning Brief — {datetime.now().strftime('%B %d, %Y')}"
        ep_desc = "Today's articles: " + ", ".join(titles)

        if PODCAST_BASE_URL:
            update_rss(episode_path, ep_title, ep_desc, PODCAST_BASE_URL)

        week_id = db.current_week_id()
        db.mark_digested(week_id, ep_title, count)

        size_mb = episode_path.stat().st_size / (1024 * 1024)
        duration_secs = int(episode_path.stat().st_size / 16000)
        mins, secs = divmod(duration_secs, 60)

        msg = f"Podcast ready! {ep_title}\n{count} articles | ~{mins}:{secs:02d} | {size_mb:.1f} MB"
        if PODCAST_BASE_URL:
            msg += f"\nEpisodes: {PODCAST_BASE_URL}/episodes/"
        self.matrix.send_message(self.room_id, msg)

    def _cleanup_old_episodes(self):
        now = datetime.now()
        if now.hour == 3 and now.minute == 0:
            from podcastbot.podcast import cleanup_old_episodes
            deleted = cleanup_old_episodes(max_age_days=30, max_episodes=20)
            if deleted:
                log(f"Cleaned up {deleted} old episode(s)")

    def _check_digest_time(self):
        now = datetime.now()
        current_week = db.current_week_id()

        if (now.weekday() == 6 and now.hour == DIGEST_HOUR
                and self._last_digest_week != current_week):
            count = db.get_article_count()
            if count > 0:
                log(f"Auto-generating weekly digest for {current_week}")
                self.matrix.send_message(self.room_id,
                    f"It's Sunday — generating your weekly digest ({count} articles)...")
                digest = generate_digest()
                if digest:
                    self.matrix.send_message(self.room_id, digest)
            self._last_digest_week = current_week
