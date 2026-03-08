"""
Generate weekly digest from collected articles.
"""

from podcastbot.config import llm_chat
from podcastbot.matrix import log
from podcastbot import db


def generate_digest(week_id: str | None = None) -> str | None:
    """Generate a weekly digest from all articles in the given week."""
    wid = week_id or db.current_week_id()
    articles = db.get_week_articles(wid)

    if not articles:
        return None

    article_lines = []
    for i, a in enumerate(articles, 1):
        title = a["title"] or "Untitled"
        summary = a["summary"] or a.get("description", "No summary")
        domain = a["source_domain"] or "unknown"
        url = a["url"]
        article_lines.append(
            f"{i}. [{title}]({url}) ({domain})\n   {summary}"
        )

    articles_text = "\n\n".join(article_lines)

    prompt = (
        "You are writing a weekly news digest for a tech professional. "
        "Given the articles below, write a concise weekly briefing.\n\n"
        "Format:\n"
        "- Start with a brief 1-2 sentence overview of the week's themes\n"
        "- Group related articles together under topic headers\n"
        "- For each article, include the title as a link, source, and a one-line takeaway\n"
        "- End with a 'Worth Watching' section for any developing stories\n"
        "- Use markdown formatting\n\n"
        f"Articles from {wid}:\n\n{articles_text}"
    )

    try:
        digest = llm_chat(prompt, max_tokens=1500, temperature=0.4)
        db.mark_digested(wid, digest, len(articles))
        return digest
    except Exception as e:
        log(f"Digest generation failed: {e}")
        return None
