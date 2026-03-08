"""
Research agent — generates deeper context and analysis for each article.
"""

from podcastbot.config import llm_chat
from podcastbot.matrix import log


def research_article(title: str, summary: str, body: str, domain: str) -> str:
    """Generate deep analysis of an article for podcast preparation."""
    prompt = (
        "You are a research analyst preparing background material for a tech podcast.\n\n"
        "Given this article, provide:\n"
        "1. Key facts and claims from the article\n"
        "2. Broader context — what led to this, why it matters now\n"
        "3. Implications — what this means for the industry/world\n"
        "4. Connections — how this relates to other recent developments\n"
        "5. Counterpoints or alternative perspectives\n\n"
        "Be specific and factual. Include relevant technical details.\n\n"
        f"Source: {domain}\n"
        f"Title: {title}\n"
        f"Summary: {summary}\n\n"
        f"Article content:\n{body[:3000]}"
    )
    try:
        return llm_chat(prompt, max_tokens=800, temperature=0.4)
    except Exception as e:
        log(f"Research failed for '{title}': {e}")
        return ""


def research_all(articles: list[dict]) -> list[dict]:
    """Research all articles. Returns articles with 'research' field added."""
    for article in articles:
        research = research_article(
            article.get("title", ""),
            article.get("summary", ""),
            article.get("body", ""),
            article.get("source_domain", ""),
        )
        article["research"] = research
        log(f"Researched: {article.get('title', '')[:60]}")
    return articles
