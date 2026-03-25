"""
generate.py
Fase 3 de la pipeline:
- Toma el contexto de research
- Llama a Claude API con el system prompt del proyecto
- Devuelve el artículo en HTML listo para WordPress
"""

import os
import json
import anthropic
from pathlib import Path
from rich.console import Console

console = Console()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


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


def generate_article(research: dict) -> str:
    """Llama a Claude API y devuelve el artículo en HTML."""
    console.rule("[bold blue]FASE 3 — Generación con Claude[/bold blue]")
    console.log(f"[cyan]Generating article for:[/cyan] {research['keyword']}")

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    system_prompt = load_system_prompt()
    user_message = build_user_message(research)

    console.log("[cyan]Calling Claude API...[/cyan]")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )

    article_html = message.content[0].text
    word_count = len(article_html.split())
    console.log(f"[green]Article generated:[/green] ~{word_count} words | {len(article_html)} chars")

    return article_html
