import streamlit as st
import pandas as pd
import requests # Mantido por precaução, caso use para outras APIs no futuro
import json
import plotly.express as px
import io
import os # Para verificar se os arquivos locais existem

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="IQM 2025 - Comparador de Microrregiões",
    page_icon="📍",
    layout="wide", # Usa a largura total da página
    initial_sidebar_state="expanded" # Deixa a sidebar aberta por padrão
)

# --- TÍTULO DO APLICATIVO ---
st.markdown("<h1 style='font-size: 40px;'>📍 Comparador de Microrregiões - IQM 2025</h1>", unsafe_allow_html=True)

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
# Adicione ou remova indicadores aqui conforme as colunas da sua planilha.
TODOS_INDICADORES_IQM = [
    "IQM / 2025", "IQM-D", "IQM-C", "IQM-IU", # Adicione mais se tiver
]
# Garante que só indicadores que existem no DF sejam usados
TODOS_INDICADORES_IQM = [ind for ind in TODOS_INDICADORES_IQM if ind in df_ranking.columns]


# --- INTERFACE (SIDEBAR) ---
st.sidebar.header("Filtros de Seleção")

# Filtro Estados (UF) - AGORA MULTISELECT
ufs = sorted(df_ranking["UF"].unique().tolist())
# Adicionado valor padrão para garantir que sempre haja um estado selecionado ao iniciar
# ou se o usuário desmarcar todos.
ufs_sel = st.sidebar.multiselect("Selecione os Estados (UF):", ufs, default=ufs[0] if ufs else [])

if not ufs_sel:
    st.sidebar.warning("Por favor, selecione pelo menos um Estado.")
    st.stop()

# Filtro Indicador para COLORIR O MAPA (ainda um selectbox simples)
# Este é o indicador que irá determinar a cor no mapa.
indicadores_disponiveis_mapa = [ind for ind in TODOS_INDICADORES_IQM] # Usa a lista completa de IQMs
indicador_sel_mapa = st.sidebar.selectbox("Selecione o Indicador para colorir o Mapa:", indicadores_disponiveis_mapa)


# Filtro Microrregião (Baseado nos Estados Selecionados)
# Filtra o DataFrame para obter apenas as microrregiões dos estados selecionados
df_micros_estados_sel = df_ranking[df_ranking["UF"].isin(ufs_sel)]
micros_por_estados_sel = sorted(df_micros_estados_sel["Microrregião"].unique().tolist())

micros_sel = st.sidebar.multiselect("Selecione Microrregiões para comparar:", micros_por_estados_sel)

# --- LÓGICA DE FILTRAGEM DOS DADOS PARA O MAPA E RANKING ---
# df_sel agora é filtrado pelos MÚLTIPLOS estados selecionados
df_sel = df_ranking[df_ranking["UF"].isin(ufs_sel)].copy()

if micros_sel: # Se alguma microrregião foi selecionada, filtra ainda mais
    df_sel = df_sel[df_sel["Microrregião"].isin(micros_sel)]

# --- VISUALIZAÇÃO DO MAPA ---
st.subheader("🌍 Mapa das Microrregiões Selecionadas")

if not df_sel.empty:
    fig = px.choropleth_map( # Mantido px.choropleth_map
        df_sel,
        geojson=geojson_data,
        locations="Código da Microrregião", # Coluna no seu DF com o ID da microrregião
        featureidkey="properties.CD_MICRO", # Caminho para o ID no GeoJSON (AGORA CORRETO!)
        color=indicador_sel_mapa, # Usa o indicador selecionado para o mapa
        hover_name="Microrregião",
        # --- AJUSTES DE ZOOM E CENTRO DO MAPA PARA O BRASIL ---
        center={"lat": -15, "lon": -53}, # Centro do Brasil
        zoom=2, # Zoom para abranger o Brasil
        color_continuous_scale="YlOrBr", # Escala de cores
        height=500 # Altura do mapa em pixels
    )

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}) # Remove margens do layout do mapa
    st.plotly_chart(fig, use_container_width=True) # use_container_width=True faz o mapa ocupar a largura disponível
# else:
#     st.info("Selecione um Estado e/ou Microrregiões para visualizar no mapa.") # Removido conforme solicitado

# --- RANKING DAS MICRORREGIÕES ---
# st.subheader("🏆 Ranking das Microrregiões Selecionadas")

if not df_sel.empty:
    # Mostra Microrregião, UF e TODOS os indicadores IQM
    df_rank = df_sel[["Microrregião", "UF"] + TODOS_INDICADORES_IQM].copy()
    # Ordena pelo indicador selecionado no mapa para coerência
    df_rank = df_rank.sort_values(by=indicador_sel_mapa, ascending=False).reset_index(drop=True)

    st.dataframe(df_rank, use_container_width=True)
# else:
#     st.info("Selecione um Estado e/ou Microrregiões para ver o ranking.") # Removido conforme solicitado
