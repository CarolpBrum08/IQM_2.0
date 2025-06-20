import streamlit as st
import pandas as pd
import requests
import json
import plotly.express as px
import io

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="IQM 2025 - Comparador de Microrregiões",
    page_icon="📍",
    layout="wide"
)

# TÍTULO
st.markdown("<h1 style='font-size: 40px;'>📍 Comparador de Microrregiões - IQM 2025</h1>", unsafe_allow_html=True)

# --- URLS ---

# GeoJSON (direto do Dropbox)
geofile_url = "https://www.dropbox.com/scl/fi/zxqlidj8bl90zfoyg903q/BR_Microrregioes_2022.json?rlkey=146tfdmyvgh58bu5p11zycuko&st=geevr72o&dl=1"

# Planilha IQM
df_url = "https://www.dropbox.com/scl/fi/b1wxo02asus661r6k6kjb/IQM_BRASIL_2025_V1.xlsm?rlkey=vsu1wm2mi768vqgjknpmbee70&st=8722gdyh&dl=1"

# --- FUNÇÕES ---

@st.cache_resource(show_spinner=True)
def load_geojson():
    response = requests.get(geofile_url)
    response.raise_for_status()
    return json.loads(response.content)

@st.cache_data(show_spinner=True)
def load_planilha():
    r = requests.get(df_url)
    r.raise_for_status()
    df_ranking = pd.read_excel(io.BytesIO(r.content), sheet_name="IQM_Ranking")
    return df_ranking

# --- CARREGAR DADOS ---

with st.spinner("🔄 Carregando GeoJSON..."):
    geojson_data = load_geojson()

with st.spinner("🔄 Carregando planilha..."):
    df_ranking = load_planilha()

# --- INTERFACE ---

# Filtro Estado
ufs = sorted(df_ranking["UF"].unique())
uf_sel = st.selectbox("Selecione o Estado (UF):", ufs)

# Filtro Indicador
indicadores = [
    "IQM / 2025",
    "IQM-D",
    "IQM-C",
    "IQM-IU"
]
indicador_sel = st.selectbox("Selecione o Indicador:", indicadores)

# Filtro Microrregião
micros = df_ranking[df_ranking["UF"] == uf_sel]["Microrregião"].unique()
micros_sel = st.multiselect("Selecione Microrregiões para comparar:", sorted(micros))

# --- EXIBIR MAPA ---

if len(micros_sel) > 0:

    df_sel = df_ranking[(df_ranking["UF"] == uf_sel) & (df_ranking["Microrregião"].isin(micros_sel))]

    st.subheader("🌍 Mapa das Microrregiões Selecionadas")

    fig = px.choropleth_mapbox(
        df_sel,
        geojson=geojson_data,
        locations="Código da Microrregião",
        featureidkey="properties.CD_MICRO",
        color=indicador_sel,
        hover_name="Microrregião",
        mapbox_style="carto-positron",
        center={"lat": -15, "lon": -53},
        zoom=4.5,
        color_continuous_scale="YlOrBr",
        height=500
    )

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    st.plotly_chart(fig, use_container_width=True)

    # --- RANKING ---
    st.subheader("🏆 Ranking das Microrregiões Selecionadas")

    df_rank = df_sel[["Microrregião", indicador_sel]]
    df_rank = df_rank.sort_values(by=indicador_sel, ascending=False).reset_index(drop=True)

    st.dataframe(df_rank, use_container_width=True)

else:
    st.warning("Selecione uma ou mais microrregiões para visualizar.")
