"""
api/generate.py — Vercel Python serverless function

POST /api/generate
Body JSON: { "keyword": str, "country": "US"|..., "status": "draft"|"publish" }

Ejecuta la pipeline completa (research → generate → publish) y devuelve
un JSON con el resumen + URL del post de WordPress.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
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
)


def derive_title(keyword: str) -> str:
    return f"{keyword.strip().title()}: Top Picks for 2026"


def run_pipeline(keyword: str, country: str, status: str) -> dict:
    research = run_research(keyword, country)
    article_html = generate_article(research)
    publish = publish_to_wordpress(
        title=derive_title(keyword),
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
        "article": {"word_count": len(article_html.split())},
        "publish": publish,
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid JSON body"})
            return

        keyword = (body.get("keyword") or "").strip()
        country = body.get("country", "US")
        status = body.get("status", "draft")

        if not keyword:
            self._send(400, {"error": "keyword is required"})
            return
        if status not in ("draft", "publish"):
            self._send(400, {"error": "status must be 'draft' or 'publish'"})
            return

        missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
        if missing:
            self._send(500, {"error": f"missing env vars: {', '.join(missing)}"})
            return

        try:
            result = run_pipeline(keyword, country, status)
        except Exception as e:
            self._send(500, {"keyword": keyword, "error": str(e)})
            return

        ok = bool(result.get("publish", {}).get("success"))
        self._send(200 if ok else 502, result)

    def do_GET(self):
        self._send(200, {"status": "ok", "endpoint": "POST /api/generate"})

    def _send(self, code: int, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
