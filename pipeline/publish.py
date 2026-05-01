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


def log(msg: str) -> None:
    print(f"[publish] {msg}", flush=True)


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


def upload_media(
    wp_url: str,
    image_bytes: bytes,
    mime: str,
    filename: str,
    alt_text: str = "",
) -> int | None:
    """Sube bytes a /wp-json/wp/v2/media y devuelve el ID, o None si falla."""
    user = os.getenv("WP_USER")
    app_password = os.getenv("WP_APP_PASSWORD", "").replace(" ", "")
    token = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    upload_url = f"{wp_url}/wp-json/wp/v2/media"

    log(f"Uploading {filename} ({len(image_bytes) // 1024} KB) to WP media")
    with httpx.Client(timeout=60) as client:
        try:
            resp = client.post(
                upload_url,
                content=image_bytes,
                headers={
                    "Authorization": f"Basic {token}",
                    "Content-Type": mime,
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
        except Exception as e:
            log(f"media upload error: {e}")
            return None

        if resp.status_code not in (200, 201):
            log(f"media upload failed: {resp.status_code} {resp.text[:200]}")
            return None

        media_id = resp.json().get("id")
        log(f"uploaded as media ID {media_id}")

        if alt_text and media_id:
            try:
                client.post(
                    f"{upload_url}/{media_id}",
                    json={"alt_text": alt_text},
                    headers={
                        "Authorization": f"Basic {token}",
                        "Content-Type": "application/json",
                    },
                )
            except Exception as e:
                log(f"alt_text update failed (non-fatal): {e}")

        return media_id


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
    featured_media_id: int | None = None,
) -> dict:
    """
    Publica o crea en borrador un post en WordPress.
    status: 'draft' | 'publish'
    """
    log("FASE 4 — Publicación en WordPress")

    wp_url = os.getenv("WP_URL", "").rstrip("/")
    headers = get_wp_headers()

    # Resolver categoría
    cat_id = None
    if category:
        cat_id = get_or_create_category(wp_url, category, headers)
        log(f"Category: {category} (ID: {cat_id})")

    # Resolver tags
    tag_ids = []
    default_tags = ["ITSM", "IT Service Management", keyword]
    all_tags = list(set((tags or []) + default_tags))
    for tag in all_tags:
        tag_id = get_or_create_tag(wp_url, tag, headers)
        if tag_id:
            tag_ids.append(tag_id)
    log(f"Tags resolved: {len(tag_ids)}")

    # Construir payload
    payload = {
        "title": title,
        "content": content_html,
        "status": status,
        "tags": tag_ids,
    }
    if cat_id:
        payload["categories"] = [cat_id]
    if featured_media_id:
        payload["featured_media"] = featured_media_id

    # Crear post
    post_url = f"{wp_url}/wp-json/wp/v2/posts"
    log(f"Posting to: {post_url} as '{status}'")

    with httpx.Client(timeout=30) as client:
        resp = client.post(post_url, json=payload, headers=headers)

    if resp.status_code in (200, 201):
        post_data = resp.json()
        post_link = post_data.get("link", "")
        post_id = post_data.get("id")
        log(f"Post created! ID: {post_id} | URL: {post_link}")
        return {"success": True, "id": post_id, "url": post_link, "status": status}
    else:
        print(f"ERROR posting: {resp.status_code} - {resp.text[:500]}")
        return {"success": False, "error": resp.text, "status_code": resp.status_code}
