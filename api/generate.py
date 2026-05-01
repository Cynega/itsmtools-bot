"""
api/generate.py — Vercel Python serverless function

POST /api/generate
Body JSON: { "keyword": str, "country": "US"|..., "status": "draft"|"publish" }

Ejecuta la pipeline completa (research → generate → publish) y devuelve
un JSON con el resumen + URL del post de WordPress.
"""

from http.server import BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.research import run_research
from pipeline.generate import generate_article
from pipeline.publish import publish_to_wordpress

REQUIRED_ENV = (
    "DATAFORSEO_LOGIN",
    "DATAFORSEO_PASSWORD",
    "WP_URL",
    "WP_USER",
    "WP_APP_PASSWORD",
    "ANTHROPIC_API_KEY",
    "AUTH_SECRET",
)

ALLOWED_COUNTRIES = {"US", "GB", "AU", "CA"}
ALLOWED_STATUSES = {"draft", "publish"}
KEYWORD_MAX_LEN = 200
AUTH_COOKIE = "auth"


def fallback_title(keyword: str) -> str:
    """Solo se usa si Claude no devolvió el comment <!-- TITLE: ... -->."""
    return f"{keyword.strip().title()}: Top Picks for 2026"


def is_same_origin(headers) -> bool:
    """Solo aceptamos requests cuyo Origin/Referer corresponda al host actual."""
    expected_host = headers.get("x-forwarded-host") or headers.get("host")
    if not expected_host:
        return False
    candidate = headers.get("origin") or headers.get("referer")
    if not candidate:
        return False
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False
    return parsed.netloc.lower() == expected_host.lower()


def verify_auth_cookie(headers) -> bool:
    """Verifica el cookie HMAC firmado por /api/auth/login (Next.js)."""
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        return False
    cookie_header = headers.get("cookie") or ""
    if not cookie_header:
        return False
    try:
        jar = SimpleCookie()
        jar.load(cookie_header)
    except Exception:
        return False
    morsel = jar.get(AUTH_COOKIE)
    if not morsel:
        return False
    token = morsel.value
    parts = token.split(".")
    if len(parts) != 2:
        return False
    expiry_str, mac = parts
    try:
        expiry = int(expiry_str)
    except ValueError:
        return False
    if expiry < int(time.time()):
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        expiry_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(mac, expected)


def run_pipeline(keyword: str, country: str, status: str) -> dict:
    research = run_research(keyword, country)
    article = generate_article(research)
    article_html = article["html"]
    title = article.get("title") or fallback_title(keyword)
    publish = publish_to_wordpress(
        title=title,
        content_html=article_html,
        keyword=keyword,
        status=status,
    )
    kd = research.get("keyword_data", {})
    return {
        "keyword": keyword,
        "research": {
            "volume": kd.get("volume"),
            "cpc": kd.get("cpc"),
            "competitors": len(research.get("competitors", [])),
        },
        "article": {"word_count": len(article_html.split()), "title": title},
        "publish": publish,
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not is_same_origin(self.headers):
            self._send(403, {"error": "forbidden"})
            return
        if not verify_auth_cookie(self.headers):
            self._send(401, {"error": "unauthorized"})
            return

        try:
            length = int(self.headers.get("content-length", 0))
        except ValueError:
            self._send(400, {"error": "invalid content-length"})
            return
        if length <= 0 or length > 4096:
            self._send(413, {"error": "request body too large"})
            return

        try:
            raw = self.rfile.read(length)
            body = json.loads(raw or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON body"})
            return
        if not isinstance(body, dict):
            self._send(400, {"error": "invalid body shape"})
            return

        keyword = body.get("keyword")
        country = body.get("country", "US")
        status = body.get("status", "draft")

        if not isinstance(keyword, str):
            self._send(400, {"error": "keyword must be a string"})
            return
        keyword = keyword.strip()
        if not keyword:
            self._send(400, {"error": "keyword is required"})
            return
        if len(keyword) > KEYWORD_MAX_LEN:
            self._send(400, {"error": f"keyword exceeds {KEYWORD_MAX_LEN} chars"})
            return
        if not isinstance(country, str) or country not in ALLOWED_COUNTRIES:
            self._send(400, {"error": "invalid country"})
            return
        if not isinstance(status, str) or status not in ALLOWED_STATUSES:
            self._send(400, {"error": "invalid status"})
            return

        missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
        if missing:
            self._send(500, {"error": "server misconfigured"})
            return

        try:
            result = run_pipeline(keyword, country, status)
        except Exception as e:
            print(f"[api] pipeline error: {e}", flush=True)
            self._send(500, {"keyword": keyword, "error": "pipeline failed"})
            return

        ok = bool(result.get("publish", {}).get("success"))
        self._send(200 if ok else 502, result)

    def do_GET(self):
        self._send(405, {"error": "method not allowed"})

    def _send(self, code: int, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header(
            "X-Robots-Tag",
            "noindex, nofollow, noarchive, nosnippet, noimageindex, notranslate",
        )
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)
