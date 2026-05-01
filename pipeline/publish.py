"""
publish.py
Fase 4 de la pipeline:
- Recibe el HTML generado + metadata (excerpt, focus keyword, category, tags)
- Sube imagen como media de WordPress (si vino)
- Resuelve categoría y tags contra whitelists, sin crear nuevos
- Crea el post en WP con featured image, excerpt y meta de Yoast
"""

import os
import re
import base64
import httpx


def log(msg: str) -> None:
    print(f"[publish] {msg}", flush=True)


# Whitelists — las categorías y tags tienen que existir ya en WP.
# Cualquier valor fuera de estas listas se descarta silenciosamente.
ALLOWED_CATEGORIES = ["Best", "Compare", "Learn", "Reviews"]
DEFAULT_CATEGORY = "Best"
ALLOWED_TAGS = [
    "ITSM",
    "ITIL",
    "Service Desk",
    "Incident Management",
    "Change Management",
    "Ticketing",
    "Knowledge Management",
    "Problem Management",
    "IT Support",
]


def get_wp_headers() -> dict:
    user = os.getenv("WP_USER")
    app_password = os.getenv("WP_APP_PASSWORD", "").replace(" ", "")
    token = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def resolve_term_id(
    wp_url: str, taxonomy: str, name: str, headers: dict
) -> int | None:
    """Busca un term existente por slug. Nunca crea. Devuelve ID o None."""
    slug = slugify(name)
    if not slug:
        return None
    url = f"{wp_url}/wp-json/wp/v2/{taxonomy}"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params={"slug": slug}, headers=headers)
        if resp.status_code != 200:
            log(f"resolve {taxonomy}/{slug}: HTTP {resp.status_code}")
            return None
        items = resp.json()
        if isinstance(items, list) and items:
            return items[0].get("id")
    except Exception as e:
        log(f"resolve {taxonomy}/{slug} failed: {e}")
    return None


def filter_to_whitelist(
    names: list[str], whitelist: list[str]
) -> list[str]:
    """Devuelve los nombres canónicos del whitelist que matchean (case-insensitive)."""
    by_lower = {w.lower(): w for w in whitelist}
    out: list[str] = []
    for n in names or []:
        canonical = by_lower.get((n or "").strip().lower())
        if canonical and canonical not in out:
            out.append(canonical)
    return out


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


def publish_to_wordpress(
    title: str,
    content_html: str,
    keyword: str,
    status: str = "draft",
    tag_names: list[str] | None = None,
    category_name: str | None = None,
    meta_description: str = "",
    focus_keyword: str = "",
    featured_media_id: int | None = None,
) -> dict:
    """
    Publica o crea en borrador un post en WordPress, con excerpt, Yoast meta
    y categoría/tags resueltos contra whitelists.

    status: 'draft' | 'publish'
    """
    log("FASE 4 — Publicación en WordPress")

    wp_url = os.getenv("WP_URL", "").rstrip("/")
    headers = get_wp_headers()

    # Categoría — solo whitelist, default a Best.
    chosen_cat = (
        category_name
        if category_name in ALLOWED_CATEGORIES
        else DEFAULT_CATEGORY
    )
    cat_id = resolve_term_id(wp_url, "categories", chosen_cat, headers)
    log(f"Category: {chosen_cat} (ID: {cat_id})")

    # Tags — filtramos al whitelist y resolvemos por slug. Sin crear.
    canonical_tags = filter_to_whitelist(tag_names or [], ALLOWED_TAGS)
    tag_ids: list[int] = []
    for t in canonical_tags:
        tid = resolve_term_id(wp_url, "tags", t, headers)
        if tid:
            tag_ids.append(tid)
    log(f"Tags: {canonical_tags} → IDs {tag_ids}")

    # Yoast SEO + subtitle del theme. Yoast Free desde v14 expone los meta al
    # REST API. Si tu theme usa otra key para el subtitle, ajustar abajo.
    meta: dict[str, object] = {}
    if focus_keyword:
        meta["_yoast_wpseo_focuskw"] = focus_keyword
    if meta_description:
        meta["_yoast_wpseo_metadesc"] = meta_description
        # Best-effort para el subtitle del theme — probamos las keys más comunes.
        meta["subtitle"] = meta_description
        meta["_subtitle"] = meta_description
        meta["wps_subtitle"] = meta_description
    if cat_id:
        meta["_yoast_wpseo_primary_category"] = cat_id

    payload: dict[str, object] = {
        "title": title,
        "content": content_html,
        "status": status,
        "tags": tag_ids,
        "excerpt": meta_description or "",
    }
    if cat_id:
        payload["categories"] = [cat_id]
    if featured_media_id:
        payload["featured_media"] = featured_media_id
    if meta:
        payload["meta"] = meta

    post_url = f"{wp_url}/wp-json/wp/v2/posts"
    log(f"Posting to: {post_url} as '{status}'")

    with httpx.Client(timeout=30) as client:
        resp = client.post(post_url, json=payload, headers=headers)

    if resp.status_code in (200, 201):
        post_data = resp.json()
        post_link = post_data.get("link", "")
        post_id = post_data.get("id")
        log(f"Post created! ID: {post_id} | URL: {post_link}")
        return {
            "success": True,
            "id": post_id,
            "url": post_link,
            "status": status,
            "category": chosen_cat,
            "tags": canonical_tags,
        }

    log(f"ERROR posting: {resp.status_code} - {resp.text[:500]}")
    return {
        "success": False,
        "error": resp.text,
        "status_code": resp.status_code,
    }
