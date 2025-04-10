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
    page_title="Dashboard PSI - Objetivos de Campanha",
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
        background-color: #3366CC !important;
        color: white !important;
        border-color: #3366CC !important;
    }
    
    /* Hover da pill */
    [role="tab"]:hover {
        background-color: #f0f2f6 !important;
        border-color: #3366CC !important;
    }
    
    /* Métricas */
    [data-testid="metric-container"] {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(49, 51, 63, 0.1);
    }
    
    /* Cabeçalho da categoria */
    .category-header {
        background-color: #3366CC;
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    
    /* Estilos para os cards de campanha */
    .campaign-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: white;
    }
    
    /* Estilos para os status */
    .status-active {
        background-color: #4CAF50;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }
    
    .status-paused {
        background-color: #FFC107;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }
    
    .status-ended {
        background-color: #9E9E9E;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }
    
    .status-planned {
        background-color: #2196F3;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }
    
    /* Estilos para os objetivos */
    .objective-pax {
        background-color: #E91E63;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }
    
    .objective-franquias {
        background-color: #9C27B0;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }
    
    .objective-hub {
        background-color: #FF9800;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }
    
    .objective-pnp {
        background-color: #00BCD4;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
    }
    
    .objective-publico {
        background-color: #8BC34A;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-block;
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

# Função para carregar dados de objetivos de campanha
def load_campaign_objectives(client):
    try:
        # Verificar se a planilha de objetivos de campanha existe
        try:
            sheet = client.open("[PAX] OBJETIVOS CAMPANHA")
            st.sidebar.success(f"Conectado à planilha: {sheet.title}")
        except Exception as e:
            st.error(f"Erro ao acessar a planilha de objetivos de campanha: {str(e)}")
            st.info("Verifique se a planilha '[PAX] OBJETIVOS CAMPANHA' existe e se as credenciais têm acesso a ela")
            return None
        
        # Carregar dados de campanhas
        try:
            sheet_campaigns = sheet.worksheet('campanhas')
            data_campaigns = pd.DataFrame(sheet_campaigns.get_all_records())
        except Exception as e:
            st.error(f"Erro ao carregar dados de campanhas: {str(e)}")
            data_campaigns = None
        
        return data_campaigns
    
    except Exception as e:
        st.error(f"Erro ao carregar dados de objetivos de campanha: {str(e)}")
        return None

# Função para processar dados de objetivos de campanha
def process_campaign_data(data_campaigns):
    if data_campaigns is None or data_campaigns.empty:
        return None
    
    try:
        # Converter datas
        date_columns = ['data_inicio', 'data_fim', 'data_atualizacao']
        for col in date_columns:
            if col in data_campaigns.columns:
                data_campaigns[col] = pd.to_datetime(data_campaigns[col], errors='coerce')
        
        # Converter métricas numéricas
        numeric_columns = ['orcamento', 'gasto_atual', 'conversoes_meta', 'conversoes_atual']
        for col in numeric_columns:
            if col in data_campaigns.columns:
                data_campaigns[col] = pd.to_numeric(data_campaigns[col], errors='coerce')
        
        # Calcular métricas derivadas
        if all(col in data_campaigns.columns for col in ['gasto_atual', 'orcamento']):
            data_campaigns['percentual_orcamento'] = (data_campaigns['gasto_atual'] / data_campaigns['orcamento'] * 100).round(2)
        
        if all(col in data_campaigns.columns for col in ['conversoes_atual', 'conversoes_meta']):
            data_campaigns['percentual_meta'] = (data_campaigns['conversoes_atual'] / data_campaigns['conversoes_meta'] * 100).round(2)
        
        # Determinar status atual baseado nas datas
        if all(col in data_campaigns.columns for col in ['data_inicio', 'data_fim', 'status']):
            today = pd.Timestamp.now().date()
            
            # Atualizar status baseado nas datas
            for idx, row in data_campaigns.iterrows():
                if pd.isna(row['data_inicio']) or pd.isna(row['data_fim']):
                    continue
                
                start_date = row['data_inicio'].date()
                end_date = row['data_fim'].date()
                
                if row['status'] != 'PAUSADA':  # Não alterar status de campanhas pausadas manualmente
                    if today < start_date:
                        data_campaigns.at[idx, 'status'] = 'PLANEJADA'
                    elif today > end_date:
                        data_campaigns.at[idx, 'status'] = 'ENCERRADA'
                    else:
                        data_campaigns.at[idx, 'status'] = 'ATIVA'
        
        return data_campaigns
    
    except Exception as e:
        st.error(f"Erro ao processar dados de objetivos de campanha: {str(e)}")
        return None

# Função para criar visualizações de objetivos de campanha
def create_campaign_objectives_visualizations(data_campaigns, platform=None, objective=None):
    if data_campaigns is None or data_campaigns.empty:
        st.warning("Não há dados de objetivos de campanha disponíveis.")
        return
    
    # Filtrar por plataforma se especificado
    if platform and platform != "Todas":
        data_campaigns = data_campaigns[data_campaigns['plataforma'] == platform]
    
    # Filtrar por objetivo se especificado
    if objective and objective != "Todos":
        data_campaigns = data_campaigns[data_campaigns['objetivo'] == objective]
    
    # Verificar se há dados após filtragem
    if len(data_campaigns) == 0:
        st.warning(f"Não há dados de campanhas disponíveis para os filtros selecionados.")
        return
    
    # Resumo de campanhas por status
    st.subheader("Resumo de Campanhas por Status")
    
    # Contar campanhas por status
    status_counts = data_campaigns['status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Quantidade']
    
    # Criar gráfico de pizza
    fig = px.pie(
        status_counts,
        values='Quantidade',
        names='Status',
        title="Distribuição de Campanhas por Status",
        color='Status',
        color_discrete_map={
            'ATIVA': '#4CAF50',
            'PAUSADA': '#FFC107',
            'ENCERRADA': '#9E9E9E',
            'PLANEJADA': '#2196F3'
        }
    )
    
    fig.update_layout(
        legend_title="Status",
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Resumo de campanhas por objetivo
    st.subheader("Resumo de Campanhas por Objetivo")
    
    # Contar campanhas por objetivo
    objective_counts = data_campaigns['objetivo'].value_counts().reset_index()
    objective_counts.columns = ['Objetivo', 'Quantidade']
    
    # Criar gráfico de barras
    fig = px.bar(
        objective_counts,
        x='Objetivo',
        y='Quantidade',
        title="Distribuição de Campanhas por Objetivo",
        color='Objetivo',
        color_discrete_map={
            'PAX': '#E91E63',
            'FRANQUIAS': '#9C27B0',
            'HUB': '#FF9800',
            'PNP': '#00BCD4',
            '+PÚBLICO': '#8BC34A'
        }
    )
    
    fig.update_layout(
        xaxis_title="Objetivo",
        yaxis_title="Quantidade de Campanhas",
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Resumo de orçamento e gastos
    if all(col in data_campaigns.columns for col in ['orcamento', 'gasto_atual']):
        st.subheader("Resumo de Orçamento e Gastos")
        
        # Calcular totais
        total_budget = data_campaigns['orcamento'].sum()
        total_spent = data_campaigns['gasto_atual'].sum()
        budget_percentage = (total_spent / total_budget * 100) if total_budget > 0 else 0
        
        # Exibir métricas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Orçamento Total", f"R$ {total_budget:,.2f}")
        
        with col2:
            st.metric("Gasto Total", f"R$ {total_spent:,.2f}")
        
        with col3:
            st.metric("% do Orçamento Utilizado", f"{budget_percentage:.2f}%")
        
        # Agrupar por objetivo
        objective_budget = data_campaigns.groupby('objetivo').agg({
            'orcamento': 'sum',
            'gasto_atual': 'sum'
        }).reset_index()
        
        # Calcular percentual
        objective_budget['percentual'] = (objective_budget['gasto_atual'] / objective_budget['orcamento'] * 100).round(2)
        
        # Criar gráfico de barras empilhadas
        fig = go.Figure()
        
        # Adicionar barras de orçamento
        fig.add_trace(go.Bar(
            x=objective_budget['objetivo'],
            y=objective_budget['orcamento'],
            name='Orçamento',
            marker_color='#3366CC'
        ))
        
        # Adicionar barras de gasto
        fig.add_trace(go.Bar(
            x=objective_budget['objetivo'],
            y=objective_budget['gasto_atual'],
            name='Gasto Atual',
            marker_color='#FF9900'
        ))
        
        # Configurar layout
        fig.update_layout(
            title="Orçamento vs. Gasto por Objetivo",
            xaxis_title="Objetivo",
            yaxis_title="Valor (R$)",
            barmode='group',
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Resumo de conversões
    if all(col in data_campaigns.columns for col in ['conversoes_meta', 'conversoes_atual']):
        st.subheader("Resumo de Conversões")
        
        # Calcular totais
        total_target = data_campaigns['conversoes_meta'].sum()
        total_conversions = data_campaigns['conversoes_atual'].sum()
        conversion_percentage = (total_conversions / total_target * 100) if total_target > 0 else 0
        
        # Exibir métricas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Meta Total", f"{total_target:,.0f}")
        
        with col2:
            st.metric("Conversões Atuais", f"{total_conversions:,.0f}")
        
        with col3:
            st.metric("% da Meta Atingida", f"{conversion_percentage:.2f}%")
        
        # Agrupar por objetivo
        objective_conversions = data_campaigns.groupby('objetivo').agg({
            'conversoes_meta': 'sum',
            'conversoes_atual': 'sum'
        }).reset_index()
        
        # Calcular percentual
        objective_conversions['percentual'] = (objective_conversions['conversoes_atual'] / objective_conversions['conversoes_meta'] * 100).round(2)
        
        # Criar gráfico de barras empilhadas
        fig = go.Figure()
        
        # Adicionar barras de meta
        fig.add_trace(go.Bar(
            x=objective_conversions['objetivo'],
            y=objective_conversions['conversoes_meta'],
            name='Meta',
            marker_color='#3366CC'
        ))
        
        # Adicionar barras de conversões atuais
        fig.add_trace(go.Bar(
            x=objective_conversions['objetivo'],
            y=objective_conversions['conversoes_atual'],
            name='Conversões Atuais',
            marker_color='#FF9900'
        ))
        
        # Configurar layout
        fig.update_layout(
            title="Meta vs. Conversões Atuais por Objetivo",
            xaxis_title="Objetivo",
            yaxis_title="Conversões",
            barmode='group',
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Detalhes das campanhas por objetivo
    st.subheader("Detalhes das Campanhas por Objetivo")
    
    # Agrupar campanhas por objetivo
    objectives = data_campaigns['objetivo'].unique()
    
    for objective in objectives:
        # Filtrar campanhas pelo objetivo atual
        objective_campaigns = data_campaigns[data_campaigns['objetivo'] == objective]
        
        # Exibir cabeçalho do objetivo
        st.markdown(f"""
        <div class="category-header">
            <h3>{objective}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Exibir cards para cada campanha
        for _, campaign in objective_campaigns.iterrows():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Título e plataforma
                st.markdown(f"### {campaign['nome_campanha']}")
                st.markdown(f"**Plataforma:** {campaign['plataforma']}")
                
                # Status
                status_class = {
                    'ATIVA': 'status-active',
                    'PAUSADA': 'status-paused',
                    'ENCERRADA': 'status-ended',
                    'PLANEJADA': 'status-planned'
                }.get(campaign['status'], 'status-active')
                
                st.markdown(f"""
                <span class="{status_class}">{campaign['status']}</span>
                <span class="objective-{campaign['objetivo'].lower()}">{campaign['objetivo']}</span>
                """, unsafe_allow_html=True)
                
                # Datas
                if 'data_inicio' in campaign and 'data_fim' in campaign:
                    start_date = campaign['data_inicio'].strftime('%d/%m/%Y') if pd.notna(campaign['data_inicio']) else 'N/A'
                    end_date = campaign['data_fim'].strftime('%d/%m/%Y') if pd.notna(campaign['data_fim']) else 'N/A'
                    st.markdown(f"**Período:** {start_date} a {end_date}")
                
                # Descrição
                if 'descricao' in campaign and pd.notna(campaign['descricao']):
                    st.markdown(f"**Descrição:** {campaign['descricao']}")
            
            with col2:
                # Métricas
                if 'orcamento' in campaign and 'gasto_atual' in campaign:
                    budget = campaign['orcamento'] if pd.notna(campaign['orcamento']) else 0
                    spent = campaign['gasto_atual'] if pd.notna(campaign['gasto_atual']) else 0
                    budget_pct = (spent / budget * 100) if budget > 0 else 0
                    
                    st.metric("Orçamento", f"R$ {budget:,.2f}")
                    st.metric("Gasto", f"R$ {spent:,.2f} ({budget_pct:.1f}%)")
                
                if 'conversoes_meta' in campaign and 'conversoes_atual' in campaign:
                    target = campaign['conversoes_meta'] if pd.notna(campaign['conversoes_meta']) else 0
                    conversions = campaign['conversoes_atual'] if pd.notna(campaign['conversoes_atual']) else 0
                    conv_pct = (conversions / target * 100) if target > 0 else 0
                    
                    st.metric("Meta", f"{target:,.0f}")
                    st.metric("Conversões", f"{conversions:,.0f} ({conv_pct:.1f}%)")
            
            st.markdown("---")
    
    # Tabela completa de campanhas
    st.subheader("Todas as Campanhas")
    
    # Formatar tabela
    formatted_campaigns = data_campaigns.copy()
    
    # Formatar datas
    date_columns = ['data_inicio', 'data_fim', 'data_atualizacao']
    for col in date_columns:
        if col in formatted_campaigns.columns:
            formatted_campaigns[col] = formatted_campaigns[col].apply(
                lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else ""
            )
    
    # Formatar valores monetários
    if 'orcamento' in formatted_campaigns.columns:
        formatted_campaigns['orcamento'] = formatted_campaigns['orcamento'].apply(
            lambda x: f"R$ {x:,.2f}" if pd.notna(x) else ""
        )
    
    if 'gasto_atual' in formatted_campaigns.columns:
        formatted_campaigns['gasto_atual'] = formatted_campaigns['gasto_atual'].apply(
            lambda x: f"R$ {x:,.2f}" if pd.notna(x) else ""
        )
    
    # Formatar conversões
    if 'conversoes_meta' in formatted_campaigns.columns:
        formatted_campaigns['conversoes_meta'] = formatted_campaigns['conversoes_meta'].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) else ""
        )
    
    if 'conversoes_atual' in formatted_campaigns.columns:
        formatted_campaigns['conversoes_atual'] = formatted_campaigns['conversoes_atual'].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) else ""
        )
    
    # Formatar percentuais
    if 'percentual_orcamento' in formatted_campaigns.columns:
        formatted_campaigns['percentual_orcamento'] = formatted_campaigns['percentual_orcamento'].apply(
            lambda x: f"{x:.2f}%" if pd.notna(x) else ""
        )
    
    if 'percentual_meta' in formatted_campaigns.columns:
        formatted_campaigns['percentual_meta'] = formatted_campaigns['percentual_meta'].apply(
            lambda x: f"{x:.2f}%" if pd.notna(x) else ""
        )
    
    # Selecionar e renomear colunas para exibição
    display_columns = [
        'nome_campanha', 'plataforma', 'objetivo', 'status', 
        'data_inicio', 'data_fim', 'orcamento', 'gasto_atual', 
        'percentual_orcamento', 'conversoes_meta', 'conversoes_atual', 
        'percentual_meta'
    ]
    display_columns = [col for col in display_columns if col in formatted_campaigns.columns]
    
    column_mapping = {
        'nome_campanha': 'Campanha',
        'plataforma': 'Plataforma',
        'objetivo': 'Objetivo',
        'status': 'Status',
        'data_inicio': 'Início',
        'data_fim': 'Fim',
        'orcamento': 'Orçamento',
        'gasto_atual': 'Gasto',
        'percentual_orcamento': '% Orçamento',
        'conversoes_meta': 'Meta',
        'conversoes_atual': 'Conversões',
        'percentual_meta': '% Meta'
    }
    
    formatted_campaigns = formatted_campaigns[display_columns].rename(
        columns={col: column_mapping.get(col, col) for col in display_columns}
    )
    
    # Exibir tabela
    st.dataframe(formatted_campaigns, use_container_width=True)

def main():
    st.title("📊 Dashboard PSI - Objetivos de Campanha")
    
    # Obter credenciais
    creds = get_credentials()
    if creds is None:
        return
    
    # Conectar ao Google Sheets
    client = gspread.authorize(creds)
    
    # Carregar dados de objetivos de campanha
    data_campaigns = load_campaign_objectives(client)
    
    # Processar dados
    data_campaigns = process_campaign_data(data_campaigns)
    
    if data_campaigns is None or data_campaigns.empty:
        st.warning("Não foi possível processar os dados de objetivos de campanha. Verifique se as planilhas estão configuradas corretamente.")
        
        # Mostrar exemplo de estrutura esperada
        st.subheader("Estrutura esperada das planilhas")
        
        st.write("Planilha: [PAX] OBJETIVOS CAMPANHA")
        
        st.write("Aba 'campanhas':")
        example_campaigns = pd.DataFrame({
            'id_campanha': ['camp1', 'camp2', 'camp3', 'camp4', 'camp5'],
            'nome_campanha': ['Campanha 1', 'Campanha 2', 'Campanha 3', 'Campanha 4', 'Campanha 5'],
            'plataforma': ['Meta Ads', 'Google Ads', 'Meta Ads', 'YouTube', 'Instagram'],
            'objetivo': ['PAX', 'FRANQUIAS', 'HUB', 'PNP', '+PÚBLICO'],
            'status': ['ATIVA', 'PAUSADA', 'ENCERRADA', 'PLANEJADA', 'ATIVA'],
            'data_inicio': ['2025-04-01', '2025-03-15', '2025-02-01', '2025-05-01', '2025-04-10'],
            'data_fim': ['2025-04-30', '2025-04-15', '2025-03-01', '2025-05-30', '2025-05-10'],
            'orcamento': [5000.00, 3000.00, 2000.00, 4000.00, 2500.00],
            'gasto_atual': [2500.00, 1500.00, 2000.00, 0.00, 1000.00],
            'conversoes_meta': [100, 50, 40, 80, 60],
            'conversoes_atual': [60, 20, 40, 0, 25],
            'descricao': ['Descrição da campanha 1', 'Descrição da campanha 2', 'Descrição da campanha 3', 'Descrição da campanha 4', 'Descrição da campanha 5'],
            'data_atualizacao': ['2025-04-15', '2025-04-15', '2025-04-15', '2025-04-15', '2025-04-15']
        })
        st.dataframe(example_campaigns)
        
        return
    
    # Filtros na barra lateral
    st.sidebar.header("Filtros")
    
    # Filtro de plataforma
    platforms = ["Todas"] + sorted(data_campaigns['plataforma'].unique().tolist())
    selected_platform = st.sidebar.selectbox("Plataforma", platforms)
    
    # Filtro de objetivo
    objectives = ["Todos"] + sorted(data_campaigns['objetivo'].unique().tolist())
    selected_objective = st.sidebar.selectbox("Objetivo", objectives)
    
    # Criar visualizações
    create_campaign_objectives_visualizations(data_campaigns, selected_platform, selected_objective)

if __name__ == "__main__":
    main()
