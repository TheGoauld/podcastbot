#!/usr/bin/env python3
"""Add an article URL to the queue (for use without Matrix)."""

import sys

from podcastbot import db
from podcastbot.fetcher import fetch_article, summarize_article

if len(sys.argv) < 2:
    print("Usage: python add_article.py <url> [url2] [url3] ...")
    sys.exit(1)

db.init_db()

for url in sys.argv[1:]:
    added = db.add_article(url)
    if not added:
        print(f"Already queued: {url}")
        continue

    print(f"Fetching: {url}")
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
    print(f"  Saved: {title} ({domain})")
    if summary:
        print(f"  {summary[:100]}...")
    print(f"  {count} article(s) queued total")
