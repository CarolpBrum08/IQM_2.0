# app.py

import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
import zipfile
import io
import os
import plotly.express as px

# CONFIG DA PÁGINA
st.set_page_config(
    page_title="IQM 2025 - Comparador de Microrregiões",
    page_icon="📍",
    layout="wide"
)

# TÍTULO
st.markdown("<h1 style='font-size: 40px;'>📍 Comparador de Microrregiões - IQM 2025</h1>", unsafe_allow_html=True)

# --- LINKS DO SHAPEFILE ZIP E PLANILHA ---

# SHAPEFILE .zip (Dropbox com dl=1)
shapefile_url = "https://www.dropbox.com/scl/fi/9ykpfmts35d0ct0ufh7c6/BR_Microrregioes_2022.zip?rlkey=kjbpqi3f6aeun4ctscae02k9e&st=she208vj&dl=1"

# PLANILHA Excel
excel_url = "https://www.dropbox.com/scl/fi/b1wxo02asus661r6k6kjb/IQM_BRASIL_2025_V1.xlsm?rlkey=vsu1wm2mi768vqgjknpmbee70&st=8722gdyh&dl=1"

# --- FUNÇÃO: CARREGAR SHAPEFILE ZIP ---

@st.cache_data(show_spinner=False)
def load_shapefile_zip(url):
    r = requests.get(url)
    r.raise_for_status()

    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall("geo_tmp")

    shapefiles = [f for f in os.listdir("geo_tmp") if f.endswith(".shp")]
    if not shapefiles:
        st.error("Nenhum .shp encontrado no ZIP!")
        st.stop()

    shp_path = os.path.join("geo_tmp", shapefiles[0])
    gdf = gpd.read_file(shp_path).to_crs(epsg=4326)
    return gdf

# --- FUNÇÃO: CARREGAR PLANILHA REMOTA ---

@st.cache_data(show_spinner=False)
def load_excel(url):
    r = requests.get(url)
    r.raise_for_status()
    df_qualif = pd.read_excel(io.BytesIO(r.content), sheet_name="IQM_Qualificação", header=3)
    df_ranking = pd.read_excel(io.BytesIO(r.content), sheet_name="IQM_Ranking")
    return df_qualif, df_ranking

# --- CARREGA DADOS ---

with st.spinner("🔄 Carregando shapefile..."):
    gdf = load_shapefile_zip(shapefile_url)
st.success("✅ Shapefile carregado com sucesso!", icon="✅")

with st.spinner("🔄 Carregando planilha..."):
    df_qualif, df_ranking = load_excel(excel_url)
st.success("✅ Planilha carregada com sucesso!", icon="✅")

# --- AJUSTE DE COLUNAS ---

df_ranking["Código da Microrregião"] = df_ranking["Código da Microrregião"].astype(str)
if "CD_MICRO" in gdf.columns:
    gdf["CD_MICRO"] = gdf["CD_MICRO"].astype(str)
    geo_df = pd.merge(df_ranking, gdf, left_on="Código da Microrregião", right_on="CD_MICRO")
else:
    gdf["CD_MICRO"] = gdf[gdf.columns[0]].astype(str)
    geo_df = pd.merge(df_ranking, gdf, left_on="Código da Microrregião", right_on="CD_MICRO")

geo_df = gpd.GeoDataFrame(geo_df, geometry="geometry")

# --- INTERFACE ---

# FILTRO UF
ufs = sorted(df_ranking["UF"].unique())
uf_sel = st.selectbox("Selecione o Estado (UF):", ufs)

# FILTRO INDICADOR
indicadores = [
    "IQM / 2025",
    "IQM-D",
    "IQM-C",
    "IQM-IU"
]
indicador_sel = st.selectbox("Selecione o Indicador:", indicadores)

# FILTRO MICRORREGIÕES
df_uf = df_ranking[df_ranking["UF"] == uf_sel]
micro_sel = st.multiselect("Selecione Microrregiões para comparar:", df_uf["Microrregião"].unique())

df_sel = df_ranking[(df_ranking["UF"] == uf_sel) & (df_ranking["Microrregião"].isin(micro_sel))]
geo_sel = geo_df[geo_df["Microrregião"].isin(micro_sel)]

# --- MAPA COM PLOTLY ---

if not geo_sel.empty:
    st.subheader("🗺️ Mapa das Microregiões Selecionadas")
    fig = px.choropleth(
        geo_sel,
        geojson=geo_sel.__geo_interface__,
        locations="Código da Microrregião",
        color=indicador_sel,
        hover_name="Microrregião",
        projection="mercator",
        color_continuous_scale="YlOrBr"
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

    # --- MÉDIAS ---
    st.subheader("📊 Indicadores das Microrregiões Selecionadas")
    cols = st.columns(4)
    cols[0].metric("IQM TOTAL", round(df_sel["IQM / 2025"].mean(), 2))
    cols[1].metric("IQM-D", round(df_sel["IQM-D"].mean(), 2))
    cols[2].metric("IQM-C", round(df_sel["IQM-C"].mean(), 2))
    cols[3].metric("IQM-IU", round(df_sel["IQM-IU"].mean(), 2))

    # --- RANKING ---
    st.subheader("🏆 Ranking das Microrregiões Selecionadas")
    df_rank_sel = df_sel.sort_values(by=indicador_sel, ascending=False).reset_index(drop=True)
    st.dataframe(df_rank_sel[["Microrregião", indicador_sel]], use_container_width=True)

else:
    st.warning("Selecione uma ou mais microrregiões para visualizar.")

# --- MENSAGEM FINAL (exemplo de mensagem temporária) ---
import time
def show_message(msg, delay=3):
    msg_container = st.empty()
    msg_container.success(msg)
    time.sleep(delay)
    msg_container.empty()

# Exemplo:
# show_message("🚀 Tudo carregado!", delay=3)
