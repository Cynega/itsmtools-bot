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

## Seguridad y privacidad

La app aplica varias capas de defensa para evitar abuso de las APIs (DataForSEO,
Anthropic, WordPress) y para no aparecer en buscadores ni ser scrapeada por LLMs.

### A nivel código (ya aplicado)

- `public/robots.txt` bloquea `User-agent: *` + lista explícita de crawlers de
  IA (GPTBot, ClaudeBot, anthropic-ai, PerplexityBot, Google-Extended, CCBot,
  Bytespider, Applebot-Extended, etc.).
- Meta `<meta name="robots" content="noindex, nofollow, noarchive, nosnippet,
  noimageindex">` inyectado en cada respuesta HTML.
- Header HTTP `X-Robots-Tag` con los mismos directives en todas las rutas.
  Más difícil de ignorar que `robots.txt` para crawlers de IA agresivos.
- Headers de seguridad globales: HSTS preload, `X-Frame-Options: DENY`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`,
  `Permissions-Policy` denegando cámara/mic/geolocation/FLoC,
  `Cross-Origin-Opener-Policy` y `Cross-Origin-Resource-Policy` en `same-origin`.
- `poweredByHeader: false` para no filtrar que corre en Next.js.
- `/api/generate` valida `Origin`/`Referer` contra el host actual:
  bloquea cualquier POST que no venga del mismo dominio (cURL desde afuera,
  scripts cross-origin, etc.).
- Validación estricta de input: keyword ≤200 chars, country en lista blanca
  (`US`/`GB`/`AU`/`CA`), status en lista blanca (`draft`/`publish`).
- El error que devuelve el endpoint en caso de fallo es genérico para no
  filtrar información del stack interno; el detalle queda en los logs.

### A nivel Vercel (ACCIÓN REQUERIDA)

La capa más importante: **encender Deployment Protection** para que solo vos
puedas acceder a la URL pública. Sin esto, cualquiera con la URL puede gatillar
la pipeline y consumir tus créditos de DataForSEO/Anthropic + crear drafts en
WordPress.

1. Vercel Dashboard → proyecto `itsmtools-bot` → **Settings** → **Deployment Protection**
2. En **Vercel Authentication** elegí **"Standard Protection"** (incluido en Pro).
   - Aplica tanto a Production como a Preview deployments.
   - Solo miembros de tu team Vercel pueden acceder.
3. Save.

Si querés que sea accesible desde un dispositivo donde no estés logueado en
Vercel (ej. una netbook nueva), usá **"Password Protection"** en lugar de
Standard: te deja definir un password que cualquier visitante tiene que
ingresar para entrar al sitio.

### Notas

- El artículo se publica en **inglés (US)** porque el sitio apunta a esa audiencia.
- Por defecto se crea en **draft** para revisar antes de publicar.
- **InvGate** siempre aparece en el listado (producto de referencia del autor).
- La function Python tiene `maxDuration: 300s` en `vercel.json`. Si una keyword tarda más, hay que mover a un job async (cola + polling).
- El sistema antiguo de `--skip-research` (basado en archivos en `output/`) **se removió** en la migración a Vercel — el filesystem es efímero. Si lo necesitás, hay que portar a Vercel Blob o KV.
