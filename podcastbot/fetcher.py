"""
Fetch article content from URLs — extract title, text, and generate summary.
"""

import re
from urllib.parse import urlparse

import requests

from podcastbot.config import llm_chat
from podcastbot.matrix import log


def fetch_article(url: str) -> dict:
    """Fetch a URL and extract title + text content."""
    try:
        r = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; PodcastBot/1.0)"
        })
        r.raise_for_status()
        html = r.text

        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""
        title = title.replace("&amp;", "&").replace("&#x27;", "'").replace("&quot;", '"')
        title = re.sub(r'\s+', ' ', title).strip()

        og_match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]*)"', html, re.IGNORECASE)
        if og_match and len(og_match.group(1)) > len(title) // 2:
            title = og_match.group(1)

        desc_match = re.search(r'<meta[^>]+(?:property="og:description"|name="description")[^>]+content="([^"]*)"', html, re.IGNORECASE)
        description = desc_match.group(1) if desc_match else ""

        body = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL | re.IGNORECASE)
        body = re.sub(r'<[^>]+>', ' ', body)
        body = re.sub(r'\s+', ' ', body).strip()[:3000]

        domain = urlparse(url).netloc.replace("www.", "")

        return {
            "title": title[:300],
            "description": description[:500],
            "body": body,
            "domain": domain,
        }
    except Exception as e:
        log(f"Failed to fetch {url}: {e}")
        domain = urlparse(url).netloc.replace("www.", "")
        return {"title": "", "description": "", "body": "", "domain": domain}


def summarize_article(title: str, body: str) -> str:
    """Use LLM to generate a 2-3 sentence summary of an article."""
    prompt = (
        "Summarize this article in 2-3 concise sentences. Focus on the key facts and takeaways.\n\n"
        f"Title: {title}\n\n"
        f"Content: {body[:2000]}"
    )
    try:
        return llm_chat(prompt, max_tokens=200, temperature=0.3)
    except Exception as e:
        log(f"Summary failed: {e}")
        return ""
