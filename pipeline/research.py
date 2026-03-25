"""
research.py
Fase 1 y 2 de la pipeline:
- Keyword data via DataForSEO (volumen, dificultad, secundarias)
- SERP top 5 USA via DataForSEO
- Scraping de estructura de cada resultado
"""

import os
import base64
import httpx
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()


def get_auth_header() -> dict:
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def get_keyword_data(keyword: str, country: str = "US") -> dict:
    """Obtiene volumen, dificultad, CPC y keywords secundarias desde DataForSEO."""
    console.log(f"[cyan]Fetching keyword data for:[/cyan] {keyword}")

    # Keywords overview
    url = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"
    payload = [{"keywords": [keyword], "location_name": "United States", "language_name": "English"}]

    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json=payload, headers=get_auth_header())
        resp.raise_for_status()
        data = resp.json()

    result = {}
    try:
        item = data["tasks"][0]["result"][0]
        result["volume"] = item.get("search_volume", "N/A")
        result["cpc"] = item.get("cpc", "N/A")
        result["competition"] = item.get("competition", "N/A")
        result["monthly_searches"] = item.get("monthly_searches", [])
    except (KeyError, IndexError, TypeError):
        result = {"volume": "N/A", "cpc": "N/A", "competition": "N/A", "monthly_searches": []}

    console.log(f"[green]Volume:[/green] {result.get('volume')} | [green]CPC:[/green] {result.get('cpc')}")
    return result


def get_related_keywords(keyword: str) -> list:
    """Obtiene keywords relacionadas y preguntas desde DataForSEO."""
    console.log(f"[cyan]Fetching related keywords...[/cyan]")

    url = "https://api.dataforseo.com/v3/dataforseo_labs/google/related_keywords/live"
    payload = [{
        "keyword": keyword,
        "location_name": "United States",
        "language_name": "English",
        "limit": 20,
        "include_seed_keyword": False
    }]

    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json=payload, headers=get_auth_header())
        resp.raise_for_status()
        data = resp.json()

    keywords = []
    try:
        items = data["tasks"][0]["result"][0]["items"]
        for item in items:
            kw = item.get("keyword_data", {})
            keywords.append({
                "keyword": kw.get("keyword"),
                "volume": kw.get("keyword_info", {}).get("search_volume"),
                "difficulty": kw.get("keyword_properties", {}).get("keyword_difficulty")
            })
    except (KeyError, IndexError, TypeError):
        pass

    console.log(f"[green]Related keywords found:[/green] {len(keywords)}")
    return keywords


def get_serp_top5(keyword: str, country: str = "US") -> list:
    """Obtiene los top 5 resultados orgánicos de Google USA para la keyword."""
    console.log(f"[cyan]Fetching SERP top 5 USA for:[/cyan] {keyword}")

    url = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"
    payload = [{
        "keyword": keyword,
        "location_name": "United States",
        "language_name": "English",
        "device": "desktop",
        "depth": 10
    }]

    with httpx.Client(timeout=60) as client:
        resp = client.post(url, json=payload, headers=get_auth_header())
        resp.raise_for_status()
        data = resp.json()

    results = []
    try:
        items = data["tasks"][0]["result"][0]["items"]
        organic = [i for i in items if i.get("type") == "organic"]
        for item in organic[:5]:
            results.append({
                "position": item.get("rank_absolute"),
                "title": item.get("title"),
                "url": item.get("url"),
                "domain": item.get("domain"),
                "description": item.get("description"),
            })
    except (KeyError, IndexError, TypeError):
        pass

    console.log(f"[green]Top results found:[/green] {len(results)}")
    return results


def scrape_competitor(url: str) -> dict:
    """Extrae estructura (título, meta, H2s, H3s) de una URL competidora."""
    console.log(f"[cyan]Scraping:[/cyan] {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        console.log(f"[red]Error scraping {url}:[/red] {e}")
        return {"url": url, "error": str(e)}

    soup = BeautifulSoup(html, "lxml")

    # Meta
    title = soup.title.string.strip() if soup.title else ""
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "").strip()

    # H1
    h1 = soup.find("h1")
    h1_text = h1.get_text(strip=True) if h1 else ""

    # H2s y H3s
    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h3s = [h.get_text(strip=True) for h in soup.find_all("h3")]

    # Word count aproximado
    body_text = soup.get_text(separator=" ", strip=True)
    word_count = len(body_text.split())

    # Tools mencionadas (búsqueda básica de nombres comunes)
    common_tools = [
        "ServiceNow", "Jira", "Zendesk", "Freshservice", "ManageEngine",
        "SolarWinds", "BMC Helix", "Ivanti", "InvGate", "TOPdesk",
        "Cherwell", "SysAid", "Spiceworks", "HaloITSM", "Hornbill"
    ]
    tools_found = [t for t in common_tools if t.lower() in body_text.lower()]

    console.log(f"[green]Scraped:[/green] {len(h2s)} H2s | ~{word_count} words | {len(tools_found)} tools mentioned")

    return {
        "url": url,
        "title": title,
        "meta_description": meta_desc,
        "h1": h1_text,
        "h2s": h2s,
        "h3s": h3s[:20],  # limitar para no saturar el context
        "word_count": word_count,
        "tools_mentioned": tools_found,
    }


def run_research(keyword: str, country: str = "US") -> dict:
    """Ejecuta toda la fase de research y devuelve el contexto completo."""
    console.rule("[bold blue]FASE 1 — Research[/bold blue]")

    keyword_data = get_keyword_data(keyword, country)
    related_keywords = get_related_keywords(keyword)
    serp = get_serp_top5(keyword, country)

    console.rule("[bold blue]FASE 2 — Scraping competidores[/bold blue]")
    competitors = []
    for result in serp:
        scraped = scrape_competitor(result["url"])
        scraped["serp_title"] = result["title"]
        scraped["serp_description"] = result["description"]
        scraped["position"] = result["position"]
        competitors.append(scraped)

    return {
        "keyword": keyword,
        "keyword_data": keyword_data,
        "related_keywords": related_keywords,
        "serp_top5": serp,
        "competitors": competitors,
    }
