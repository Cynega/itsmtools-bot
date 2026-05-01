# ITSM Content Bot

Pipeline automatizada para generar y publicar artículos SEO en **itsmtools.com**.
Stack: **Next.js (UI)** + **Vercel Python serverless functions (pipeline)** + Claude API + DataForSEO + WordPress REST.

## Arquitectura

```
itsmtools-bot/
├── app/                  # Next.js App Router (UI)
│   ├── page.tsx          # Form de keywords + estado
│   ├── layout.tsx
│   └── globals.css
├── api/
│   └── generate.py       # POST /api/generate — corre la pipeline
├── pipeline/             # módulos Python compartidos
│   ├── research.py       # DataForSEO + scraping de competidores
│   ├── generate.py       # llamada a Claude API
│   └── publish.py        # WordPress REST API
├── prompts/
│   └── article.md        # system prompt
├── requirements.txt      # deps de la function Python
├── package.json          # deps de Next.js
└── vercel.json           # runtime + maxDuration + includeFiles
```

## Pipeline (en orden)

1. **Research de keyword** → DataForSEO: volumen, dificultad, CPC, keywords secundarias
2. **SERP USA** → DataForSEO: top 5 resultados orgánicos
3. **Scraping competidores** → httpx + BeautifulSoup: títulos, H2/H3, word count, tools mencionadas
4. **Generación** → Claude API con el system prompt de `prompts/article.md`
5. **Publicación** → WordPress REST API (draft o publish)

## Setup local

```bash
# 1. Instalar deps
npm install
pip install -r requirements.txt

# 2. Variables de entorno
cp .env.example .env.local
# Editar .env.local con las credenciales reales

# 3. Levantar Vercel dev server (UI + Python function)
npx vercel dev
# Abrir http://localhost:3000
```

> Para correr **solo la UI** sin la function Python: `npm run dev`. El form va a fallar al hacer submit porque `/api/generate` solo corre con `vercel dev`.

## Deploy a Vercel

```bash
# Primera vez: linkear el proyecto
npx vercel link

# Cargar las env vars desde .env.local al proyecto en Vercel
npx vercel env pull   # baja las que ya estén
# o cargarlas en Dashboard → Settings → Environment Variables

# Deploy
npx vercel --prod
```

## Variables de entorno

| Variable | Cómo obtenerla |
|---|---|
| `DATAFORSEO_LOGIN` | Email en dataforseo.com |
| `DATAFORSEO_PASSWORD` | Password en dataforseo.com |
| `WP_URL` | URL de WP sin trailing slash (ej. `https://itsmtools.com`) |
| `WP_USER` | Usuario admin de WP |
| `WP_APP_PASSWORD` | WP Admin → Usuarios → Tu perfil → Application Passwords |
| `ANTHROPIC_API_KEY` | console.anthropic.com |

## Endpoint

`POST /api/generate`

```json
{
  "keyword": "best ITSM tools",
  "country": "US",
  "status": "draft"
}
```

Respuesta:

```json
{
  "keyword": "best ITSM tools",
  "research": { "volume": 1000, "cpc": 12.5, "competitors": 5 },
  "article": { "word_count": 2350 },
  "publish": { "success": true, "id": 1234, "url": "https://itsmtools.com/?p=1234", "status": "draft" }
}
```

## Notas

- El artículo se publica en **inglés (US)** porque el sitio apunta a esa audiencia.
- Por defecto se crea en **draft** para revisar antes de publicar.
- **InvGate** siempre aparece en el listado (producto de referencia del autor).
- La function Python tiene `maxDuration: 300s` en `vercel.json`. Si una keyword tarda más, hay que mover a un job async (cola + polling).
- El sistema antiguo de `--skip-research` (basado en archivos en `output/`) **se removió** en la migración a Vercel — el filesystem es efímero. Si lo necesitás, hay que portar a Vercel Blob o KV.
