import streamlit as st
import pandas as pd
import requests # Mantido por precaução, caso use para outras APIs no futuro
import json
import plotly.express as px
import io
import os # Para verificar se os arquivos locais existem

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Top 10 IQM / 2025 - Brasil",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- TÍTULO DA PÁGINA ---
st.markdown("<h1 style='font-size: 40px;'>🏆 Top 10 Microrregiões - IQM / 2025 Brasil</h1>", unsafe_allow_html=True)

# --- CAMINHOS LOCAIS DOS DADOS ---
GEOJSON_MICRORREGIOES_PATH = "data/BR_Microrregioes_2022.1.json"
EXCEL_IQM_PATH = "data/IQM_BRASIL_2025_V1.xlsm"

# --- FUNÇÕES PARA CARREGAMENTO DE DADOS (COM CACHE) ---
@st.cache_resource(show_spinner="🔄 Carregando GeoJSON das Microrregiões...")
def load_geojson_local(path):
    if not os.path.exists(path):
        st.error(f"Erro: O arquivo GeoJSON não foi encontrado em '{path}'. "
                 "Verifique se ele foi adicionado corretamente ao repositório na pasta 'data'.")
        st.stop()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        st.error(f"Erro ao decodificar JSON do arquivo '{path}'. "
                 "Verifique a validade do arquivo GeoJSON.")
        st.stop()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar o GeoJSON: {e}")
        st.stop()

@st.cache_data(show_spinner="🔄 Carregando Planilha IQM...")
def load_planilha_local(path):
    if not os.path.exists(path):
        st.error(f"Erro: A planilha IQM não foi encontrada em '{path}'. "
                 "Verifique se ela foi adicionada corretamente ao repositório na pasta 'data'.")
        st.stop()
    try:
        df_ranking = pd.read_excel(path, sheet_name="IQM_Ranking", engine='openpyxl')
        return df_ranking
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar a planilha: {e}")
        st.stop()

# --- CARREGAR DADOS NA INICIALIZAÇÃO DO APP ---
geojson_data = load_geojson_local(GEOJSON_MICRORREGIOES_PATH)
df_ranking = load_planilha_local(EXCEL_IQM_PATH)

# --- CONVERTE O CÓDIGO DA MICRORREGIÃO PARA STRING E GARANTE QUE NÃO HÁ ESPAÇOS EXTRAS ---
df_ranking['Código da Microrregião'] = df_ranking['Código da Microrregião'].astype(str).str.strip()

# --- LISTA DE TODOS OS INDICADORES IQM (para a tabela) ---
TODOS_INDICADORES_IQM = [
    "IQM / 2025", "IQM-D", "IQM-C", "IQM-IU", # Adicione mais se tiver
]
TODOS_INDICADORES_IQM = [ind for ind in TODOS_INDICADORES_IQM if ind in df_ranking.columns]


# --- LÓGICA PARA TOP 10 IQM / 2025 ---
# Garante que a coluna existe antes de tentar filtrar
if "IQM / 2025" in df_ranking.columns:
    df_top_10 = df_ranking.nlargest(10, "IQM / 2025").copy()
else:
    st.error("Coluna 'IQM / 2025' não encontrada para gerar o Top 10. Verifique o nome na planilha.")
    st.stop()


# --- VISUALIZAÇÃO DO MAPA ---
st.subheader("🌍 Mapa das Top 10 Microrregiões")

if not df_top_10.empty:
    fig = px.choropleth_map(
        df_top_10, # Usando o DataFrame do Top 10
        geojson=geojson_data,
        locations="Código da Microrregião",
        featureidkey="properties.CD_MICRO",
        color="IQM / 2025", # Colorir pelo IQM / 2025
        hover_name="Microrregião",
        # --- AJUSTES DE ZOOM E CENTRO DO MAPA PARA O BRASIL ---
        # Pode ser necessário ajustar o zoom para mostrar melhor as top 10 espalhadas
        center={"lat": -15, "lon": -53}, # Centro do Brasil
        zoom=3.5, # Zoom geral do Brasil
        color_continuous_scale="YlOrBr",
        height=500
    )

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhuma microrregião encontrada para o Top 10. Verifique os dados.")


# --- RANKING DAS MICRORREGIÕES ---
st.subheader("🏆 Top 10 Microrregiões - IQM / 2025")

if not df_top_10.empty:
    # Prepara as colunas para o DataFrame, incluindo UF e todos os indicadores IQM
    cols_to_display = ["Microrregião", "UF"] + TODOS_INDICADORES_IQM
    df_rank_top_10 = df_top_10[cols_to_display].copy()

    # Adiciona uma coluna de ranking começando do 1
    df_rank_top_10 = df_rank_top_10.sort_values(by="IQM / 2025", ascending=False).reset_index(drop=True)
    df_rank_top_10.index = df_rank_top_10.index + 1 # Ajusta o índice para começar de 1
    df_rank_top_10.index.name = "Ranking"

    # Cria a configuração de coluna para centralizar os IQMs
    column_config = {
        "Microrregião": st.column_config.Column("Microrregião", help="Nome da Microrregião"),
        "UF": st.column_config.Column("UF", help="Unidade Federativa"),
        "Ranking": st.column_config.Column("Ranking", help="Posição no ranking", width="small")
    }
    for ind in TODOS_INDICADORES_IQM:
        column_config[ind] = st.column_config.NumberColumn(
            label=ind,
            help=f"Valor do indicador {ind}",
            format="%.2f",
            text_align="center"
        )

    # Exibe a tabela interativa com as configurações de coluna
    st.dataframe(df_rank_top_10, use_container_width=True, column_config=column_config)