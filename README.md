# ITSM Content Bot

Pipeline automatizada para generar y publicar artículos SEO en itsmtools.com.

## Setup

```bash
# 1. Cloná o descargá esta carpeta
cd itsm-content-bot

# 2. Creá el archivo de credenciales
cp .env.example .env
# Editá .env con tus credenciales reales

# 3. Instalá dependencias
pip install -r requirements.txt

# 4. Corré para una keyword
python main.py --keyword "best ITSM tools" --publish draft
```

## Credenciales necesarias en .env

| Variable | Cómo obtenerla |
|---|---|
| `DATAFORSEO_LOGIN` | Tu email en dataforseo.com |
| `DATAFORSEO_PASSWORD` | Tu password en dataforseo.com |
| `WP_URL` | URL de tu WP sin trailing slash |
| `WP_USER` | Tu usuario admin de WP |
| `WP_APP_PASSWORD` | WP Admin → Usuarios → Tu perfil → Application Passwords |
| `ANTHROPIC_API_KEY` | console.anthropic.com |

## Opciones

```bash
# Publicar en borrador (recomendado para revisar)
python main.py -k "best ITSM tools" -p draft

# Publicar directo
python main.py -k "best ITSM tools" -p publish

# Saltar research si ya está guardado en output/research.json
python main.py -k "best ITSM tools" --skip-research

# Saltar generación si ya está en output/article.html
python main.py -k "best ITSM tools" --skip-generate --publish publish
```

## Archivos de salida

Después de correr, encontrás en `output/`:
- `research.json` → todo el keyword data y análisis de competidores
- `article.html` → el HTML generado, listo para revisar antes de publicar

## Customización

- Editá `prompts/article.md` para cambiar el estilo, estructura o tono del artículo
- Editá `CLAUDE.md` para cambiar el contexto del proyecto
- El script es modular: podés correr cada fase por separado con `--skip-research` o `--skip-generate`
