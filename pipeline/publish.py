"""
publish.py
Fase 4 de la pipeline:
- Recibe el HTML generado
- Lo publica en WordPress via REST API
- Devuelve la URL del post creado
"""

import os
import base64
import httpx
from rich.console import Console

console = Console()


def get_wp_headers() -> dict:
    user = os.getenv("WP_USER")
    app_password = os.getenv("WP_APP_PASSWORD", "").replace(" ", "")
    token = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def get_or_create_tag(wp_url: str, tag_name: str, headers: dict) -> int | None:
    """Busca un tag existente o lo crea. Devuelve el ID."""
    search_url = f"{wp_url}/wp-json/wp/v2/tags"
    resp = httpx.get(search_url, params={"search": tag_name}, headers=headers, timeout=15)
    tags = resp.json()
    if tags and isinstance(tags, list):
        return tags[0]["id"]

    # Crear si no existe
    resp = httpx.post(search_url, json={"name": tag_name}, headers=headers, timeout=15)
    if resp.status_code == 201:
        return resp.json()["id"]
    return None


def get_or_create_category(wp_url: str, cat_name: str, headers: dict) -> int | None:
    """Busca una categoría existente o la crea. Devuelve el ID."""
    search_url = f"{wp_url}/wp-json/wp/v2/categories"
    resp = httpx.get(search_url, params={"search": cat_name}, headers=headers, timeout=15)
    cats = resp.json()
    if cats and isinstance(cats, list):
        return cats[0]["id"]

    resp = httpx.post(search_url, json={"name": cat_name}, headers=headers, timeout=15)
    if resp.status_code == 201:
        return resp.json()["id"]
    return None


def publish_to_wordpress(
    title: str,
    content_html: str,
    keyword: str,
    status: str = "draft",
    tags: list[str] = None,
    category: str = "ITSM Tools",
) -> dict:
    """
    Publica o crea en borrador un post en WordPress.
    status: 'draft' | 'publish'
    """
    console.rule("[bold blue]FASE 4 — Publicación en WordPress[/bold blue]")

    wp_url = os.getenv("WP_URL", "").rstrip("/")
    headers = get_wp_headers()

    # Resolver categoría
    cat_id = None
    if category:
        cat_id = get_or_create_category(wp_url, category, headers)
        console.log(f"[cyan]Category:[/cyan] {category} (ID: {cat_id})")

    # Resolver tags
    tag_ids = []
    default_tags = ["ITSM", "IT Service Management", keyword]
    all_tags = list(set((tags or []) + default_tags))
    for tag in all_tags:
        tag_id = get_or_create_tag(wp_url, tag, headers)
        if tag_id:
            tag_ids.append(tag_id)
    console.log(f"[cyan]Tags resolved:[/cyan] {len(tag_ids)}")

    # Construir payload
    payload = {
        "title": title,
        "content": content_html,
        "status": status,
        "tags": tag_ids,
    }
    if cat_id:
        payload["categories"] = [cat_id]

    # Crear post
    post_url = f"{wp_url}/wp-json/wp/v2/posts"
    console.log(f"[cyan]Posting to:[/cyan] {post_url} as '{status}'")

    with httpx.Client(timeout=30) as client:
        resp = client.post(post_url, json=payload, headers=headers)

    if resp.status_code in (200, 201):
        post_data = resp.json()
        post_link = post_data.get("link", "")
        post_id = post_data.get("id")
        console.log(f"[bold green]Post created![/bold green] ID: {post_id} | URL: {post_link}")
        return {"success": True, "id": post_id, "url": post_link, "status": status}
    else:
        print(f"ERROR posting: {resp.status_code} - {resp.text[:500]}")
        return {"success": False, "error": resp.text, "status_code": resp.status_code}
