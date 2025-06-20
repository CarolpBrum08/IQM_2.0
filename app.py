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

# --- LINKS ---

shapefile_url = "https://www.dropbox.com/scl/fi/9ykpfmts35d0ct0ufh7c6/BR_Microrregioes_2022.zip?rlkey=kjbpqi3f6aeun4ctscae02k9e&st=she208vj&dl=1"
uf_url = "https://www.dropbox.com/scl/fi/59ca4fup55cu3utng68df/BR_UF_2024.zip?rlkey=36m2xsdv0aspalu7zvs2oleuy&st=xlxaq39z&dl=1"
excel_url = "https://www.dropbox.com/scl/fi/b1wxo02asus661r6k6kjb/IQM_BRASIL_2025_V1.xlsm?rlkey=vsu1wm2mi768vqgjknpmbee70&st=8722gdyh&dl=1"

# --- LOAD SHAPEFILE ZIP ---
@st.cache_data(show_spinner=False)
def load_shapefile_zip(url):
    r = requests.get(url)
    r.raise_for_status()

    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall("geo_tmp")

    shp_path = [f for f in os.listdir("geo_tmp") if f.endswith(".shp")][0]
    full_path = os.path.join("geo_tmp", shp_path)

    gdf = gpd.read_file(full_path).to_crs(epsg=4326)
    return gdf

# --- LOAD EXCEL ---
@st.cache_data(show_spinner=False)
def load_excel(url):
    r = requests.get(url)
    r.raise_for_status()
    df_qualif = pd.read_excel(io.BytesIO(r.content), sheet_name="IQM_Qualificação", header=3)
    df_ranking = pd.read_excel(io.BytesIO(r.content), sheet_name="IQM_Ranking")
    return df_qualif, df_ranking

# --- LOAD DATA ---
with st.spinner("🔄 Carregando Microrregiões..."):
    gdf = load_shapefile_zip(shapefile_url)

with st.spinner("🔄 Carregando UFs..."):
    gdf_uf = load_shapefile_zip(uf_url)

with st.spinner("🔄 Carregando planilha..."):
    df_qualif, df_ranking = load_excel(excel_url)

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

    # --- RANKING ---
    st.subheader("🏆 Ranking das Microrregiões Selecionadas")
    df_rank = df_sel[["Microrregião", indicador_sel]].sort_values(by=indicador_sel, ascending=False).reset_index(drop=True)
    st.dataframe(df_rank, use_container_width=True)

else:
    st.info("Selecione uma ou mais microrregiões para visualizar.")
