import streamlit as st
import pandas as pd
import requests # Mantido por precaução, caso use para outras APIs no futuro
import json
import plotly.express as px
import io
import os # Para verificar se os arquivos locais existem

# --- CONFIGURAÇÃO DA PÁGINA ---
# Esta configuração será para esta página específica
st.set_page_config(
    page_title="Comparador de Microrregiões - IQM 2025",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- TÍTULO DO APLICATIVO ---
st.markdown("<h1 style='font-size: 40px;'>📍 Comparador de Microrregiões - IQM 2025</h1>", unsafe_allow_html=True)

# --- CAMINHOS LOCAIS DOS DADOS ---
GEOJSON_MICRORREGIOES_PATH = "data/BR_Microrregioes_2022.1.json"
EXCEL_IQM_PATH = "data/IQM_BRASIL_2025_V1.xlsm"

# --- FUNÇÕES PARA CARREGAMENTO DE DADOS (COM CACHE) ---
# (Manter as funções de cache resource e data aqui, o Streamlit as gerencia bem entre páginas)
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

# --- VERIFICAÇÃO DE COLUNAS ESSENCIAIS NO DATAFRAME ---
required_cols = ["UF", "Microrregião", "Código da Microrregião"]
for col in required_cols:
    if col not in df_ranking.columns:
        st.error(f"Erro: Coluna '{col}' não encontrada na planilha. Por favor, verifique a planilha.")
        st.stop()

if df_ranking["UF"].empty:
    st.error("Coluna 'UF' está vazia na planilha. Não é possível filtrar por estado.")
    st.stop()

# --- LISTA DE TODOS OS INDICADORES IQM (para a tabela) ---
TODOS_INDICADORES_IQM = [
    "IQM / 2025", "IQM-D", "IQM-C", "IQM-IU", # Adicione mais se tiver
]
TODOS_INDICADORES_IQM = [ind for ind in TODOS_INDICADORES_IQM if ind in df_ranking.columns]


# --- INTERFACE (SIDEBAR) ---
st.sidebar.header("Filtros de Seleção")

# Filtro Estados (UF) - AGORA MULTISELECT
ufs = sorted(df_ranking["UF"].unique().tolist())
ufs_sel = st.sidebar.multiselect("Selecione os Estados (UF):", ufs, default=ufs[0] if ufs else [])

if not ufs_sel:
    st.sidebar.warning("Por favor, selecione pelo menos um Estado.")
    st.stop()

# Filtro Indicador para COLORIR O MAPA (ainda um selectbox simples)
indicadores_disponiveis_mapa = [ind for ind in TODOS_INDICADORES_IQM]
indicador_sel_mapa = st.sidebar.selectbox("Selecione o Indicador para colorir o Mapa:", indicadores_disponiveis_mapa)


# Filtro Microrregião (Baseado nos Estados Selecionados)
df_micros_estados_sel = df_ranking[df_ranking["UF"].isin(ufs_sel)]
micros_por_estados_sel = sorted(df_micros_estados_sel["Microrregião"].unique().tolist())

micros_sel = st.sidebar.multiselect("Selecione Microrregiões para comparar:", micros_por_estados_sel)

# --- LÓGICA DE FILTRAGEM DOS DADOS PARA O MAPA E RANKING ---
df_sel = df_ranking[df_ranking["UF"].isin(ufs_sel)].copy()

if micros_sel: # Se alguma microrregião foi selecionada, filtra ainda mais
    df_sel = df_sel[df_sel["Microrregião"].isin(micros_sel)]

# --- VISUALIZAÇÃO DO MAPA ---
st.subheader("🌍 Mapa das Microrregiões Selecionadas")

if not df_sel.empty:
    fig = px.choropleth_map(
        df_sel,
        geojson=geojson_data,
        locations="Código da Microrregião",
        featureidkey="properties.CD_MICRO",
        color=indicador_sel_mapa,
        hover_name="Microrregião",
        center={"lat": -15, "lon": -53},
        zoom=1.5, # Ajustado para focar mais no Brasil
        color_continuous_scale="YlOrBr",
        height=500
    )

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

# --- RANKING DAS MICRORREGIÕES ---
st.subheader("🏆 Ranking das Microrregiões Selecionadas")

if not df_sel.empty:
    # Prepara as colunas para o DataFrame, incluindo UF e todos os indicadores IQM
    cols_to_display = ["Microrregião", "UF"] + TODOS_INDICADORES_IQM
    df_rank = df_sel[cols_to_display].copy()

    # Adiciona uma coluna de ranking começando do 1
    df_rank = df_rank.sort_values(by=indicador_sel_mapa, ascending=False).reset_index(drop=True)
    df_rank.index = df_rank.index + 1 # Ajusta o índice para começar de 1

    # Define o nome do índice (o "0" ou "1")
    df_rank.index.name = "Ranking"

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
            format="%.2f", # Formata para 2 casas decimais, ajuste se precisar
            text_align="center" # Centraliza o texto
        )

    # Exibe a tabela interativa com as configurações de coluna
    st.dataframe(df_rank, use_container_width=True, column_config=column_config)