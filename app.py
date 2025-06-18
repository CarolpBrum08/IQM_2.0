import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import zipfile
import io
import requests
import os

# Configuração da página
st.set_page_config(layout="wide", page_title="Comparador de Microregiões - IQM 2025")

# URL do shapefile zipado
URL_ZIP = "https://www.dropbox.com/scl/fi/ij1y8m3bwn6voyr7xrj4p/BR_RG_Imediatas_2024.zip?rlkey=npfrxoci8ufu2zap40grp8zxr&st=hhzu0dup&dl=1"

# Função para baixar e extrair o zip
@st.cache_data(show_spinner=False)
def load_geo_from_zip(url):
    r = requests.get(url)
    if r.headers.get("Content-Type") not in ["application/zip", "application/octet-stream"]:
        st.error("Erro: o link não retornou um ZIP válido. Verifique a URL.")
        st.stop()
    
    z = zipfile.ZipFile(io.BytesIO(r.content))
    os.makedirs("geo_tmp", exist_ok=True)
    z.extractall("geo_tmp")
    
    shp_files = [f for f in os.listdir("geo_tmp") if f.endswith(".shp")]
    if not shp_files:
        st.error("Nenhum .shp encontrado no ZIP!")
        st.stop()
    
    shp_path = os.path.join("geo_tmp", shp_files[0])
    gdf = gpd.read_file(shp_path).to_crs(epsg=4326)
    
    return gdf

# Função para carregar a planilha
@st.cache_data
def load_excel():
    df_qualif = pd.read_excel("data/IQM_BRASIL_2025_V1.xlsm", sheet_name="IQM_Qualificação", header=3)
    df_ranking = pd.read_excel("data/IQM_BRASIL_2025_V1.xlsm", sheet_name="IQM_Ranking")
    return df_qualif, df_ranking

# --- BOTÃO ATUALIZAR ---
st.sidebar.title("⚙️ Opções")
update_map = st.sidebar.button("🔄 Atualizar Shapefile")

# --- LOADING ---
with st.spinner("🔄 Carregando shapefile..."):
    if update_map:
        st.cache_data.clear()
    gdf = load_geo_from_zip(URL_ZIP)

# --- LOAD PLANILHAS ---
df_qualif, df_ranking = load_excel()

# --- AJUSTES ---
df_qualif["Código da Microrregião"] = df_qualif["Código da Microrregião"].astype(str)
df_ranking["Código da Microrregião"] = df_ranking["Código da Microrregião"].astype(str)

if "CD_MICRO" in gdf.columns:
    gdf["CD_MICRO"] = gdf["CD_MICRO"].astype(str)
    geo_df = pd.merge(df_ranking, gdf, left_on="Código da Microrregião", right_on="CD_MICRO")
else:
    gdf["CD_MICRO"] = gdf[gdf.columns[0]].astype(str)
    geo_df = pd.merge(df_ranking, gdf, left_on="Código da Microrregião", right_on="CD_MICRO")

geo_df = gpd.GeoDataFrame(geo_df, geometry="geometry")

# --- TÍTULO ---
st.title("📍 Comparador de Microregiões - IQM 2025")

# --- FILTROS ---
ufs = sorted(df_ranking["UF"].unique())
uf_sel = st.selectbox("Selecione o Estado (UF):", ufs)

df_uf = df_ranking[df_ranking["UF"] == uf_sel]
micro_sel = st.multiselect("Selecione Microregiões para comparar:", df_uf["Microrregião"].unique())

df_sel = df_ranking[(df_ranking["UF"] == uf_sel) & (df_ranking["Microrregião"].isin(micro_sel))]
geo_sel = geo_df[geo_df["Microrregião"].isin(micro_sel)]

# --- MAPA ---
if not geo_sel.empty:
    st.subheader("🗺️ Mapa das Microregiões Selecionadas")
    fig = px.choropleth(
        geo_sel,
        geojson=geo_sel.__geo_interface__,
        locations="Código da Microrregião",
        color="IQM / 2025",
        hover_name="Microrregião",
        projection="mercator",
        color_continuous_scale="YlOrBr"
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

    # --- CARDS ---
    st.subheader("📊 Indicadores das Microregiões Selecionadas")
    cols = st.columns(4)
    cols[0].metric("IQM TOTAL", round(df_sel["IQM / 2025"].mean(), 2))
    cols[1].metric("IQM-D", round(df_sel["IQM-D"].mean(), 2))
    cols[2].metric("IQM-C", round(df_sel["IQM-C"].mean(), 2))
    cols[3].metric("IQM-IU", round(df_sel["IQM-IU"].mean(), 2))

    # --- TABELA ---
    st.subheader("📋 Tabela Qualificação - Detalhe das Selecionadas")
    df_qualif_sel = df_qualif[df_qualif["Microrregião"].isin(micro_sel)]
    st.dataframe(df_qualif_sel, use_container_width=True)
else:
    st.warning("⚠️ Selecione uma ou mais microregiões para visualizar.")
