import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import zipfile
import io
import requests
import json
import os

# PRIMEIRO comando Streamlit
st.set_page_config(layout="wide")

# ======= Carga de dados =======
@st.cache_data
def load_data():
    df = pd.read_excel("IQM_BRASIL_2025_V1.xlsm", sheet_name="IQM_Qualificação", header=3)
    ranking = pd.read_excel("IQM_BRASIL_2025_V1.xlsm", sheet_name="IQM_Ranking")
    return df, ranking

@st.cache_data
def load_geo():
    st.info("🔄 Baixando shapefile zipado do Dropbox...")

    url = "https://www.dropbox.com/scl/fi/9ykpfmts35d0ct0ufh7c6/BR_Microrregioes_2022.zip?rlkey=kjbpqi3f6aeun4ctscae02k9e&st=mer376fu&dl=1"

    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall("micros")

    gdf = gpd.read_file("micros/BR_Microrregioes_2022.shp").to_crs(epsg=4326)
    gdf = gdf[['CD_MICRO', 'geometry']]
    return gdf

df, df_ranking = load_data()
gdf = load_geo()

# Ajustar tipos para merge
df["Código da Microrregião"] = df["Código da Microrregião"].astype(str)
gdf["CD_MICRO"] = gdf["CD_MICRO"].astype(str)

# Merge para juntar geometria e indicadores
geo_df = pd.merge(df, gdf, left_on="Código da Microrregião", right_on="CD_MICRO")

# ======= Interface =======
st.title("📊 Dashboard IQM - Microregiões do Brasil")

# Filtro por Estado
ufs = sorted(geo_df["UF"].unique())
uf_sel = st.selectbox("Selecione um Estado (UF):", ufs)
df_uf = geo_df[geo_df["UF"] == uf_sel]

# Seleção de indicador
indicadores = ["IQM", "Desvio Padrão", "Correção", "IQM FINAL", "Top 10 Microregiões (Ranking IQM)"]
ind_sel = st.selectbox("Selecione o Indicador:", indicadores)

# Modo normal
if ind_sel != "Top 10 Microregiões (Ranking IQM)":
    gdf_uf = gpd.GeoDataFrame(df_uf).set_index("Código da Microrregião")
    geojson = json.loads(gdf_uf.to_json())

    st.subheader(f"{ind_sel} - Microregiões de {uf_sel}")
    fig = px.choropleth(
        df_uf,
        geojson=geojson,
        locations="Código da Microrregião",
        color=ind_sel,
        hover_name="Microrregião",
        projection="mercator",
        color_continuous_scale="YlGnBu"
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

    # Ranking normal
    st.subheader("🏆 Ranking por " + ind_sel)
    rank = df_uf[["Microrregião", ind_sel]].sort_values(by=ind_sel, ascending=False).reset_index(drop=True)
    rank.index += 1
    st.dataframe(rank.style.background_gradient(cmap="YlGnBu", subset=[ind_sel]), use_container_width=True)

else:
    st.subheader("🏆 Top 10 Microregiões - Ranking IQM (Brasil)")

    top10 = df_ranking.head(10)
    top10["Código da Microrregião"] = top10["Código da Microrregião"].astype(str)
    df_top10 = geo_df[geo_df["Código da Microrregião"].isin(top10["Código da Microrregião"])]

    gdf_top10 = gpd.GeoDataFrame(df_top10).set_index("Código da Microrregião")
    geojson_top10 = json.loads(gdf_top10.to_json())

    fig = px.choropleth(
        df_top10,
        geojson=geojson_top10,
        locations="Código da Microrregião",
        color="IQM FINAL",
        hover_name="Microrregião",
        projection="mercator",
        color_continuous_scale="YlGnBu"
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

    # Ranking do Top 10
    top10_view = df_top10[["Microrregião", "UF", "IQM FINAL"]].sort_values(by="IQM FINAL", ascending=False).reset_index(drop=True)
    top10_view.index += 1
    st.dataframe(top10_view.style.background_gradient(cmap="YlGnBu", subset=["IQM FINAL"]), use_container_width=True)

# Detalhes por Microrregião
if ind_sel != "Top 10 Microregiões (Ranking IQM)":
    micros = sorted(df_uf["Microrregião"].unique())
    mic_sel = st.selectbox("Selecione uma Microrregião para detalhes:", micros)
    df_micro = df_uf[df_uf["Microrregião"] == mic_sel]
    st.write(df_micro.T.iloc[-4:])

# Tabela completa
with st.expander("📁 Ver tabela completa"):
    st.dataframe(df_uf, use_container_width=True)
