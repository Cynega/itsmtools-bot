"""
generate.py
Fase 3 de la pipeline:
- Toma el contexto de research
- Llama a Claude API con el system prompt del proyecto
- Devuelve el artículo en HTML listo para WordPress
"""

import os
import re
import anthropic
from pathlib import Path


def log(msg: str) -> None:
    print(f"[generate] {msg}", flush=True)


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

TITLE_RE = re.compile(r"<!--\s*TITLE:\s*(.+?)\s*-->", re.IGNORECASE | re.DOTALL)
IMAGE_QUERY_RE = re.compile(r"<!--\s*IMAGE_QUERY:\s*(.+?)\s*-->", re.IGNORECASE | re.DOTALL)


def _extract_first(pattern: re.Pattern, text: str) -> tuple[str | None, str]:
    match = pattern.search(text)
    if not match:
        return None, text
    value = match.group(1).strip()
    cleaned = (text[: match.start()] + text[match.end() :])
    return value or None, cleaned


def extract_metadata(text: str) -> tuple[str | None, str | None, str]:
    """Saca <!-- TITLE: ... --> y <!-- IMAGE_QUERY: ... --> del HTML.

    Devuelve (title, image_query, html_limpio).
    """
    title, text = _extract_first(TITLE_RE, text)
    image_query, text = _extract_first(IMAGE_QUERY_RE, text)
    return title, image_query, text.lstrip()


def load_system_prompt() -> str:
    prompt_path = PROMPTS_DIR / "article.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"System prompt not found at {prompt_path}")


def build_user_message(research: dict) -> str:
    keyword = research["keyword"]
    kd = research["keyword_data"]
    related = research["related_keywords"][:15]
    competitors = research["competitors"]

    # Formatear competidores
    comp_summary = ""
    for i, c in enumerate(competitors, 1):
        if "error" in c:
            comp_summary += f"\n### Competitor {i}: {c['url']} (error al scrapear)\n"
            continue
        comp_summary += f"""
### Competitor {i} — Position {c.get('position')} — {c.get('url')}
- Title: {c.get('title')}
- H1: {c.get('h1')}
- Word count: ~{c.get('word_count')}
- Tools mentioned: {', '.join(c.get('tools_mentioned', []))}
- H2 structure:
{chr(10).join(f'  - {h}' for h in c.get('h2s', []))}
"""

    # Keywords secundarias
    secondary_kws = "\n".join(
        f"- {k['keyword']} (vol: {k['volume']}, diff: {k['difficulty']})"
        for k in related if k.get("keyword")
    )

    return f"""
## Target keyword
"{keyword}"

## Keyword data (USA)
- Monthly search volume: {kd.get('volume')}
- CPC: ${kd.get('cpc')}
- Competition: {kd.get('competition')}

## Secondary / related keywords to include naturally
{secondary_kws}

## Competitor analysis (top 5 Google USA)
{comp_summary}

---

Based on this research, write the full article. Follow all instructions in your system prompt exactly.
"""


def generate_article(research: dict) -> dict:
    """Llama a Claude API y devuelve {'title': str | None, 'html': str}."""
    log("FASE 3 — Generación con Claude")
    log(f"Generating article for: {research['keyword']}")

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    system_prompt = load_system_prompt()
    user_message = build_user_message(research)

    log("Calling Claude API...")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )

    raw = message.content[0].text
    title, image_query, article_html = extract_metadata(raw)
    word_count = len(article_html.split())
    log(
        f"Article generated: title={title!r} | image_query={image_query!r} | "
        f"~{word_count} words | {len(article_html)} chars"
    )

    return {"title": title, "image_query": image_query, "html": article_html}
