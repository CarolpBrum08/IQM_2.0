import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import requests
import zipfile
import io
import json
import os

# Configuração da página
st.set_page_config(layout="wide", page_title="Comparador de Microrregiões - IQM 2025", page_icon="📍")

st.markdown("<h1 style='font-size: 36px;'>📍 Comparador de Microrregiões - IQM 2025</h1>", unsafe_allow_html=True)

# URL do shapefile
shapefile_url = "https://www.dropbox.com/scl/fi/9ykpfmts35d0ct0ufh7c6/BR_Microrregioes_2022.zip?rlkey=kjbpqi3f6aeun4ctscae02k9e&st=she208vj&dl=1"

# Nome do Excel
excel_file = "IQM_Qualificação_2025.xlsx"

# Baixa e carrega shapefile
with st.spinner("Baixando shapefile zipado..."):
    r = requests.get(shapefile_url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(".")

# Identifica arquivo .shp
shp_file = [f for f in os.listdir(".") if f.endswith(".shp")][0]

# Lê shapefile
geo = gpd.read_file(shp_file)

# Renomeia colunas
geo = geo.rename(columns={
    "CD_MICRO": "Código da Microrregião",
    "NM_MICRO": "Microrregião",
    "NM_UF": "UF"
})

# Lê Excel
with st.spinner("Carregando dados da planilha..."):
    df = pd.read_excel(excel_file, sheet_name="IQM_Qualificação")

# Faz merge
geo_df = pd.merge(geo, df, on="Código da Microrregião", how="inner")

# Toasts
st.toast("🗺️ Shapefile carregado com sucesso!", icon="✅")
st.toast("📊 Planilha carregada com sucesso!", icon="✅")

# Cria abas
tab1, tab2 = st.tabs(["🌍 Comparador de Microrregiões", "🏆 Top 10 IQM"])

# --- Aba Comparador ---
with tab1:
    st.sidebar.header("Filtros")

    uf_sel = st.sidebar.selectbox("Selecione o Estado (UF):", sorted(geo_df["UF"].unique()))

    df_uf = geo_df[geo_df["UF"] == uf_sel]
    micros_uf = sorted(df_uf["Microrregião"].unique())

    micro_sel = st.sidebar.multiselect("Selecione Microrregiões para comparar (busque por nome):", micros_uf)

    # Campo de escolha do indicador
    numeric_cols = geo_df.select_dtypes(include='number').columns.tolist()
    indicator_sel = st.sidebar.selectbox("Selecione o indicador:", numeric_cols)

    geo_sel = geo_df[geo_df["Microrregião"].isin(micro_sel)]

    if not geo_sel.empty:
        st.subheader(f"🗺️ Mapa - Indicador: {indicator_sel}")

        geojson = json.loads(geo_sel.to_json())

        fig = px.choropleth_mapbox(
            geo_sel,
            geojson=geojson,
            locations=geo_sel.index,
            color=indicator_sel,
            hover_name="Microrregião",
            hover_data={indicator_sel: True, "UF": True},
            mapbox_style="carto-positron",
            center={"lat": geo_sel.geometry.centroid.y.mean(), "lon": geo_sel.geometry.centroid.x.mean()},
            zoom=5,
            opacity=0.7
        )
        st.plotly_chart(fig, use_container_width=True)

        # Ranking
        st.subheader(f"📋 Indicadores das Microrregiões ({indicator_sel})")
        df_rank = geo_sel[["UF", "Microrregião", indicator_sel]].sort_values(by=indicator_sel, ascending=False)
        st.dataframe(df_rank, use_container_width=True)

        # Botão para download
        csv = df_rank.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar tabela em CSV",
            data=csv,
            file_name=f"IQM_Microrregioes_{indicator_sel}.csv",
            mime='text/csv'
        )
    else:
        st.info("Selecione uma ou mais microrregiões para visualizar.")

# --- Aba Top 10 ---
with tab2:
    st.subheader("🏆 Top 10 Microrregiões com maior IQM FINAL no Brasil")

    top10 = geo_df[["UF", "Microrregião", "IQM FINAL"]].sort_values(by="IQM FINAL", ascending=False).head(10)

    st.dataframe(top10, use_container_width=True)

    top10_csv = top10.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Top 10 em CSV",
        data=top10_csv,
        file_name="Top10_IQM.csv",
        mime='text/csv'
    )
