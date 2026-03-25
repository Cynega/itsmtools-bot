"""
app.py — Interfaz Streamlit para ITSM Content Bot
Genera y publica artículos SEO en itsmtools.com
"""

import streamlit as st
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Cargar st.secrets en os.environ para que el pipeline los lea igual que en local
for key, value in st.secrets.items():
    if key not in os.environ:
        os.environ[key] = str(value)

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.research import run_research
from pipeline.generate import generate_article
from pipeline.publish import publish_to_wordpress

# ————————————————————————————————————————
# Config de página
# ————————————————————————————————————————
st.set_page_config(
    page_title="ITSM Content Bot",
    page_icon="✍️",
    layout="centered"
)

st.title("✍️ ITSM Content Bot")
st.caption("Generador automático de artículos SEO para itsmtools.com")
st.divider()

# ————————————————————————————————————————
# Formulario principal
# ————————————————————————————————————————
st.subheader("Configuración")

keywords_input = st.text_area(
    "Keywords (una por línea)",
    placeholder="best ITSM tools\nbest help desk software\nITSM vs ITSM comparison",
    height=120,
    help="Podés poner una o varias keywords. Se genera un artículo por cada una."
)

col1, col2 = st.columns(2)

with col1:
    publish_status = st.selectbox(
        "Estado en WordPress",
        options=["draft", "publish"],
        index=0,
        help="'draft' = borrador para revisar. 'publish' = publica directo."
    )

with col2:
    country = st.selectbox(
        "País del SERP",
        options=["US", "GB", "AU", "CA"],
        index=0,
        help="País para el análisis de competidores en Google."
    )

skip_research = st.checkbox(
    "Saltar research (usar research.json guardado)",
    value=False,
    help="Útil si ya hiciste el research antes y solo querés regenerar el artículo."
)

st.divider()

# ————————————————————————————————————————
# Botón de generación
# ————————————————————————————————————————
if st.button("🚀 Generar artículos", type="primary", use_container_width=True):

    keywords = [k.strip() for k in keywords_input.strip().splitlines() if k.strip()]

    if not keywords:
        st.error("Escribí al menos una keyword.")
        st.stop()

    OUTPUT_DIR = Path("output")
    OUTPUT_DIR.mkdir(exist_ok=True)

    for i, keyword in enumerate(keywords):
        st.subheader(f"📄 {keyword}")

        # — Research —
        research_file = OUTPUT_DIR / f"research_{keyword[:30].replace(' ', '_')}.json"

        if skip_research and research_file.exists():
            with st.spinner("Cargando research guardado..."):
                with open(research_file) as f:
                    research = json.load(f)
            st.success(f"Research cargado desde archivo guardado.")
        else:
            with st.spinner("Analizando keyword y competidores en Google USA..."):
                try:
                    research = run_research(keyword, country)
                    with open(research_file, "w") as f:
                        json.dump(research, f, indent=2, ensure_ascii=False)
                    kd = research.get("keyword_data", {})
                    st.success(
                        f"Research completo — "
                        f"Volumen: **{kd.get('volume', 'N/A')}** | "
                        f"CPC: **${kd.get('cpc', 'N/A')}** | "
                        f"Competidores analizados: **{len(research.get('competitors', []))}**"
                    )
                except Exception as e:
                    st.error(f"Error en research: {e}")
                    continue

        # — Generación —
        article_file = OUTPUT_DIR / f"article_{keyword[:30].replace(' ', '_')}.html"

        with st.spinner("Generando artículo con Claude AI..."):
            try:
                article_html = generate_article(research)
                article_file.write_text(article_html, encoding="utf-8")
                word_count = len(article_html.split())
                st.success(f"Artículo generado — ~{word_count} palabras")
            except Exception as e:
                st.error(f"Error generando artículo: {e}")
                continue

        # — Publicación —
        title = keyword.title() + ": Top Picks for 2025"

        with st.spinner("Publicando en WordPress..."):
            try:
                result = publish_to_wordpress(
                    title=title,
                    content_html=article_html,
                    keyword=keyword,
                    status=publish_status,
                )
                if result.get("success"):
                    wp_url = result.get("url", "")
                    st.success(f"✅ Publicado en WordPress")
                    st.markdown(f"🔗 [Ver borrador en WordPress]({wp_url})")
                else:
                    st.error(f"Error publicando: {result.get('error', '')}")
            except Exception as e:
                st.error(f"Error publicando: {e}")
                continue

        if i < len(keywords) - 1:
            st.divider()

    st.balloons()
    st.success("¡Todo listo!")

# ————————————————————————————————————————
# Footer
# ————————————————————————————————————————
st.divider()
st.caption("itsmtools.com · ITSM Content Bot · Powered by Claude AI + DataForSEO")
