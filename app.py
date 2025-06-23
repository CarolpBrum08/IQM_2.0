import streamlit as st
import pandas as pd
import requests # Mantido por precaução, caso use para outras APIs no futuro
import json
import plotly.express as px
import io
import os # Para verificar se os arquivos locais existem

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="IQM 2025 - Comparador de Microrregiões",
    page_icon="📍",
    layout="wide"
)

# TÍTULO
st.markdown("<h1 style='font-size: 40px;'>📍 Comparador de Microrregiões - IQM 2025</h1>", unsafe_allow_html=True)

# --- CAMINHOS LOCAIS DOS DADOS ---
# ATENÇÃO: Estes caminhos agora apontam para os arquivos DENTRO do seu repositório Git!
geojson_local_path = "data/BR_Microrregioes_2022.json"
planilha_local_path = "data/IQM_BRASIL_2025_V1.xlsm"

# --- FUNÇÕES ---

@st.cache_resource(show_spinner=True)
def load_geojson_local():
    """
    Carrega o arquivo GeoJSON das microrregiões de um caminho local.
    """
    if not os.path.exists(geojson_local_path):
        st.error(f"Erro: O arquivo GeoJSON não foi encontrado em '{geojson_local_path}'. "
                 "Verifique se ele foi adicionado corretamente ao repositório na pasta 'data'.")
        st.stop() # Interrompe a execução do Streamlit se o arquivo não estiver lá
    try:
        with open(geojson_local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        st.error(f"Erro ao decodificar JSON do arquivo '{geojson_local_path}'. "
                 "Verifique a validade do arquivo GeoJSON.")
        st.stop()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar o GeoJSON: {e}")
        st.stop()


@st.cache_data(show_spinner=True)
def load_planilha_local():
    """
    Carrega a planilha IQM de um caminho local.
    """
    if not os.path.exists(planilha_local_path):
        st.error(f"Erro: A planilha IQM não foi encontrada em '{planilha_local_path}'. "
                 "Verifique se ela foi adicionada corretamente ao repositório na pasta 'data'.")
        st.stop() # Interrompe a execução do Streamlit se o arquivo não estiver lá
    try:
        df_ranking = pd.read_excel(planilha_local_path, sheet_name="IQM_Ranking")
        return df_ranking
    except FileNotFoundError: # Já coberto pelo os.path.exists, mas como fallback
        st.error(f"Erro: O arquivo da planilha não foi encontrado em '{planilha_local_path}'.")
        st.stop()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar a planilha: {e}")
        st.stop()


# --- CARREGAR DADOS ---

with st.spinner("🔄 Carregando GeoJSON localmente..."):
    geojson_data = load_geojson_local()

with st.spinner("🔄 Carregando planilha localmente..."):
    df_ranking = load_planilha_local()

# --- INTERFACE ---

# Filtro Estado
# Garante que a coluna "UF" e "Microrregião" existem antes de tentar usá-las
if "UF" not in df_ranking.columns or df_ranking["UF"].empty:
    st.error("Coluna 'UF' não encontrada ou vazia na planilha. Verifique a planilha.")
    st.stop()
if "Microrregião" not in df_ranking.columns:
    st.error("Coluna 'Microrregião' não encontrada na planilha. Verifique a planilha.")
    st.stop()
if "Código da Microrregião" not in df_ranking.columns:
    st.error("Coluna 'Código da Microrregião' não encontrada na planilha. É essencial para o mapa.")
    st.stop()

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

    # O featureidkey 'properties.CD_MICRO' é o nome da propriedade no GeoJSON
    # Certifique-se que o GeoJSON tem essa estrutura e que 'CD_MICRO' é o código da microrregião.
    # Se o seu GeoJSON tiver um nome de campo diferente para o código da microrregião,
    # você precisará ajustar 'properties.CD_MICRO' aqui.

    fig = px.choropleth_map(
        df_sel,
        geojson=geojson_data,
        locations="Código da Microrregião", # Coluna no DataFrame com o ID da microrregião
        featureidkey="properties.CD_MICRO", # Caminho para o ID no GeoJSON
        color=indicador_sel,
        hover_name="Microrregião",
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
