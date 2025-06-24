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
# ATENÇÃO: O nome do GeoJSON foi atualizado para BR_Microrregioes_2022.1.json
GEOJSON_MICRORREGIOES_PATH = "data/BR_Microrregioes_2022.1.json"
EXCEL_IQM_PATH = "data/IQM_BRASIL_2025_V1.xlsm" # Ajuste se o nome da aba for diferente de "IQM_Ranking"

# --- FUNÇÕES PARA CARREGAMENTO DE DADOS (COM CACHE) ---

# st.cache_resource é usado para objetos que não mudam (como um dicionário GeoJSON grande)
# Ele armazena o recurso em cache, economizando tempo em execuções futuras.
@st.cache_resource(show_spinner="🔄 Carregando GeoJSON das Microrregiões...")
def load_geojson_local(path):
    """
    Carrega o arquivo GeoJSON das microrregiões de um caminho local.
    Inclui tratamento de erros para arquivo não encontrado ou JSON inválido.
    """
    if not os.path.exists(path):
        st.error(f"Erro: O arquivo GeoJSON não foi encontrado em '{path}'. "
                 "Verifique se ele foi adicionado corretamente ao repositório na pasta 'data'.")
        st.stop() # Interrompe a execução do Streamlit se o arquivo não estiver lá
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

# st.cache_data é usado para DataFrames ou outros dados que podem ser processados
# Ele armazena o DataFrame em cache.
@st.cache_data(show_spinner="🔄 Carregando Planilha IQM...")
def load_planilha_local(path):
    """
    Carrega a planilha IQM de um caminho local.
    Espera uma aba chamada "IQM_Ranking" por padrão.
    """
    if not os.path.exists(path):
        st.error(f"Erro: A planilha IQM não foi encontrada em '{path}'. "
                 "Verifique se ela foi adicionada corretamente ao repositório na pasta 'data'.")
        st.stop() # Interrompe a execução do Streamlit se o arquivo não estiver lá
    try:
        # Certifique-se que 'sheet_name' corresponde ao nome real da aba com os dados de ranking
        df_ranking = pd.read_excel(path, sheet_name="IQM_Ranking", engine='openpyxl')
        return df_ranking
    except FileNotFoundError: # Já coberto pelo os.path.exists, mas como fallback
        st.error(f"Erro: O arquivo da planilha não foi encontrado em '{path}'.")
        st.stop()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao carregar a planilha: {e}")
        st.stop()

# --- CARREGAR DADOS NA INICIALIZAÇÃO DO APP ---
geojson_data = load_geojson_local(GEOJSON_MICRORREGIOES_PATH)
df_ranking = load_planilha_local(EXCEL_IQM_PATH)

# --- ADICIONE ESTA LINHA PARA CONVERTER O CÓDIGO DA MICRORREGIÃO PARA STRING ---
df_ranking['Código da Microrregião'] = df_ranking['Código da Microrregião'].astype(str)

# --- VERIFICAÇÃO DE COLUNAS ESSENCIAIS NO DATAFRAME ---
# Se o nome das colunas no seu Excel for diferente, ajuste aqui!
required_cols = ["UF", "Microrregião", "Código da Microrregião"]
for col in required_cols:
    if col not in df_ranking.columns:
        st.error(f"Erro: Coluna '{col}' não encontrada na planilha. Por favor, verifique a planilha.")
        st.stop()

if df_ranking["UF"].empty:
    st.error("Coluna 'UF' está vazia na planilha. Não é possível filtrar por estado.")
    st.stop()

# --- INTERFACE (SIDEBAR) ---
st.sidebar.header("Filtros de Seleção")

# Filtro Estado (UF)
ufs = sorted(df_ranking["UF"].unique().tolist())
uf_sel = st.sidebar.selectbox("Selecione o Estado (UF):", ufs)

# Filtro Indicador
# Adapte esta lista para incluir APENAS os nomes EXATOS dos seus indicadores no Excel!
indicadores_disponiveis = [
    "IQM / 2025", "IQM-D", "IQM-C", "IQM-IU"
]
# Filtra para garantir que apenas indicadores existentes no DataFrame sejam mostrados
indicadores_disponiveis = [ind for ind in indicadores_disponiveis if ind in df_ranking.columns]

if not indicadores_disponiveis:
    st.sidebar.error("Nenhum indicador válido encontrado no DataFrame. Verifique os nomes das colunas na planilha e na lista de indicadores.")
    st.stop() # Interrompe se não houver indicadores para evitar erros

indicador_sel = st.sidebar.selectbox("Selecione o Indicador:", indicadores_disponiveis)

# Filtro Microrregião (Baseado no Estado Selecionado)
micros_por_uf = df_ranking[df_ranking["UF"] == uf_sel]["Microrregião"].unique().tolist()
micros_sel = st.sidebar.multiselect("Selecione Microrregiões para comparar:", sorted(micros_por_uf))

# --- LÓGICA DE FILTRAGEM DOS DADOS PARA O MAPA E RANKING ---
df_sel = df_ranking[df_ranking["UF"] == uf_sel].copy()

if micros_sel: # Se alguma microrregião foi selecionada
    df_sel = df_sel[df_sel["Microrregião"].isin(micros_sel)]

# --- VISUALIZAÇÃO DO MAPA ---
st.subheader("🌍 Mapa das Microrregiões Selecionadas")

if not df_sel.empty:
   
    # Ajuste o 'locations' para a coluna exata no seu DataFrame que contém o código da microrregião (ex: 29001)
    # E o 'featureidkey' para o caminho exato no GeoJSON (geralmente properties.CD_MICRO para IBGE)
    fig = px.choropleth_mapbox(
        df_sel,
        geojson=geojson_data,
        locations="Código da Microrregião", # <--- *** Coluna no seu DF com o ID da microrregião ***
        featureidkey="properties.CD_MICRO", # <--- *** Caminho para o ID no GeoJSON (CONFIRMADO) ***
        color=indicador_sel,
        hover_name="Microrregião",
        # --- AJUSTES DE ZOOM E CENTRO DO MAPA (UX) ---
        # Estes são valores FIXOS. Para zoom dinâmico, você precisaria calcular o centroide
        # e o zoom com base nas microrregiões selecionadas no df_sel.
        center={"lat": -15, "lon": -53}, # Exemplo: Centro do Brasil. Ajuste para um ponto inicial melhor.
        zoom=4, # Zoom inicial. 4.5 pode ser demais se for Brasil inteiro. Ajuste conforme necessário.
        # --- FIM AJUSTES DE ZOOM ---
        color_continuous_scale="YlOrBr", # Escala de cores (pode experimentar outras: Viridis, Plasma, etc.)
        height=500 # Altura do mapa em pixels
    )

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}) # Remove margens do layout do mapa
    st.plotly_chart(fig, use_container_width=True) # use_container_width=True faz o mapa ocupar a largura disponível
else:
    st.info("Selecione um Estado e/ou Microrregiões para visualizar no mapa.")

# --- RANKING DAS MICRORREGIÕES ---
st.subheader("🏆 Ranking das Microrregiões Selecionadas")

# --- AJUSTE DE TEXTO/FORMATACAO (UX) ---
# Se o problema das "letras" for a formatação dos cabeçalhos da tabela,
# geralmente o st.dataframe já tenta ser legível. Se ainda houver problemas,
# pode ser necessário inspecionar com as ferramentas de desenvolvedor do navegador
# ou usar formatação personalizada no Pandas antes de exibir o DataFrame.
# Por exemplo: df_rank.rename(columns={'col_antiga': 'Col. Nova Legível'})
# Ou até usar st.markdown para criar os próprios cabeçalhos se a tabela for pequena.
# --- FIM AJUSTE DE TEXTO ---

if not df_sel.empty:
    df_rank = df_sel[["Microrregião", indicador_sel]].copy()
    df_rank = df_rank.sort_values(by=indicador_sel, ascending=False).reset_index(drop=True)

    # Exibe a tabela interativa
    st.dataframe(df_rank, use_container_width=True)
else:
    st.info("Selecione um Estado e/ou Microrregiões para ver o ranking.")

