"""
Podcast script writer — turns articles + research into a two-host conversational script.
"""

import json

from podcastbot.config import PODCAST_NAME, llm_chat
from podcastbot.matrix import log


def write_script(articles: list[dict]) -> list[dict]:
    """
    Generate a podcast script from researched articles.
    Returns: [{"speaker": "HOST1"|"HOST2", "text": "..."}]
    """
    article_blocks = []
    for i, a in enumerate(articles, 1):
        block = (
            f"ARTICLE {i}:\n"
            f"Title: {a.get('title', 'Untitled')}\n"
            f"Source: {a.get('source_domain', 'unknown')}\n"
            f"Summary: {a.get('summary', '')}\n"
            f"Research & Context: {a.get('research', '')}\n"
        )
        article_blocks.append(block)

    articles_text = "\n---\n".join(article_blocks)

    prompt = f"""You are writing a script for a daily tech podcast called "{PODCAST_NAME}".

The podcast has two hosts:
- HOST1: The main host. Knowledgeable, direct, occasionally witty.
- HOST2: The co-host. Asks good questions, provides counterpoints, brings energy.

Write a natural, conversational podcast script covering these articles. Guidelines:
- Start with a brief, energetic intro after the music (HOST1 welcomes listeners)
- Cover each article with genuine discussion, not just reading summaries
- Include the deeper implications and context from the research
- Make it sound like two people actually talking — interruptions, reactions, "oh that's interesting", building on each other's points
- Connect articles to each other when relevant
- End with a quick wrap-up and sign-off
- Aim for about {len(articles) * 3 + 2} minutes of content (roughly {len(articles) * 400 + 200} words)
- Do NOT include stage directions, only dialogue

Output format: Return ONLY a JSON array of objects, each with "speaker" (either "HOST1" or "HOST2") and "text" (their dialogue). Example:
[{{"speaker": "HOST1", "text": "Good morning everyone..."}}, {{"speaker": "HOST2", "text": "Hey, we've got some great stuff today..."}}]

Articles to cover:

{articles_text}"""

    try:
        content = llm_chat(prompt, max_tokens=4000, temperature=0.7)

        # Parse JSON from response (handle markdown code blocks)
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        segments = json.loads(content)

        valid = []
        for seg in segments:
            if isinstance(seg, dict) and "speaker" in seg and "text" in seg:
                valid.append({
                    "speaker": seg["speaker"].upper(),
                    "text": seg["text"].strip(),
                })

        log(f"Script generated: {len(valid)} segments")
        return valid

    except Exception as e:
        log(f"Script generation failed: {e}")
        return []
