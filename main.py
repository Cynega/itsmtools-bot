"""
main.py — ITSM Content Bot
Entry point que orquesta la pipeline completa:
Research → Generate → Publish

Uso:
  python main.py --keyword "best ITSM tools" --publish draft
  python main.py --keyword "best ITSM tools" --publish publish
"""

import os
import json
import click
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv()

from pipeline.research import run_research
from pipeline.generate import generate_article
from pipeline.publish import publish_to_wordpress

console = Console()

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def check_env():
    required = ["DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD", "WP_URL", "WP_USER", "WP_APP_PASSWORD", "ANTHROPIC_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        console.print(f"[bold red]Missing env vars:[/bold red] {', '.join(missing)}")
        console.print("Copy .env.example to .env and fill in the values.")
        raise SystemExit(1)


def derive_title(keyword: str) -> str:
    """Genera un título SEO básico desde la keyword. Claude puede refinarlo después."""
    keyword_clean = keyword.strip().title()
    return f"{keyword_clean}: Top Picks for {2025}"


@click.command()
@click.option("--keyword", "-k", required=True, help="Target keyword (e.g. 'best ITSM tools')")
@click.option("--country", "-c", default="US", show_default=True, help="Country code for SERP")
@click.option("--publish", "-p", default="draft", type=click.Choice(["draft", "publish"]), show_default=True, help="WP post status")
@click.option("--skip-research", is_flag=True, help="Skip research phase and load from output/research.json")
@click.option("--skip-generate", is_flag=True, help="Skip generation phase and load from output/article.html")
def main(keyword: str, country: str, publish: str, skip_research: bool, skip_generate: bool):
    check_env()

    console.print(Panel.fit(
        f"[bold]ITSM Content Bot[/bold]\nKeyword: [cyan]{keyword}[/cyan] | Country: {country} | Status: [yellow]{publish}[/yellow]",
        border_style="blue"
    ))

    # FASE 1+2: Research
    research_file = OUTPUT_DIR / "research.json"
    if skip_research and research_file.exists():
        console.log("[yellow]Skipping research — loading from output/research.json[/yellow]")
        with open(research_file) as f:
            research = json.load(f)
    else:
        research = run_research(keyword, country)
        with open(research_file, "w") as f:
            json.dump(research, f, indent=2, ensure_ascii=False)
        console.log(f"[green]Research saved to[/green] {research_file}")

    # FASE 3: Generación
    article_file = OUTPUT_DIR / "article.html"
    if skip_generate and article_file.exists():
        console.log("[yellow]Skipping generation — loading from output/article.html[/yellow]")
        article_html = article_file.read_text(encoding="utf-8")
    else:
        article_html = generate_article(research)
        article_file.write_text(article_html, encoding="utf-8")
        console.log(f"[green]Article saved to[/green] {article_file}")

    # FASE 4: Publicación
    title = derive_title(keyword)
    result = publish_to_wordpress(
        title=title,
        content_html=article_html,
        keyword=keyword,
        status=publish,
    )

    # Resultado final
    if result.get("success"):
        console.print(Panel.fit(
            f"[bold green]Done![/bold green]\n"
            f"Post ID: {result['id']}\n"
            f"Status: {result['status']}\n"
            f"URL: {result['url']}",
            border_style="green"
        ))
    else:
        print(f"PUBLISH FAILED: {result.get('error', '')}")
        print(f"Article saved locally at: {article_file}")


if __name__ == "__main__":
    main()
