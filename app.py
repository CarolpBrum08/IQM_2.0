# app.py

import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
import json
import folium
from streamlit_folium import st_folium
from io import BytesIO
import time

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="IQM 2025 - Comparador de Microrregiões",
    page_icon="📍",
    layout="wide"
)

# TÍTULO
st.markdown("<h1 style='font-size: 40px;'>📍 Comparador de Microrregiões - IQM 2025</h1>", unsafe_allow_html=True)

# LINKS
json_micro_url = "https://www.dropbox.com/scl/fi/zxqlidj8bl90zfoyg903q/BR_Microrregioes_2022.json?rlkey=146tfdmyvgh58bu5p11zycuko&st=geevr72o&dl=1"
zip_uf_url = "https://www.dropbox.com/scl/fi/59ca4fup55cu3utng68df/BR_UF_2024.zip?rlkey=36m2xsdv0aspalu7zvs2oleuy&st=xlxaq39z&dl=1"
excel_url = "https://www.dropbox.com/scl/fi/b1wxo02asus661r6k6kjb/IQM_BRASIL_2025_V1.xlsm?rlkey=vsu1wm2mi768vqgjknpmbee70&st=8722gdyh&dl=1"

# FUNÇÃO: LOAD GEOJSON MICRORREGIÕES
@st.cache_data(show_spinner=False)
def load_micro_json(url):
    r = requests.get(url)
    r.raise_for_status()
    gdf = gpd.read_file(BytesIO(r.content))
    return gdf

# FUNÇÃO: LOAD UF (ZIP COM SHAPEFILE)
@st.cache_data(show_spinner=False)
def load_uf_shapefile(url):
    r = requests.get(url)
    r.raise_for_status()
    z = zipfile.ZipFile(BytesIO(r.content))
    shp_path = [f for f in z.namelist() if f.endswith('.shp')][0]
    gdf = gpd.read_file(f"zip://{url}")
    return gdf

# FUNÇÃO: LOAD PLANILHA
@st.cache_data(show_spinner=False)
def load_excel(url):
    r = requests.get(url)
    r.raise_for_status()
    df_qualificacao = pd.read_excel(BytesIO(r.content), sheet_name="IQM_Qualificação")
    df_ranking = pd.read_excel(BytesIO(r.content), sheet_name="IQM_Ranking")
    return df_qualificacao, df_ranking

# CARREGA OS DADOS
with st.spinner("🔄 Carregando microrregiões..."):
    gdf_micro = load_micro_json(json_micro_url)

with st.spinner("🔄 Carregando estados (UF)..."):
    gdf_uf = gpd.read_file(f"zip://{zip_uf_url}")

with st.spinner("🔄 Carregando planilha..."):
    df_qualificacao, df_ranking = load_excel(excel_url)

# INTERFACE
ufs = sorted(gdf_micro["UF"].unique())
uf_selecionada = st.selectbox("Selecione o Estado (UF):", ufs)

micros_disponiveis = gdf_micro[gdf_micro["UF"] == uf_selecionada]["NM_MICRO"].unique()
micros_selecionadas = st.multiselect(
    "Selecione Microrregiões para comparar:",
    options=sorted(micros_disponiveis)
)

# MAPA
if len(micros_selecionadas) > 0:

    st.markdown("### 🗺️ Mapa das Microrregiões Selecionadas")

    gdf_micro_sel = gdf_micro[
        (gdf_micro["UF"] == uf_selecionada) &
        (gdf_micro["NM_MICRO"].isin(micros_selecionadas))
    ]

    gdf_uf_sel = gdf_uf[gdf_uf["NM_UF"] == uf_selecionada]

    m = folium.Map(location=[-14.2350, -51.9253], zoom_start=5, tiles="cartodbpositron")

    # Fundo do Estado
    folium.GeoJson(gdf_uf_sel, name="Estado", style_function=lambda x: {
        'fillColor': '#f5f5f5',
        'color': '#000',
        'weight': 1,
        'fillOpacity': 0.2
    }).add_to(m)

    # Microrregiões Selecionadas
    folium.GeoJson(
        gdf_micro_sel,
        name="Microrregiões",
        tooltip=folium.GeoJsonTooltip(fields=["NM_MICRO"]),
        style_function=lambda x: {
            'fillColor': '#FF5733',
            'color': '#FF5733',
            'weight': 2,
            'fillOpacity': 0.5
        }
    ).add_to(m)

    st_folium(m, width=1000, height=600)

    # INDICADORES
    st.markdown("### 📊 Indicadores das Microrregiões Selecionadas")

    df_sel = df_ranking[
        (df_ranking["UF"] == uf_selecionada) &
        (df_ranking["Microrregião"].isin(micros_selecionadas))
    ]

    cols = st.columns(len(df_sel))

    for i, row in df_sel.iterrows():
        nome = row["Microrregião"]
        iqm = row["IQM / 2025"]
        cols[i % len(cols)].metric(nome, round(iqm, 2))

    # RANKING
    st.markdown("### 🏆 Ranking das Microrregiões")

    df_rank = df_sel[["Microrregião", "IQM / 2025"]].sort_values(by="IQM / 2025", ascending=False)
    st.dataframe(df_rank, use_container_width=True)

else:
    st.info("Selecione uma ou mais microrregiões para visualizar.")

