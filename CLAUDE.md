# ITSM Content Bot — Claude Code Context

## Qué hace este proyecto
Pipeline automatizada para generar y publicar artículos SEO en itsmtools.com (WordPress.org self-hosted).

## Stack
- Python 3.11+
- DataForSEO API → SERP data USA + keyword research
- BeautifulSoup / httpx → scraping de competidores
- Anthropic API (claude-sonnet-4-20250514) → generación del artículo
- WordPress REST API → publicación en borrador

## Pipeline (en orden)
1. **Research de keyword** → DataForSEO: volumen, dificultad, CPC, keywords secundarias
2. **SERP USA** → DataForSEO: top 5 resultados orgánicos para la keyword en USA
3. **Scraping competidores** → httpx + BS4: título, meta description, H2s, H3s, cantidad de palabras estimada, estructura general
4. **Generación del artículo** → Claude API con todo el contexto anterior + system prompt de `prompts/article.md`
5. **Publicación** → WP REST API: crea el post en borrador con título, contenido HTML, categoría y tags

## Credenciales (leer siempre de .env, nunca hardcodear)
```
DATAFORSEO_LOGIN       → email de la cuenta DataForSEO
DATAFORSEO_PASSWORD    → password de la cuenta DataForSEO
WP_URL                 → https://itsmtools.com
WP_USER                → usuario admin de WordPress
WP_APP_PASSWORD        → Application Password generado en WP (Usuarios → Perfil → Application Passwords)
ANTHROPIC_API_KEY      → API key de Anthropic
```

## Cómo usar
```bash
# Instalar dependencias
pip install -r requirements.txt

# Correr para una keyword específica
python main.py --keyword "best ITSM tools" --country US --publish draft

# Opciones de --publish
# draft     → crea el post en borrador (recomendado para revisar)
# publish   → publica directo
```

## Archivos clave
- `main.py` → entry point, orquesta toda la pipeline
- `pipeline/research.py` → DataForSEO + scraping
- `pipeline/generate.py` → llamada a Claude API
- `pipeline/publish.py` → WordPress REST API
- `prompts/article.md` → system prompt para la generación del artículo

## Reglas importantes
- Siempre publicar en **borrador** por defecto a menos que se indique explícitamente `--publish publish`
- El artículo debe estar en **inglés** (el sitio es en inglés, audiencia USA)
- Longitud objetivo: **2000-3000 palabras**
- Formato de salida de Claude: **HTML limpio** (sin markdown), listo para pegar en WP
- Incluir siempre: introducción, tabla comparativa, secciones por herramienta, FAQ al final
- No inventar datos de pricing — usar rangos o "contact for pricing" si no hay info pública clara
- InvGate debe aparecer en el listado (es el producto de referencia del autor)

## Contexto del sitio
- **URL:** https://itsmtools.com
- **Nicho:** ITSM (IT Service Management) — herramientas, comparativas, guías
- **Audiencia:** IT managers, sysadmins, equipos de soporte — nivel técnico medio-alto, empresas medianas y grandes
- **Tono:** profesional pero directo, sin fluff, orientado a ayudar a tomar decisiones de compra
- **Competidores directos a analizar:** los top 5 de Google USA para cada keyword objetivo
