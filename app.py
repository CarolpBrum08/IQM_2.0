# app.py

import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
import io
import folium
from streamlit_folium import st_folium

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="IQM 2025 - Comparador de Microrregiões",
    page_icon="📍",
    layout="wide"
)

# TÍTULO
st.markdown("<h1 style='font-size: 40px;'>📍 Comparador de Microrregiões - IQM 2025</h1>", unsafe_allow_html=True)

# --- LINKS DO GEOJSON E PLANILHA ---

# GeoJSON
geojson_url = "https://www.dropbox.com/scl/fi/zxqlidj8bl90zfoyg903q/BR_Microrregioes_2022.json?rlkey=146tfdmyvgh58bu5p11zycuko&st=geevr72o&dl=1"

# Planilha Excel
excel_url = "https://www.dropbox.com/scl/fi/b1wxo02asus661r6k6kjb/IQM_BRASIL_2025_V1.xlsm?rlkey=vsu1wm2mi768vqgjknpmbee70&st=8722gdyh&dl=1"

# --- FUNÇÃO: CARREGAR GEOJSON REMOTO ---
@st.cache_data(show_spinner=False)
def load_geojson(url):
    r = requests.get(url)
    r.raise_for_status()
    gdf = gpd.read_file(io.BytesIO(r.content))
    return gdf

# --- FUNÇÃO: CARREGAR PLANILHA REMOTA ---
@st.cache_data(show_spinner=False)
def load_excel(url):
    r = requests.get(url)
    r.raise_for_status()
    df_qualificacao = pd.read_excel(io.BytesIO(r.content), sheet_name="IQM_Qualificação")
    df_ranking = pd.read_excel(io.BytesIO(r.content), sheet_name="IQM_Ranking")
    return df_qualificacao, df_ranking

# --- CARREGA DADOS ---
with st.spinner("🔄 Carregando GeoJSON..."):
    gdf = load_geojson(geojson_url)
st.success("✅ GeoJSON carregado com sucesso!", icon="✅")

with st.spinner("🔄 Carregando planilha..."):
    df_qualificacao, df_ranking = load_excel(excel_url)
st.success("✅ Planilha carregada com sucesso!", icon="✅")

# --- INTERFACE ---

# Filtro por Estado
ufs = sorted(gdf["UF"].unique())
uf_selecionada = st.selectbox("Selecione o Estado (UF):", ufs)

# Filtro por Microrregião
micros_disponiveis = gdf[gdf["UF"] == uf_selecionada]["NM_MICRO"].unique()
micros_selecionadas = st.multiselect(
    "Selecione Microrregiões para comparar:",
    options=sorted(micros_disponiveis)
)

# Exibe mapa se houver seleção
if len(micros_selecionadas) > 0:
    gdf_filtrado = gdf[
        (gdf["UF"] == uf_selecionada) & 
        (gdf["NM_MICRO"].isin(micros_selecionadas))
    ]

    # Cria mapa
    m = folium.Map(location=[-14.2350, -51.9253], zoom_start=5, tiles="cartodbpositron")
    folium.GeoJson(gdf_filtrado, name="Microrregiões").add_to(m)

    # Mostra no Streamlit
    st_folium(m, width=1000, height=600)
else:
    st.warning("Selecione uma ou mais microrregiões para visualizar.")

# --- MENSAGENS TEMPORÁRIAS (some depois de alguns segundos) ---
import time

def show_message(msg, delay=3):
    msg_container = st.empty()
    msg_container.success(msg)
    time.sleep(delay)
    msg_container.empty()

# Exemplo:
# show_message("🚀 Dados prontos!", delay=3)
