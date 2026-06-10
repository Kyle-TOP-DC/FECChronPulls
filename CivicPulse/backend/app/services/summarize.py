"""AI article summaries + message drafting.

Uses the Anthropic SDK when ANTHROPIC_API_KEY is configured; otherwise falls
back to plain templates so the app works without an API key.
"""
from __future__ import annotations

import logging

from ..config import ANTHROPIC_API_KEY
from ..models import Article, User
from ..schemas import Representative

log = logging.getLogger(__name__)

_MODEL = "claude-opus-4-8"


def _client():
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic

        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except Exception as exc:
        log.warning("Anthropic client unavailable: %s", exc)
        return None


def summarize_article(title: str, source: str | None, text: str) -> str | None:
    """Summarize raw article text into 3-4 sentences suitable for a
    constituent letter. Returns None when no API key is configured."""
    client = _client()
    if client is None:
        return None
    try:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=(
                "You summarize news articles for a civic-engagement app. "
                "Write a neutral, factual 3-4 sentence summary that a constituent "
                "could include in a letter to their member of Congress. No preamble."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Title: {title}\nSource: {source or 'unknown'}\n\n{text[:30000]}",
                }
            ],
        )
        return next((b.text for b in response.content if b.type == "text"), None)
    except Exception as exc:
        log.warning("Summarization failed: %s", exc)
        return None


def _salutation(rep: Representative) -> str:
    last_name = rep.name.split()[-1]
    return f"Dear {'Senator' if rep.role == 'senator' else 'Representative'} {last_name},"


def draft_message(
    user: User, article: Article, rep: Representative, thoughts: str
) -> tuple[str, str]:
    """Compose (subject, body): boilerplate intro + article summary, with the
    constituent's own thoughts front and center."""
    subject = f"A constituent's view on: {article.title}"[:300]

    summary = article.summary
    client = _client()
    if client is not None:
        try:
            response = client.messages.create(
                model=_MODEL,
                max_tokens=2048,
                system=(
                    "You help constituents write short, respectful messages to their "
                    "members of Congress about a news article. Keep the constituent's "
                    "own words and opinions intact and central — lightly structure them, "
                    "never replace them. Output only the letter body, no subject line."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Recipient: {_salutation(rep)}\n"
                            f"Constituent name: {user.name or 'A constituent'}\n"
                            f"Constituent zip: {user.zip_code}\n"
                            f"Article title: {article.title}\n"
                            f"Article source: {article.source or 'unknown'}\n"
                            f"Article URL: {article.url}\n"
                            f"Article summary: {summary or '(none available)'}\n\n"
                            f"The constituent's own thoughts (keep these central):\n{thoughts}"
                        ),
                    }
                ],
            )
            body = next((b.text for b in response.content if b.type == "text"), None)
            if body:
                return subject, body
        except Exception as exc:
            log.warning("AI drafting failed, using template: %s", exc)

    # Template fallback — boilerplate summary plus the user's thoughts verbatim.
    paragraphs = [
        _salutation(rep),
        (
            f"I am a constituent in zip code {user.zip_code}. I recently read "
            f"\"{article.title}\"{f' from {article.source}' if article.source else ''} "
            f"({article.url}) and wanted to share my perspective with your office."
        ),
    ]
    if summary:
        paragraphs.append(f"In brief, the article reports: {summary}")
    paragraphs.append("My own thoughts:\n" + thoughts.strip())
    paragraphs.append(
        "I would appreciate a response from your office on this issue.\n\n"
        f"Sincerely,\n{user.name or 'A constituent'}"
        + (f"\n{user.email}" if user.email else "")
    )
    return subject, "\n\n".join(paragraphs)
