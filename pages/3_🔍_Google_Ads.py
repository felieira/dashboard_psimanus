import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

st.set_page_config(
    page_title="Dashboard PSI - Google Ads",
    page_icon="📊",
    layout="wide"
)

# Adicionar CSS customizado
st.markdown("""
    <style>
    /* Estilo geral */
    .stApp {
        background-color: #FFFFFF;
    }
    
    /* Container das pills */
    [role="tablist"] {
        background-color: #f0f2f6 !important;
        padding: 10px;
        border-radius: 20px;
        margin-bottom: 20px;
        border: none !important;
    }
    
    /* Pills */
    [role="tab"] {
        background-color: #FFFFFF !important;
        color: #6d7174 !important;
        border: 1px solid rgba(49, 51, 63, 0.2) !important;
        border-radius: 20px !important;
        padding: 8px 16px !important;
        margin: 0 5px !important;
        font-size: 14px !important;
        transition: all 0.2s ease !important;
    }
    
    /* Pill selecionada */
    [role="tab"][aria-selected="true"] {
        background-color: #4285F4 !important;
        color: white !important;
        border-color: #4285F4 !important;
    }
    
    /* Hover da pill */
    [role="tab"]:hover {
        background-color: #f0f2f6 !important;
        border-color: #4285F4 !important;
    }
    
    /* Métricas */
    [data-testid="metric-container"] {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(49, 51, 63, 0.1);
    }
    
    /* Cabeçalho da conta */
    .account-header {
        background-color: #4285F4;
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# Função para obter credenciais
def get_credentials():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Tentar várias abordagens para obter credenciais
    creds = None
    error_messages = []
    
    # 1. Tentar usar os segredos do Streamlit
    try:
        if "gcp_service_account" in st.secrets:
            service_account_info = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
            st.sidebar.success("Usando credenciais dos segredos do Streamlit")
        else:
            error_messages.append("Segredos do Streamlit não contêm 'gcp_service_account'")
    except Exception as e:
        error_messages.append(f"Erro ao acessar segredos do Streamlit: {str(e)}")
    
    # 2. Tentar usar arquivo de credenciais local
    if creds is None:
        creds_path = './credenciais.json'
        if os.path.exists(creds_path):
            try:
                creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
                st.sidebar.success("Usando arquivo de credenciais local")
            except Exception as e:
                error_messages.append(f"Erro ao usar arquivo de credenciais local: {str(e)}")
        else:
            error_messages.append(f"Arquivo de credenciais não encontrado em: {creds_path}")
    
    # Se nenhuma credencial foi obtida, mostrar erro e retornar None
    if creds is None:
        st.error("Não foi possível obter credenciais para acessar o Google Sheets")
        st.error("\n".join(error_messages))
        st.info("Configure os segredos no Streamlit Cloud ou forneça o arquivo credenciais.json")
        return None
        
    return creds

# Função para carregar dados do Google Ads
def load_google_ads_data(client):
    try:
        # Verificar se a planilha de Google Ads existe
        try:
            sheet = client.open("[PAX] GOOGLE ADS")
            st.sidebar.success(f"Conectado à planilha: {sheet.title}")
        except Exception as e:
            st.error(f"Erro ao acessar a planilha de Google Ads: {str(e)}")
            st.info("Verifique se a planilha '[PAX] GOOGLE ADS' existe e se as credenciais têm acesso a ela")
            return None, None
        
        # Carregar dados de campanhas
        try:
            sheet_campaigns = sheet.worksheet('campanhas')
            data_campaigns = pd.DataFrame(sheet_campaigns.get_all_records())
        except Exception as e:
            st.error(f"Erro ao carregar dados de campanhas: {str(e)}")
            data_campaigns = None
        
        # Carregar dados de métricas
        try:
            sheet_metrics = sheet.worksheet('metricas')
            data_metrics = pd.DataFrame(sheet_metrics.get_all_records())
        except Exception as e:
            st.error(f"Erro ao carregar dados de métricas: {str(e)}")
            data_metrics = None
        
        return data_campaigns, data_metrics
    
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Ads: {str(e)}")
        return None, None

# Função para processar dados do Google Ads
def process_google_ads_data(data_campaigns, data_metrics):
    if data_campaigns is None or data_metrics is None:
        return None
    
    try:
        # Converter datas
        data_metrics['data'] = pd.to_datetime(data_metrics['data'], errors='coerce')
        
        # Converter métricas numéricas
        numeric_columns = ['impressoes', 'cliques', 'conversoes', 'custo', 'valor_conversao']
        for col in numeric_columns:
            if col in data_metrics.columns:
                data_metrics[col] = pd.to_numeric(data_metrics[col], errors='coerce')
        
        # Calcular métricas derivadas
        data_metrics['ctr'] = (data_metrics['cliques'] / data_metrics['impressoes'] * 100).round(2)
        data_metrics['cpc'] = (data_metrics['custo'] / data_metrics['cliques']).round(2)
        data_metrics['cpa'] = (data_metrics['custo'] / data_metrics['conversoes']).round(2)
        data_metrics['roas'] = (data_metrics['valor_conversao'] / data_metrics['custo']).round(2)
        
        # Mesclar dados de campanhas e métricas
        data_merged = pd.merge(
            data_metrics, 
            data_campaigns, 
            left_on='id_campanha', 
            right_on='id_campanha', 
            how='left'
        )
        
        return data_merged
    
    except Exception as e:
        st.error(f"Erro ao processar dados do Google Ads: {str(e)}")
        return None

# Função para criar visualizações
def create_visualizations(data, account_id=None):
    if data is None:
        return
    
    # Filtrar por conta se especificado
    if account_id:
        data = data[data['id_conta'] == account_id]
    
    # Verificar se há dados após filtragem
    if len(data) == 0:
        st.warning(f"Não há dados disponíveis para a conta selecionada: {account_id}")
        return
    
    # Agrupar dados por data para métricas gerais
    daily_metrics = data.groupby('data').agg({
        'impressoes': 'sum',
        'cliques': 'sum',
        'conversoes': 'sum',
        'custo': 'sum',
        'valor_conversao': 'sum'
    }).reset_index()
    
    # Calcular métricas derivadas
    daily_metrics['ctr'] = (daily_metrics['cliques'] / daily_metrics['impressoes'] * 100).round(2)
    daily_metrics['cpc'] = (daily_metrics['custo'] / daily_metrics['cliques']).round(2)
    daily_metrics['cpa'] = (daily_metrics['custo'] / daily_metrics['conversoes']).round(2)
    daily_metrics['roas'] = (daily_metrics['valor_conversao'] / daily_metrics['custo']).round(2)
    
    # Calcular totais para métricas principais
    total_impressions = daily_metrics['impressoes'].sum()
    total_clicks = daily_metrics['cliques'].sum()
    total_conversions = daily_metrics['conversoes'].sum()
    total_cost = daily_metrics['custo'].sum()
    total_conversion_value = daily_metrics['valor_conversao'].sum()
    
    # Calcular médias para métricas derivadas
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    avg_cpc = (total_cost / total_clicks) if total_clicks > 0 else 0
    avg_cpa = (total_cost / total_conversions) if total_conversions > 0 else 0
    avg_roas = (total_conversion_value / total_cost) if total_cost > 0 else 0
    
    # Exibir métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Impressões", f"{total_impressions:,.0f}")
        st.metric("CTR", f"{avg_ctr:.2f}%")
    
    with col2:
        st.metric("Cliques", f"{total_clicks:,.0f}")
        st.metric("CPC Médio", f"R$ {avg_cpc:.2f}")
    
    with col3:
        st.metric("Conversões", f"{total_conversions:,.0f}")
        st.metric("CPA Médio", f"R$ {avg_cpa:.2f}")
    
    with col4:
        st.metric("Custo Total", f"R$ {total_cost:,.2f}")
        st.metric("ROAS", f"{avg_roas:.2f}x")
    
    # Gráfico de tendência de métricas ao longo do tempo
    st.subheader("Tendência de Métricas ao Longo do Tempo")
    
    # Opções de métricas para visualização
    metric_options = {
        "Impressões": "impressoes",
        "Cliques": "cliques",
        "Conversões": "conversoes",
        "Custo": "custo",
        "CTR (%)": "ctr",
        "CPC (R$)": "cpc",
        "CPA (R$)": "cpa",
        "ROAS": "roas"
    }
    
    # Seletor de métricas
    selected_metrics = st.multiselect(
        "Selecione as métricas para visualizar",
        options=list(metric_options.keys()),
        default=["Impressões", "Cliques", "Conversões"]
    )
    
    if selected_metrics:
        # Criar figura
        fig = go.Figure()
        
        for metric_name in selected_metrics:
            metric_col = metric_options[metric_name]
            
            # Adicionar linha para cada métrica selecionada
            fig.add_trace(go.Scatter(
                x=daily_metrics['data'],
                y=daily_metrics[metric_col],
                mode='lines+markers',
                name=metric_name
            ))
        
        # Configurar layout
        fig.update_layout(
            title="Tendência de Métricas Diárias",
            xaxis_title="Data",
            yaxis_title="Valor",
            legend_title="Métricas",
            template="plotly_white",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Análise por tipo de rede
    if 'rede' in data.columns:
        st.subheader("Desempenho por Rede")
        
        # Agrupar dados por rede
        network_metrics = data.groupby('rede').agg({
            'impressoes': 'sum',
            'cliques': 'sum',
            'conversoes': 'sum',
            'custo': 'sum',
            'valor_conversao': 'sum'
        }).reset_index()
        
        # Calcular métricas derivadas
        network_metrics['ctr'] = (network_metrics['cliques'] / network_metrics['impressoes'] * 100).round(2)
        network_metrics['cpc'] = (network_metrics['custo'] / network_metrics['cliques']).round(2)
        network_metrics['cpa'] = (network_metrics['custo'] / network_metrics['conversoes']).round(2)
        network_metrics['roas'] = (network_metrics['valor_conversao'] / network_metrics['custo']).round(2)
        
        # Seletor de métrica para comparação
        network_metric = st.selectbox(
            "Selecione a métrica para comparar redes",
            options=["Impressões", "Cliques", "Conversões", "Custo", "CTR (%)", "CPC (R$)", "CPA (R$)", "ROAS"],
            index=2
        )
        
        # Mapear seleção para coluna
        metric_mapping = {
            "Impressões": "impressoes",
            "Cliques": "cliques",
            "Conversões": "conversoes",
            "Custo": "custo",
            "CTR (%)": "ctr",
            "CPC (R$)": "cpc",
            "CPA (R$)": "cpa",
            "ROAS": "roas"
        }
        
        selected_col = metric_mapping[network_metric]
        
        # Criar gráfico de pizza
        fig = px.pie(
            network_metrics,
            values=selected_col,
            names='rede',
            title=f"{network_metric} por Rede",
            hole=0.4
        )
        
        # Ajustar layout
        fig.update_layout(
            legend_title="Rede",
            template="plotly_white"
        )
        
        # Exibir gráfico
        st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de desempenho por campanha
    st.subheader("Desempenho por Campanha")
    
    # Agrupar dados por campanha
    campaign_metrics = data.groupby(['nome_campanha', 'objetivo']).agg({
        'impressoes': 'sum',
        'cliques': 'sum',
        'conversoes': 'sum',
        'custo': 'sum',
        'valor_conversao': 'sum'
    }).reset_index()
    
    # Calcular métricas derivadas
    campaign_metrics['ctr'] = (campaign_metrics['cliques'] / campaign_metrics['impressoes'] * 100).round(2)
    campaign_metrics['cpc'] = (campaign_metrics['custo'] / campaign_metrics['cliques']).round(2)
    campaign_metrics['cpa'] = (campaign_metrics['custo'] / campaign_metrics['conversoes']).round(2)
    campaign_metrics['roas'] = (campaign_metrics['valor_conversao'] / campaign_metrics['custo']).round(2)
    
    # Seletor de métrica para comparação
    campaign_metric = st.selectbox(
        "Selecione a métrica para comparar campanhas",
        options=["Impressões", "Cliques", "Conversões", "Custo", "CTR (%)", "CPC (R$)", "CPA (R$)", "ROAS"],
        index=2
    )
    
    # Mapear seleção para coluna
    selected_col = metric_mapping[campaign_metric]
    
    # Ordenar campanhas pela métrica selecionada
    campaign_metrics = campaign_metrics.sort_values(by=selected_col, ascending=False)
    
    # Criar gráfico de barras
    fig = px.bar(
        campaign_metrics,
        x='nome_campanha',
        y=selected_col,
        color='objetivo',
        title=f"{campaign_metric} por Campanha",
        labels={'nome_campanha': 'Campanha', selected_col: campaign_metric},
        height=500
    )
    
    # Ajustar layout
    fig.update_layout(
        xaxis_title="Campanha",
        yaxis_title=campaign_metric,
        legend_title="Objetivo",
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Análise de palavras-chave (se disponível)
    if 'keywords' in data.columns or any('keyword' in col.lower() for col in data.columns):
        st.subheader("Análise de Palavras-chave")
        
        # Identificar a coluna de palavras-chave
        keyword_col = next((col for col in data.columns if 'keyword' in col.lower()), None)
        
        if keyword_col:
            # Agrupar dados por palavra-chave
            keyword_metrics = data.groupby(keyword_col).agg({
                'impressoes': 'sum',
                'cliques': 'sum',
                'conversoes': 'sum',
                'custo': 'sum',
                'valor_conversao': 'sum'
            }).reset_index()
            
            # Calcular métricas derivadas
            keyword_metrics['ctr'] = (keyword_metrics['cliques'] / keyword_metrics['impressoes'] * 100).round(2)
            keyword_metrics['cpc'] = (keyword_metrics['custo'] / keyword_metrics['cliques']).round(2)
            keyword_metrics['cpa'] = (keyword_metrics['custo'] / keyword_metrics['conversoes']).round(2)
            keyword_metrics['roas'] = (keyword_metrics['valor_conversao'] / keyword_metrics['custo']).round(2)
            
            # Ordenar por conversões (padrão)
            keyword_metrics = keyword_metrics.sort_values(by='conversoes', ascending=False)
            
            # Limitar às 20 principais palavras-chave
            top_keywords = keyword_metrics.head(20)
            
            # Exibir tabela
            st.dataframe(top_keywords.style.format({
                'impressoes': '{:,.0f}',
                'cliques': '{:,.0f}',
                'conversoes': '{:,.0f}',
                'custo': 'R$ {:.2f}',
                'valor_conversao': 'R$ {:.2f}',
                'ctr': '{:.2f}%',
                'cpc': 'R$ {:.2f}',
                'cpa': 'R$ {:.2f}',
                'roas': '{:.2f}x'
            }))
    
    # Tabela detalhada de campanhas
    st.subheader("Detalhes das Campanhas")
    
    # Formatar tabela
    formatted_campaign_metrics = campaign_metrics.copy()
    formatted_campaign_metrics['impressoes'] = formatted_campaign_metrics['impressoes'].apply(lambda x: f"{x:,.0f}")
    formatted_campaign_metrics['cliques'] = formatted_campaign_metrics['cliques'].apply(lambda x: f"{x:,.0f}")
    formatted_campaign_metrics['conversoes'] = formatted_campaign_metrics['conversoes'].apply(lambda x: f"{x:,.0f}")
    formatted_campaign_metrics['custo'] = formatted_campaign_metrics['custo'].apply(lambda x: f"R$ {x:,.2f}")
    formatted_campaign_metrics['valor_conversao'] = formatted_campaign_metrics['valor_conversao'].apply(lambda x: f"R$ {x:,.2f}")
    formatted_campaign_metrics['ctr'] = formatted_campaign_metrics['ctr'].apply(lambda x: f"{x:.2f}%")
    formatted_campaign_metrics['cpc'] = formatted_campaign_metrics['cpc'].apply(lambda x: f"R$ {x:.2f}")
    formatted_campaign_metrics['cpa'] = formatted_campaign_metrics['cpa'].apply(lambda x: f"R$ {x:.2f}")
    formatted_campaign_metrics['roas'] = formatted_campaign_metrics['roas'].apply(lambda x: f"{x:.2f}x")
    
    # Renomear colunas para exibição
    formatted_campaign_metrics = formatted_campaign_metrics.rename(columns={
        'nome_campanha': 'Campanha',
        'objetivo': 'Objetivo',
        'impressoes': 'Impressões',
        'cliques': 'Cliques',
        'conversoes': 'Conversões',
        'custo': 'Custo',
        'valor_conversao': 'Valor de Conversão',
        'ctr': 'CTR',
        'cpc': 'CPC',
        'cpa': 'CPA',
        'roas': 'ROAS'
    })
    
    st.dataframe(formatted_campaign_metrics, use_container_width=True)

def main():
    st.title("📊 Dashboard PSI - Google Ads")
    
    # Obter credenciais
    creds = get_credentials()
    if creds is None:
        return
    
    # Conectar ao Google Sheets
    client = gspread.authorize(creds)
    
    # Carregar dados do Google Ads
    data_campaigns, data_metrics = load_google_ads_data(client)
    
    # Processar dados
    data_processed = process_google_ads_data(data_campaigns, data_metrics)
    
    if data_processed is None:
        st.warning("Não foi possível processar os dados do Google Ads. Verifique se as planilhas estão configuradas corretamente.")
        
        # Mostrar exemplo de estrutura esperada
        st.subheader("Estrutura esperada das planilhas")
        
        st.write("Planilha: [PAX] GOOGLE ADS")
        
        st.write("Aba 'campanhas':")
        example_campaigns = pd.DataFrame({
            'id_campanha': ['123456789', '987654321'],
            'id_conta': ['111111', '111111'],
            'nome_conta': ['Conta Principal', 'Conta Principal'],
            'nome_campanha': ['Campanha Pesquisa', 'Campanha Display'],
            'objetivo': ['Geração de Leads', 'Conversão'],
            'status': ['ATIVO', 'ATIVO'],
            'rede': ['Pesquisa', 'Display'],
            'categoria': ['PAX', 'FRANQUIAS']
        })
        st.dataframe(example_campaigns)
        
        st.write("Aba 'metricas':")
        example_metrics = pd.DataFrame({
            'id_campanha': ['123456789', '123456789', '987654321', '987654321'],
            'data': ['2025-04-01', '2025-04-02', '2025-04-01', '2025-04-02'],
            'impressoes': [1000, 1200, 800, 900],
            'cliques': [50, 60, 40, 45],
            'conversoes': [5, 6, 4, 5],
            'custo': [100.00, 120.00, 80.00, 90.00],
            'valor_conversao': [200.00, 240.00, 160.00, 180.00]
        })
        st.dataframe(example_metrics)
        
        return
    
    # Verificar se há múltiplas contas
    if 'id_conta' in data_processed.columns:
        unique_accounts = data_processed[['id_conta', 'nome_conta']].drop_duplicates()
        
        if len(unique_accounts) > 1:
            # Adicionar opção para visualizar todas as contas
            all_accounts_option = pd.DataFrame({
                'id_conta': ['all'],
                'nome_conta': ['Todas as Contas']
            })
            unique_accounts = pd.concat([all_accounts_option, unique_accounts])
            
            # Seletor de conta
            selected_account = st.sidebar.selectbox(
                "Selecione a Conta",
                options=unique_accounts['id_conta'].tolist(),
                format_func=lambda x: unique_accounts.loc[unique_accounts['id_conta'] == x, 'nome_conta'].iloc[0],
                index=0
            )
            
            if selected_account == 'all':
                # Mostrar dados de todas as contas
                st.header("Visão Geral - Todas as Contas")
                create_visualizations(data_processed)
                
                # Mostrar métricas por conta
                st.header("Métricas por Conta")
                
                # Agrupar dados por conta
                account_metrics = data_processed.groupby(['id_conta', 'nome_conta']).agg({
                    'impressoes': 'sum',
                    'cliques': 'sum',
                    'conversoes': 'sum',
                    'custo': 'sum',
                    'valor_conversao': 'sum'
                }).reset_index()
                
                # Calcular métricas derivadas
                account_metrics['ctr'] = (account_metrics['cliques'] / account_metrics['impressoes'] * 100).round(2)
                account_metrics['cpc'] = (account_metrics['custo'] / account_metrics['cliques']).round(2)
                account_metrics['cpa'] = (account_metrics['custo'] / account_metrics['conversoes']).round(2)
                account_metrics['roas'] = (account_metrics['valor_conversao'] / account_metrics['custo']).round(2)
                
                # Exibir métricas por conta
                for _, account in account_metrics.iterrows():
                    st.markdown(f"""
                    <div class="account-header">
                        <h3>{account['nome_conta']} (ID: {account['id_conta']})</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Impressões", f"{account['impressoes']:,.0f}")
                        st.metric("CTR", f"{account['ctr']:.2f}%")
                    
                    with col2:
                        st.metric("Cliques", f"{account['cliques']:,.0f}")
                        st.metric("CPC Médio", f"R$ {account['cpc']:.2f}")
                    
                    with col3:
                        st.metric("Conversões", f"{account['conversoes']:,.0f}")
                        st.metric("CPA Médio", f"R$ {account['cpa']:.2f}")
                    
                    with col4:
                        st.metric("Custo Total", f"R$ {account['custo']:,.2f}")
                        st.metric("ROAS", f"{account['roas']:.2f}x")
            else:
                # Mostrar dados da conta selecionada
                account_name = unique_accounts.loc[unique_accounts['id_conta'] == selected_account, 'nome_conta'].iloc[0]
                st.header(f"Conta: {account_name}")
                create_visualizations(data_processed, selected_account)
        else:
            # Apenas uma conta, mostrar dados diretamente
            create_visualizations(data_processed)
    else:
        # Não há informação de conta, mostrar dados diretamente
        create_visualizations(data_processed)

if __name__ == "__main__":
    main()
