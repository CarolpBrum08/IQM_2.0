import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import requests
import zipfile
import io

# Configuração da página
st.set_page_config(layout="wide", page_title="Comparador de Microrregiões - IQM 2025", page_icon="📍")

# Títulos e instruções
st.markdown("<h1 style='font-size: 36px;'>📍 Comparador de Microrregiões - IQM 2025</h1>", unsafe_allow_html=True)

# URL do novo shapefile de microrregiões 2022
shapefile_url = "https://www.dropbox.com/scl/fi/9ykpfmts35d0ct0ufh7c6/BR_Microrregioes_2022.zip?rlkey=kjbpqi3f6aeun4ctscae02k9e&st=she208vj&dl=1"

# Nome do arquivo Excel que está no mesmo nível do script
excel_file = "IQM_Qualificação_2025.xlsx"

# Baixa e carrega o shapefile
with st.spinner("Baixando shapefile zipado..."):
    r = requests.get(shapefile_url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(".")

# Identifica o arquivo .shp extraído
import os
shp_file = [f for f in os.listdir(".") if f.endswith(".shp")][0]

# Carrega o shapefile como GeoDataFrame
geo = gpd.read_file(shp_file)

# Padroniza nomes de colunas
geo = geo.rename(columns={
    "CD_MICRO": "CD_MICRO",
    "NM_MICRO": "Microrregião",
    "NM_UF": "UF"
})

# Lê o Excel
with st.spinner("Carregando dados da planilha..."):
    df = pd.read_excel(excel_file, sheet_name="IQM_Qualificação")

# Faz o merge entre shapefile e Excel
geo_df = pd.merge(geo, df, on="CD_MICRO", how="inner")

# Mensagens de sucesso (com toast)
st.toast("🗺️ Shapefile carregado com sucesso!")
st.toast("📊 Planilha carregada com sucesso!")

# Sidebar - filtros
st.sidebar.header("Filtros")

uf_sel = st.sidebar.selectbox("Selecione o Estado (UF):", sorted(geo_df["UF"].unique()))

# Filtra microrregiões do estado escolhido
df_uf = geo_df[geo_df["UF"] == uf_sel]
micros_uf = sorted(df_uf["Microrregião"].unique())

micro_sel = st.sidebar.multiselect("Selecione Microrregiões para comparar:", micros_uf)

# Mostra resultados se tiver seleção
geo_sel = geo_df[geo_df["Microrregião"].isin(micro_sel)]

if not geo_sel.empty:
    st.subheader("🗺️ Mapa das Microrregiões Selecionadas")

    fig = px.choropleth_mapbox(
        geo_sel,
        geojson=geo_sel.geometry,
        locations=geo_sel.index,
        color="IQM FINAL",
        hover_name="Microrregião",
        hover_data={"IQM FINAL": True, "UF": True},
        mapbox_style="carto-positron",
        center={"lat": geo_sel.geometry.centroid.y.mean(), "lon": geo_sel.geometry.centroid.x.mean()},
        zoom=5,
        opacity=0.7
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Indicadores das Microrregiões")
    st.dataframe(geo_sel[["UF", "Microrregião", "IQM FINAL"]].sort_values(by="IQM FINAL", ascending=False), use_container_width=True)

else:
    st.warning("Selecione uma ou mais microregiões para visualizar.")
