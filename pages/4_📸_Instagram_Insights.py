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
    page_title="Dashboard PSI - Instagram Insights",
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
        background-color: #C13584 !important;
        color: white !important;
        border-color: #C13584 !important;
    }
    
    /* Hover da pill */
    [role="tab"]:hover {
        background-color: #f0f2f6 !important;
        border-color: #C13584 !important;
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
        background: linear-gradient(45deg, #405DE6, #5851DB, #833AB4, #C13584, #E1306C, #FD1D1D, #F56040, #F77737, #FCAF45, #FFDC80);
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    
    /* Estilo para cards de posts */
    .post-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: white;
    }
    
    .post-image {
        border-radius: 8px;
        width: 100%;
        margin-bottom: 10px;
    }
    
    .post-metrics {
        display: flex;
        justify-content: space-between;
        margin-top: 10px;
    }
    
    .post-metric {
        text-align: center;
        padding: 5px;
    }
    
    .post-metric-value {
        font-weight: bold;
        font-size: 18px;
    }
    
    .post-metric-label {
        font-size: 12px;
        color: #666;
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

# Função para carregar dados do Instagram Insights
def load_instagram_data(client):
    try:
        # Verificar se a planilha de Instagram Insights existe
        try:
            sheet = client.open("[PAX] INSTAGRAM INSIGHTS")
            st.sidebar.success(f"Conectado à planilha: {sheet.title}")
        except Exception as e:
            st.error(f"Erro ao acessar a planilha de Instagram Insights: {str(e)}")
            st.info("Verifique se a planilha '[PAX] INSTAGRAM INSIGHTS' existe e se as credenciais têm acesso a ela")
            return None, None, None
        
        # Carregar dados de perfil
        try:
            sheet_profile = sheet.worksheet('perfil')
            data_profile = pd.DataFrame(sheet_profile.get_all_records())
        except Exception as e:
            st.error(f"Erro ao carregar dados de perfil: {str(e)}")
            data_profile = None
        
        # Carregar dados de métricas diárias
        try:
            sheet_daily = sheet.worksheet('metricas_diarias')
            data_daily = pd.DataFrame(sheet_daily.get_all_records())
        except Exception as e:
            st.error(f"Erro ao carregar dados de métricas diárias: {str(e)}")
            data_daily = None
        
        # Carregar dados de posts
        try:
            sheet_posts = sheet.worksheet('posts')
            data_posts = pd.DataFrame(sheet_posts.get_all_records())
        except Exception as e:
            st.error(f"Erro ao carregar dados de posts: {str(e)}")
            data_posts = None
        
        return data_profile, data_daily, data_posts
    
    except Exception as e:
        st.error(f"Erro ao carregar dados do Instagram: {str(e)}")
        return None, None, None

# Função para processar dados do Instagram
def process_instagram_data(data_profile, data_daily, data_posts):
    if data_profile is None or data_daily is None or data_posts is None:
        return None, None, None
    
    try:
        # Processar dados de perfil
        if not data_profile.empty:
            # Converter datas
            if 'data_atualizacao' in data_profile.columns:
                data_profile['data_atualizacao'] = pd.to_datetime(data_profile['data_atualizacao'], errors='coerce')
            
            # Converter métricas numéricas
            numeric_columns = ['seguidores', 'seguindo', 'posts', 'alcance', 'impressoes', 'engajamento']
            for col in numeric_columns:
                if col in data_profile.columns:
                    data_profile[col] = pd.to_numeric(data_profile[col], errors='coerce')
        
        # Processar dados diários
        if not data_daily.empty:
            # Converter datas
            if 'data' in data_daily.columns:
                data_daily['data'] = pd.to_datetime(data_daily['data'], errors='coerce')
            
            # Converter métricas numéricas
            numeric_columns = ['seguidores', 'alcance', 'impressoes', 'visitas_perfil', 'cliques_site', 'novos_seguidores']
            for col in numeric_columns:
                if col in data_daily.columns:
                    data_daily[col] = pd.to_numeric(data_daily[col], errors='coerce')
        
        # Processar dados de posts
        if not data_posts.empty:
            # Converter datas
            if 'data_publicacao' in data_posts.columns:
                data_posts['data_publicacao'] = pd.to_datetime(data_posts['data_publicacao'], errors='coerce')
            
            # Converter métricas numéricas
            numeric_columns = ['curtidas', 'comentarios', 'salvos', 'compartilhamentos', 'alcance', 'impressoes', 'engajamento']
            for col in numeric_columns:
                if col in data_posts.columns:
                    data_posts[col] = pd.to_numeric(data_posts[col], errors='coerce')
            
            # Calcular taxa de engajamento
            if all(col in data_posts.columns for col in ['curtidas', 'comentarios', 'alcance']):
                data_posts['taxa_engajamento'] = ((data_posts['curtidas'] + data_posts['comentarios']) / data_posts['alcance'] * 100).round(2)
        
        return data_profile, data_daily, data_posts
    
    except Exception as e:
        st.error(f"Erro ao processar dados do Instagram: {str(e)}")
        return None, None, None

# Função para criar visualizações de perfil
def create_profile_visualizations(data_profile, account_id=None):
    if data_profile is None or data_profile.empty:
        st.warning("Não há dados de perfil disponíveis.")
        return
    
    # Filtrar por conta se especificado
    if account_id:
        data_profile = data_profile[data_profile['id_conta'] == account_id]
    
    # Verificar se há dados após filtragem
    if len(data_profile) == 0:
        st.warning(f"Não há dados de perfil disponíveis para a conta selecionada: {account_id}")
        return
    
    # Obter dados do perfil mais recente
    latest_profile = data_profile.sort_values('data_atualizacao', ascending=False).iloc[0]
    
    # Exibir métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Seguidores", f"{latest_profile['seguidores']:,.0f}")
    
    with col2:
        st.metric("Seguindo", f"{latest_profile['seguindo']:,.0f}")
    
    with col3:
        st.metric("Posts", f"{latest_profile['posts']:,.0f}")
    
    with col4:
        if 'taxa_engajamento' in latest_profile:
            st.metric("Taxa de Engajamento", f"{latest_profile['taxa_engajamento']:.2f}%")
        elif 'engajamento' in latest_profile and 'impressoes' in latest_profile and latest_profile['impressoes'] > 0:
            engagement_rate = (latest_profile['engajamento'] / latest_profile['impressoes'] * 100)
            st.metric("Taxa de Engajamento", f"{engagement_rate:.2f}%")
    
    # Exibir informações adicionais
    st.subheader("Informações do Perfil")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'nome_usuario' in latest_profile:
            st.write(f"**Nome de Usuário:** @{latest_profile['nome_usuario']}")
        if 'nome_completo' in latest_profile:
            st.write(f"**Nome Completo:** {latest_profile['nome_completo']}")
        if 'categoria' in latest_profile:
            st.write(f"**Categoria:** {latest_profile['categoria']}")
    
    with col2:
        if 'data_atualizacao' in latest_profile:
            st.write(f"**Última Atualização:** {latest_profile['data_atualizacao'].strftime('%d/%m/%Y %H:%M')}")
        if 'website' in latest_profile:
            st.write(f"**Website:** {latest_profile['website']}")
        if 'email' in latest_profile:
            st.write(f"**Email:** {latest_profile['email']}")

# Função para criar visualizações de métricas diárias
def create_daily_visualizations(data_daily, account_id=None):
    if data_daily is None or data_daily.empty:
        st.warning("Não há dados de métricas diárias disponíveis.")
        return
    
    # Filtrar por conta se especificado
    if account_id:
        data_daily = data_daily[data_daily['id_conta'] == account_id]
    
    # Verificar se há dados após filtragem
    if len(data_daily) == 0:
        st.warning(f"Não há dados de métricas diárias disponíveis para a conta selecionada: {account_id}")
        return
    
    # Ordenar por data
    data_daily = data_daily.sort_values('data')
    
    # Gráfico de tendência de seguidores
    st.subheader("Evolução de Seguidores")
    
    fig = px.line(
        data_daily,
        x='data',
        y='seguidores',
        title="Evolução do Número de Seguidores",
        markers=True
    )
    
    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Seguidores",
        template="plotly_white",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de tendência de métricas de alcance e impressões
    st.subheader("Alcance e Impressões")
    
    # Verificar quais colunas estão disponíveis
    available_metrics = []
    if 'alcance' in data_daily.columns:
        available_metrics.append('alcance')
    if 'impressoes' in data_daily.columns:
        available_metrics.append('impressoes')
    
    if available_metrics:
        fig = go.Figure()
        
        for metric in available_metrics:
            fig.add_trace(go.Scatter(
                x=data_daily['data'],
                y=data_daily[metric],
                mode='lines+markers',
                name=metric.capitalize()
            ))
        
        fig.update_layout(
            title="Evolução de Alcance e Impressões",
            xaxis_title="Data",
            yaxis_title="Valor",
            legend_title="Métrica",
            template="plotly_white",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de tendência de engajamento
    engagement_metrics = []
    if 'visitas_perfil' in data_daily.columns:
        engagement_metrics.append('visitas_perfil')
    if 'cliques_site' in data_daily.columns:
        engagement_metrics.append('cliques_site')
    if 'novos_seguidores' in data_daily.columns:
        engagement_metrics.append('novos_seguidores')
    
    if engagement_metrics:
        st.subheader("Métricas de Engajamento")
        
        fig = go.Figure()
        
        for metric in engagement_metrics:
            fig.add_trace(go.Scatter(
                x=data_daily['data'],
                y=data_daily[metric],
                mode='lines+markers',
                name=' '.join(word.capitalize() for word in metric.split('_'))
            ))
        
        fig.update_layout(
            title="Evolução de Métricas de Engajamento",
            xaxis_title="Data",
            yaxis_title="Valor",
            legend_title="Métrica",
            template="plotly_white",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabela de métricas diárias
    st.subheader("Tabela de Métricas Diárias")
    
    # Formatar tabela
    formatted_daily = data_daily.copy()
    formatted_daily['data'] = formatted_daily['data'].dt.strftime('%d/%m/%Y')
    
    # Formatar colunas numéricas
    numeric_columns = ['seguidores', 'alcance', 'impressoes', 'visitas_perfil', 'cliques_site', 'novos_seguidores']
    for col in numeric_columns:
        if col in formatted_daily.columns:
            formatted_daily[col] = formatted_daily[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
    
    # Renomear colunas para exibição
    column_mapping = {
        'data': 'Data',
        'seguidores': 'Seguidores',
        'alcance': 'Alcance',
        'impressoes': 'Impressões',
        'visitas_perfil': 'Visitas ao Perfil',
        'cliques_site': 'Cliques no Site',
        'novos_seguidores': 'Novos Seguidores'
    }
    
    formatted_daily = formatted_daily.rename(columns={col: column_mapping.get(col, col) for col in formatted_daily.columns})
    
    # Exibir tabela
    st.dataframe(formatted_daily, use_container_width=True)

# Função para criar visualizações de posts
def create_posts_visualizations(data_posts, account_id=None):
    if data_posts is None or data_posts.empty:
        st.warning("Não há dados de posts disponíveis.")
        return
    
    # Filtrar por conta se especificado
    if account_id:
        data_posts = data_posts[data_posts['id_conta'] == account_id]
    
    # Verificar se há dados após filtragem
    if len(data_posts) == 0:
        st.warning(f"Não há dados de posts disponíveis para a conta selecionada: {account_id}")
        return
    
    # Ordenar por data de publicação (mais recentes primeiro)
    data_posts = data_posts.sort_values('data_publicacao', ascending=False)
    
    # Análise de desempenho por tipo de post
    if 'tipo' in data_posts.columns:
        st.subheader("Desempenho por Tipo de Post")
        
        # Agrupar dados por tipo de post
        post_type_metrics = data_posts.groupby('tipo').agg({
            'curtidas': 'mean',
            'comentarios': 'mean',
            'salvos': 'mean',
            'compartilhamentos': 'mean',
            'alcance': 'mean',
            'impressoes': 'mean',
            'taxa_engajamento': 'mean'
        }).reset_index()
        
        # Arredondar valores
        numeric_columns = ['curtidas', 'comentarios', 'salvos', 'compartilhamentos', 'alcance', 'impressoes', 'taxa_engajamento']
        for col in numeric_columns:
            if col in post_type_metrics.columns:
                post_type_metrics[col] = post_type_metrics[col].round(2)
        
        # Seletor de métrica para comparação
        post_metric = st.selectbox(
            "Selecione a métrica para comparar tipos de post",
            options=["Taxa de Engajamento", "Curtidas", "Comentários", "Salvos", "Compartilhamentos", "Alcance", "Impressões"],
            index=0
        )
        
        # Mapear seleção para coluna
        metric_mapping = {
            "Taxa de Engajamento": "taxa_engajamento",
            "Curtidas": "curtidas",
            "Comentários": "comentarios",
            "Salvos": "salvos",
            "Compartilhamentos": "compartilhamentos",
            "Alcance": "alcance",
            "Impressões": "impressoes"
        }
        
        selected_col = metric_mapping[post_metric]
        
        # Criar gráfico de barras
        fig = px.bar(
            post_type_metrics,
            x='tipo',
            y=selected_col,
            title=f"{post_metric} Média por Tipo de Post",
            labels={'tipo': 'Tipo de Post', selected_col: post_metric},
            color='tipo',
            height=400
        )
        
        # Ajustar layout
        fig.update_layout(
            xaxis_title="Tipo de Post",
            yaxis_title=post_metric,
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Melhores horários para postar
    if 'data_publicacao' in data_posts.columns:
        st.subheader("Melhores Horários para Postar")
        
        # Extrair hora do dia
        data_posts['hora'] = data_posts['data_publicacao'].dt.hour
        
        # Agrupar por hora
        hourly_performance = data_posts.groupby('hora').agg({
            'taxa_engajamento': 'mean',
            'alcance': 'mean',
            'curtidas': 'mean'
        }).reset_index()
        
        # Criar gráfico
        fig = px.line(
            hourly_performance,
            x='hora',
            y='taxa_engajamento',
            title="Taxa de Engajamento Média por Hora do Dia",
            markers=True
        )
        
        # Ajustar layout
        fig.update_layout(
            xaxis_title="Hora do Dia",
            yaxis_title="Taxa de Engajamento Média (%)",
            template="plotly_white",
            height=400,
            xaxis=dict(
                tickmode='linear',
                tick0=0,
                dtick=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Top posts
    st.subheader("Top Posts por Engajamento")
    
    # Ordenar por taxa de engajamento
    top_posts = data_posts.sort_values('taxa_engajamento', ascending=False).head(5)
    
    # Exibir cards para os top posts
    for _, post in top_posts.iterrows():
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if 'url_imagem' in post and post['url_imagem']:
                st.image(post['url_imagem'], caption=f"Post de {post['data_publicacao'].strftime('%d/%m/%Y')}")
            else:
                st.write("Imagem não disponível")
        
        with col2:
            if 'legenda' in post:
                st.write(f"**Legenda:** {post['legenda'][:100]}..." if len(post['legenda']) > 100 else f"**Legenda:** {post['legenda']}")
            
            if 'tipo' in post:
                st.write(f"**Tipo:** {post['tipo']}")
            
            if 'data_publicacao' in post:
                st.write(f"**Data:** {post['data_publicacao'].strftime('%d/%m/%Y %H:%M')}")
            
            # Métricas do post
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
            
            with metrics_col1:
                st.metric("Curtidas", f"{post['curtidas']:,.0f}")
            
            with metrics_col2:
                st.metric("Comentários", f"{post['comentarios']:,.0f}")
            
            with metrics_col3:
                st.metric("Alcance", f"{post['alcance']:,.0f}")
            
            with metrics_col4:
                st.metric("Taxa Eng.", f"{post['taxa_engajamento']:.2f}%")
        
        st.markdown("---")
    
    # Tabela completa de posts
    st.subheader("Todos os Posts")
    
    # Formatar tabela
    formatted_posts = data_posts.copy()
    formatted_posts['data_publicacao'] = formatted_posts['data_publicacao'].dt.strftime('%d/%m/%Y %H:%M')
    
    # Formatar colunas numéricas
    numeric_columns = ['curtidas', 'comentarios', 'salvos', 'compartilhamentos', 'alcance', 'impressoes']
    for col in numeric_columns:
        if col in formatted_posts.columns:
            formatted_posts[col] = formatted_posts[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
    
    if 'taxa_engajamento' in formatted_posts.columns:
        formatted_posts['taxa_engajamento'] = formatted_posts['taxa_engajamento'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
    
    # Selecionar e renomear colunas para exibição
    display_columns = ['data_publicacao', 'tipo', 'curtidas', 'comentarios', 'salvos', 'compartilhamentos', 'alcance', 'impressoes', 'taxa_engajamento']
    display_columns = [col for col in display_columns if col in formatted_posts.columns]
    
    column_mapping = {
        'data_publicacao': 'Data',
        'tipo': 'Tipo',
        'curtidas': 'Curtidas',
        'comentarios': 'Comentários',
        'salvos': 'Salvos',
        'compartilhamentos': 'Compartilhamentos',
        'alcance': 'Alcance',
        'impressoes': 'Impressões',
        'taxa_engajamento': 'Taxa Eng.'
    }
    
    formatted_posts = formatted_posts[display_columns].rename(columns={col: column_mapping.get(col, col) for col in display_columns})
    
    # Exibir tabela
    st.dataframe(formatted_posts, use_container_width=True)

def main():
    st.title("📊 Dashboard PSI - Instagram Insights")
    
    # Obter credenciais
    creds = get_credentials()
    if creds is None:
        return
    
    # Conectar ao Google Sheets
    client = gspread.authorize(creds)
    
    # Carregar dados do Instagram
    data_profile, data_daily, data_posts = load_instagram_data(client)
    
    # Processar dados
    data_profile, data_daily, data_posts = process_instagram_data(data_profile, data_daily, data_posts)
    
    if data_profile is None and data_daily is None and data_posts is None:
        st.warning("Não foi possível processar os dados do Instagram. Verifique se as planilhas estão configuradas corretamente.")
        
        # Mostrar exemplo de estrutura esperada
        st.subheader("Estrutura esperada das planilhas")
        
        st.write("Planilha: [PAX] INSTAGRAM INSIGHTS")
        
        st.write("Aba 'perfil':")
        example_profile = pd.DataFrame({
            'id_conta': ['123456789', '987654321'],
            'nome_usuario': ['psi_principal', 'psi_secundaria'],
            'nome_completo': ['PSI Principal', 'PSI Secundária'],
            'categoria': ['Saúde/Beleza', 'Saúde/Beleza'],
            'seguidores': [10000, 5000],
            'seguindo': [500, 300],
            'posts': [120, 80],
            'website': ['https://psi.com.br', 'https://psi.com.br/secundaria'],
            'email': ['contato@psi.com.br', 'secundaria@psi.com.br'],
            'alcance': [25000, 12000],
            'impressoes': [30000, 15000],
            'engajamento': [5000, 2500],
            'data_atualizacao': ['2025-04-01', '2025-04-01']
        })
        st.dataframe(example_profile)
        
        st.write("Aba 'metricas_diarias':")
        example_daily = pd.DataFrame({
            'id_conta': ['123456789', '123456789', '987654321', '987654321'],
            'data': ['2025-04-01', '2025-04-02', '2025-04-01', '2025-04-02'],
            'seguidores': [10000, 10050, 5000, 5020],
            'alcance': [2500, 2600, 1200, 1250],
            'impressoes': [3000, 3100, 1500, 1550],
            'visitas_perfil': [500, 520, 250, 260],
            'cliques_site': [100, 110, 50, 55],
            'novos_seguidores': [50, 55, 20, 22]
        })
        st.dataframe(example_daily)
        
        st.write("Aba 'posts':")
        example_posts = pd.DataFrame({
            'id_conta': ['123456789', '123456789', '987654321', '987654321'],
            'id_post': ['post1', 'post2', 'post3', 'post4'],
            'tipo': ['Carrossel', 'Imagem', 'Vídeo', 'Reels'],
            'legenda': ['Exemplo de legenda 1', 'Exemplo de legenda 2', 'Exemplo de legenda 3', 'Exemplo de legenda 4'],
            'url_imagem': ['https://exemplo.com/img1.jpg', 'https://exemplo.com/img2.jpg', 'https://exemplo.com/img3.jpg', 'https://exemplo.com/img4.jpg'],
            'data_publicacao': ['2025-04-01 10:00', '2025-04-02 15:30', '2025-04-01 12:00', '2025-04-02 18:00'],
            'curtidas': [500, 600, 250, 300],
            'comentarios': [50, 60, 25, 30],
            'salvos': [100, 120, 50, 60],
            'compartilhamentos': [80, 90, 40, 45],
            'alcance': [2000, 2200, 1000, 1100],
            'impressoes': [2500, 2700, 1200, 1300]
        })
        st.dataframe(example_posts)
        
        return
    
    # Verificar se há múltiplas contas
    has_multiple_accounts = False
    account_column = None
    
    for df in [data_profile, data_daily, data_posts]:
        if df is not None and 'id_conta' in df.columns and len(df['id_conta'].unique()) > 1:
            has_multiple_accounts = True
            account_column = 'id_conta'
            break
    
    if has_multiple_accounts and account_column:
        # Coletar informações de contas de todos os dataframes
        accounts = []
        
        if data_profile is not None and account_column in data_profile.columns:
            profile_accounts = data_profile[[account_column, 'nome_usuario']].drop_duplicates()
            accounts.append(profile_accounts)
        
        if data_daily is not None and account_column in data_daily.columns:
            daily_accounts = data_daily[[account_column]].drop_duplicates()
            if 'nome_usuario' not in daily_accounts.columns:
                daily_accounts['nome_usuario'] = daily_accounts[account_column]
            accounts.append(daily_accounts)
        
        if data_posts is not None and account_column in data_posts.columns:
            posts_accounts = data_posts[[account_column]].drop_duplicates()
            if 'nome_usuario' not in posts_accounts.columns:
                posts_accounts['nome_usuario'] = posts_accounts[account_column]
            accounts.append(posts_accounts)
        
        # Mesclar informações de contas
        unique_accounts = pd.concat(accounts).drop_duplicates(subset=[account_column])
        
        # Adicionar opção para visualizar todas as contas
        all_accounts_option = pd.DataFrame({
            account_column: ['all'],
            'nome_usuario': ['Todas as Contas']
        })
        unique_accounts = pd.concat([all_accounts_option, unique_accounts])
        
        # Seletor de conta
        selected_account = st.sidebar.selectbox(
            "Selecione a Conta",
            options=unique_accounts[account_column].tolist(),
            format_func=lambda x: unique_accounts.loc[unique_accounts[account_column] == x, 'nome_usuario'].iloc[0],
            index=0
        )
        
        if selected_account == 'all':
            # Mostrar dados de todas as contas
            st.header("Visão Geral - Todas as Contas")
            
            # Mostrar métricas por conta
            st.header("Métricas por Conta")
            
            # Exibir métricas para cada conta
            for _, account in unique_accounts[unique_accounts[account_column] != 'all'].iterrows():
                account_id = account[account_column]
                account_name = account['nome_usuario']
                
                st.markdown(f"""
                <div class="account-header">
                    <h3>@{account_name} (ID: {account_id})</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Criar abas para diferentes visualizações
                tab1, tab2, tab3 = st.tabs(["Perfil", "Métricas Diárias", "Posts"])
                
                with tab1:
                    create_profile_visualizations(data_profile, account_id)
                
                with tab2:
                    create_daily_visualizations(data_daily, account_id)
                
                with tab3:
                    create_posts_visualizations(data_posts, account_id)
        else:
            # Mostrar dados da conta selecionada
            account_name = unique_accounts.loc[unique_accounts[account_column] == selected_account, 'nome_usuario'].iloc[0]
            st.header(f"Conta: @{account_name}")
            
            # Criar abas para diferentes visualizações
            tab1, tab2, tab3 = st.tabs(["Perfil", "Métricas Diárias", "Posts"])
            
            with tab1:
                create_profile_visualizations(data_profile, selected_account)
            
            with tab2:
                create_daily_visualizations(data_daily, selected_account)
            
            with tab3:
                create_posts_visualizations(data_posts, selected_account)
    else:
        # Apenas uma conta, mostrar dados diretamente
        # Criar abas para diferentes visualizações
        tab1, tab2, tab3 = st.tabs(["Perfil", "Métricas Diárias", "Posts"])
        
        with tab1:
            create_profile_visualizations(data_profile)
        
        with tab2:
            create_daily_visualizations(data_daily)
        
        with tab3:
            create_posts_visualizations(data_posts)

if __name__ == "__main__":
    main()
