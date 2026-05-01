"""
image.py
Busca una foto relevante en Unsplash, la descarga en 16:9 ≤250 KB,
y devuelve los bytes + datos de atribución.

Atribución obligatoria por las API guidelines de Unsplash:
https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines
"""

import os
import httpx


def log(msg: str) -> None:
    print(f"[image] {msg}", flush=True)


UNSPLASH_API = "https://api.unsplash.com"
UTM_SUFFIX = "?utm_source=itsmtools_bot&utm_medium=referral"
TARGET_KB = 250

# Tamaños/qualities a probar hasta caer bajo TARGET_KB.
SIZE_VARIANTS = [
    {"w": 1600, "h": 900, "q": 80},
    {"w": 1600, "h": 900, "q": 70},
    {"w": 1280, "h": 720, "q": 75},
    {"w": 1280, "h": 720, "q": 60},
    {"w": 1024, "h": 576, "q": 70},
]


def fetch_image(query: str) -> dict | None:
    """Busca y devuelve una imagen 16:9 lista para subir, o None si falla.

    Estructura del dict:
        {
            "bytes": bytes,
            "mime": "image/jpeg",
            "alt": str,
            "photographer_name": str,
            "photographer_url": str,
            "unsplash_url": str,
        }
    """
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key:
        log("UNSPLASH_ACCESS_KEY missing — skipping image step")
        return None
    if not query:
        log("empty query — skipping image step")
        return None

    headers = {"Authorization": f"Client-ID {access_key}"}

    log(f"Fetching random Unsplash photo for: {query!r}")
    # /photos/random devuelve uno distinto en cada llamada para la misma query,
    # mejor que /search/photos para no repetir fotos con queries similares.
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(
                f"{UNSPLASH_API}/photos/random",
                params={
                    "query": query,
                    "orientation": "landscape",
                    "content_filter": "high",
                },
                headers=headers,
            )
            if r.status_code == 404:
                log("no Unsplash result for this query")
                return None
            r.raise_for_status()
            photo = r.json()
    except Exception as e:
        log(f"Unsplash random fetch failed: {e}")
        return None

    if not isinstance(photo, dict):
        log("unexpected Unsplash payload")
        return None

    raw_url = photo.get("urls", {}).get("raw")
    download_endpoint = photo.get("links", {}).get("download_location")
    user = photo.get("user") or {}
    photographer_name = user.get("name") or "Unknown"
    photographer_link = (user.get("links") or {}).get("html") or "https://unsplash.com"
    alt = photo.get("alt_description") or query

    if not raw_url:
        log("no raw URL in Unsplash response")
        return None

    # Trigger del endpoint de download (requerido por las guidelines).
    if download_endpoint:
        try:
            with httpx.Client(timeout=10) as client:
                client.get(download_endpoint, headers=headers)
        except Exception as e:
            log(f"download trigger failed (non-fatal): {e}")

    image_bytes = _download_under_target(raw_url)
    if not image_bytes:
        return None

    return {
        "bytes": image_bytes,
        "mime": "image/jpeg",
        "alt": alt,
        "photographer_name": photographer_name,
        "photographer_url": f"{photographer_link}{UTM_SUFFIX}",
        "unsplash_url": f"https://unsplash.com{UTM_SUFFIX}",
    }


def _download_under_target(raw_url: str) -> bytes | None:
    """Itera variantes hasta encontrar una <=TARGET_KB."""
    last_bytes: bytes | None = None
    for variant in SIZE_VARIANTS:
        url = (
            f"{raw_url}?fit=crop&crop=entropy&fm=jpg&auto=format"
            f"&w={variant['w']}&h={variant['h']}&q={variant['q']}"
        )
        try:
            with httpx.Client(timeout=20) as client:
                resp = client.get(url)
                resp.raise_for_status()
                content = resp.content
        except Exception as e:
            log(f"download failed at {variant}: {e}")
            continue
        size_kb = len(content) / 1024
        log(f"  variant {variant} → {size_kb:.0f} KB")
        last_bytes = content
        if size_kb <= TARGET_KB:
            return content
    if last_bytes is not None:
        log(f"no variant under {TARGET_KB} KB; using smallest available ({len(last_bytes)//1024} KB)")
    return last_bytes


def attribution_html(image_meta: dict) -> str:
    """HTML de atribución obligatoria, para apendear al final del artículo."""
    name = image_meta.get("photographer_name", "")
    photo_url = image_meta.get("photographer_url", "")
    unsplash_url = image_meta.get("unsplash_url", "")
    return (
        f'<p><small>Photo by '
        f'<a href="{photo_url}" target="_blank" rel="noopener">{name}</a> '
        f'on <a href="{unsplash_url}" target="_blank" rel="noopener">Unsplash</a>'
        f"</small></p>"
    )
