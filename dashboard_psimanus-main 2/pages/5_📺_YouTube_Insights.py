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
    page_title="Dashboard PSI - YouTube Insights",
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
        background-color: #FF0000 !important;
        color: white !important;
        border-color: #FF0000 !important;
    }
    
    /* Hover da pill */
    [role="tab"]:hover {
        background-color: #f0f2f6 !important;
        border-color: #FF0000 !important;
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
        background-color: #FF0000;
        color: white;
        padding: 10px 15px;
        border-radius: 10px;
        margin-bottom: 15px;
    }
    
    /* Estilo para cards de vídeos */
    .video-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: white;
    }
    
    .video-thumbnail {
        border-radius: 8px;
        width: 100%;
        margin-bottom: 10px;
    }
    
    .video-metrics {
        display: flex;
        justify-content: space-between;
        margin-top: 10px;
    }
    
    .video-metric {
        text-align: center;
        padding: 5px;
    }
    
    .video-metric-value {
        font-weight: bold;
        font-size: 18px;
    }
    
    .video-metric-label {
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

# Função para carregar dados do YouTube Insights
def load_youtube_data(client):
    try:
        # Verificar se a planilha de YouTube Insights existe
        try:
            sheet = client.open("[PAX] YOUTUBE INSIGHTS")
            st.sidebar.success(f"Conectado à planilha: {sheet.title}")
        except Exception as e:
            st.error(f"Erro ao acessar a planilha de YouTube Insights: {str(e)}")
            st.info("Verifique se a planilha '[PAX] YOUTUBE INSIGHTS' existe e se as credenciais têm acesso a ela")
            return None, None, None
        
        # Carregar dados de canal
        try:
            sheet_channel = sheet.worksheet('canal')
            data_channel = pd.DataFrame(sheet_channel.get_all_records())
        except Exception as e:
            st.error(f"Erro ao carregar dados de canal: {str(e)}")
            data_channel = None
        
        # Carregar dados de métricas diárias
        try:
            sheet_daily = sheet.worksheet('metricas_diarias')
            data_daily = pd.DataFrame(sheet_daily.get_all_records())
        except Exception as e:
            st.error(f"Erro ao carregar dados de métricas diárias: {str(e)}")
            data_daily = None
        
        # Carregar dados de vídeos
        try:
            sheet_videos = sheet.worksheet('videos')
            data_videos = pd.DataFrame(sheet_videos.get_all_records())
        except Exception as e:
            st.error(f"Erro ao carregar dados de vídeos: {str(e)}")
            data_videos = None
        
        return data_channel, data_daily, data_videos
    
    except Exception as e:
        st.error(f"Erro ao carregar dados do YouTube: {str(e)}")
        return None, None, None

# Função para processar dados do YouTube
def process_youtube_data(data_channel, data_daily, data_videos):
    if data_channel is None or data_daily is None or data_videos is None:
        return None, None, None
    
    try:
        # Processar dados de canal
        if not data_channel.empty:
            # Converter datas
            if 'data_atualizacao' in data_channel.columns:
                data_channel['data_atualizacao'] = pd.to_datetime(data_channel['data_atualizacao'], errors='coerce')
            
            # Converter métricas numéricas
            numeric_columns = ['inscritos', 'videos', 'visualizacoes', 'horas_assistidas']
            for col in numeric_columns:
                if col in data_channel.columns:
                    data_channel[col] = pd.to_numeric(data_channel[col], errors='coerce')
        
        # Processar dados diários
        if not data_daily.empty:
            # Converter datas
            if 'data' in data_daily.columns:
                data_daily['data'] = pd.to_datetime(data_daily['data'], errors='coerce')
            
            # Converter métricas numéricas
            numeric_columns = ['inscritos', 'visualizacoes', 'horas_assistidas', 'novos_inscritos', 'impressoes', 'ctr']
            for col in numeric_columns:
                if col in data_daily.columns:
                    data_daily[col] = pd.to_numeric(data_daily[col], errors='coerce')
        
        # Processar dados de vídeos
        if not data_videos.empty:
            # Converter datas
            if 'data_publicacao' in data_videos.columns:
                data_videos['data_publicacao'] = pd.to_datetime(data_videos['data_publicacao'], errors='coerce')
            
            # Converter métricas numéricas
            numeric_columns = ['visualizacoes', 'likes', 'comentarios', 'compartilhamentos', 'tempo_assistido', 'impressoes', 'ctr']
            for col in numeric_columns:
                if col in data_videos.columns:
                    data_videos[col] = pd.to_numeric(data_videos[col], errors='coerce')
            
            # Calcular taxa de engajamento
            if all(col in data_videos.columns for col in ['likes', 'comentarios', 'visualizacoes']):
                data_videos['taxa_engajamento'] = ((data_videos['likes'] + data_videos['comentarios']) / data_videos['visualizacoes'] * 100).round(2)
        
        return data_channel, data_daily, data_videos
    
    except Exception as e:
        st.error(f"Erro ao processar dados do YouTube: {str(e)}")
        return None, None, None

# Função para criar visualizações de canal
def create_channel_visualizations(data_channel, account_id=None):
    if data_channel is None or data_channel.empty:
        st.warning("Não há dados de canal disponíveis.")
        return
    
    # Filtrar por conta se especificado
    if account_id:
        data_channel = data_channel[data_channel['id_conta'] == account_id]
    
    # Verificar se há dados após filtragem
    if len(data_channel) == 0:
        st.warning(f"Não há dados de canal disponíveis para a conta selecionada: {account_id}")
        return
    
    # Obter dados do canal mais recente
    latest_channel = data_channel.sort_values('data_atualizacao', ascending=False).iloc[0]
    
    # Exibir métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Inscritos", f"{latest_channel['inscritos']:,.0f}")
    
    with col2:
        st.metric("Vídeos", f"{latest_channel['videos']:,.0f}")
    
    with col3:
        st.metric("Visualizações Totais", f"{latest_channel['visualizacoes']:,.0f}")
    
    with col4:
        if 'horas_assistidas' in latest_channel:
            st.metric("Horas Assistidas", f"{latest_channel['horas_assistidas']:,.0f}")
    
    # Exibir informações adicionais
    st.subheader("Informações do Canal")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'nome_canal' in latest_channel:
            st.write(f"**Nome do Canal:** {latest_channel['nome_canal']}")
        if 'descricao' in latest_channel:
            st.write(f"**Descrição:** {latest_channel['descricao']}")
    
    with col2:
        if 'data_atualizacao' in latest_channel:
            st.write(f"**Última Atualização:** {latest_channel['data_atualizacao'].strftime('%d/%m/%Y %H:%M')}")
        if 'data_criacao' in latest_channel:
            st.write(f"**Data de Criação:** {pd.to_datetime(latest_channel['data_criacao']).strftime('%d/%m/%Y')}")
        if 'url_canal' in latest_channel:
            st.write(f"**URL do Canal:** {latest_channel['url_canal']}")

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
    
    # Gráfico de tendência de inscritos
    st.subheader("Evolução de Inscritos")
    
    fig = px.line(
        data_daily,
        x='data',
        y='inscritos',
        title="Evolução do Número de Inscritos",
        markers=True
    )
    
    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Inscritos",
        template="plotly_white",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de tendência de visualizações e horas assistidas
    st.subheader("Visualizações e Horas Assistidas")
    
    # Verificar quais colunas estão disponíveis
    available_metrics = []
    if 'visualizacoes' in data_daily.columns:
        available_metrics.append('visualizacoes')
    if 'horas_assistidas' in data_daily.columns:
        available_metrics.append('horas_assistidas')
    
    if available_metrics:
        # Criar figura com dois eixos Y
        fig = go.Figure()
        
        # Adicionar visualizações no eixo Y primário
        if 'visualizacoes' in available_metrics:
            fig.add_trace(go.Scatter(
                x=data_daily['data'],
                y=data_daily['visualizacoes'],
                mode='lines+markers',
                name='Visualizações',
                line=dict(color='#FF0000')
            ))
        
        # Adicionar horas assistidas no eixo Y secundário
        if 'horas_assistidas' in available_metrics:
            fig.add_trace(go.Scatter(
                x=data_daily['data'],
                y=data_daily['horas_assistidas'],
                mode='lines+markers',
                name='Horas Assistidas',
                line=dict(color='#0066FF'),
                yaxis='y2'
            ))
        
        # Configurar layout com dois eixos Y
        fig.update_layout(
            title="Evolução de Visualizações e Horas Assistidas",
            xaxis_title="Data",
            yaxis_title="Visualizações",
            yaxis2=dict(
                title="Horas Assistidas",
                overlaying='y',
                side='right'
            ),
            legend_title="Métrica",
            template="plotly_white",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de tendência de impressões e CTR
    if 'impressoes' in data_daily.columns and 'ctr' in data_daily.columns:
        st.subheader("Impressões e CTR")
        
        # Criar figura com dois eixos Y
        fig = go.Figure()
        
        # Adicionar impressões no eixo Y primário
        fig.add_trace(go.Scatter(
            x=data_daily['data'],
            y=data_daily['impressoes'],
            mode='lines+markers',
            name='Impressões',
            line=dict(color='#FF9900')
        ))
        
        # Adicionar CTR no eixo Y secundário
        fig.add_trace(go.Scatter(
            x=data_daily['data'],
            y=data_daily['ctr'],
            mode='lines+markers',
            name='CTR (%)',
            line=dict(color='#00CC66'),
            yaxis='y2'
        ))
        
        # Configurar layout com dois eixos Y
        fig.update_layout(
            title="Evolução de Impressões e CTR",
            xaxis_title="Data",
            yaxis_title="Impressões",
            yaxis2=dict(
                title="CTR (%)",
                overlaying='y',
                side='right'
            ),
            legend_title="Métrica",
            template="plotly_white",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de novos inscritos
    if 'novos_inscritos' in data_daily.columns:
        st.subheader("Novos Inscritos por Dia")
        
        fig = px.bar(
            data_daily,
            x='data',
            y='novos_inscritos',
            title="Novos Inscritos por Dia",
            color_discrete_sequence=['#FF0000']
        )
        
        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="Novos Inscritos",
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
    numeric_columns = ['inscritos', 'visualizacoes', 'horas_assistidas', 'novos_inscritos', 'impressoes']
    for col in numeric_columns:
        if col in formatted_daily.columns:
            formatted_daily[col] = formatted_daily[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
    
    # Formatar CTR
    if 'ctr' in formatted_daily.columns:
        formatted_daily['ctr'] = formatted_daily['ctr'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
    
    # Renomear colunas para exibição
    column_mapping = {
        'data': 'Data',
        'inscritos': 'Inscritos',
        'visualizacoes': 'Visualizações',
        'horas_assistidas': 'Horas Assistidas',
        'novos_inscritos': 'Novos Inscritos',
        'impressoes': 'Impressões',
        'ctr': 'CTR'
    }
    
    formatted_daily = formatted_daily.rename(columns={col: column_mapping.get(col, col) for col in formatted_daily.columns})
    
    # Exibir tabela
    st.dataframe(formatted_daily, use_container_width=True)

# Função para criar visualizações de vídeos
def create_videos_visualizations(data_videos, account_id=None):
    if data_videos is None or data_videos.empty:
        st.warning("Não há dados de vídeos disponíveis.")
        return
    
    # Filtrar por conta se especificado
    if account_id:
        data_videos = data_videos[data_videos['id_conta'] == account_id]
    
    # Verificar se há dados após filtragem
    if len(data_videos) == 0:
        st.warning(f"Não há dados de vídeos disponíveis para a conta selecionada: {account_id}")
        return
    
    # Ordenar por data de publicação (mais recentes primeiro)
    data_videos = data_videos.sort_values('data_publicacao', ascending=False)
    
    # Análise de desempenho por categoria
    if 'categoria' in data_videos.columns:
        st.subheader("Desempenho por Categoria")
        
        # Agrupar dados por categoria
        category_metrics = data_videos.groupby('categoria').agg({
            'visualizacoes': 'mean',
            'likes': 'mean',
            'comentarios': 'mean',
            'compartilhamentos': 'mean',
            'tempo_assistido': 'mean',
            'impressoes': 'mean',
            'ctr': 'mean'
        }).reset_index()
        
        # Arredondar valores
        numeric_columns = ['visualizacoes', 'likes', 'comentarios', 'compartilhamentos', 'tempo_assistido', 'impressoes', 'ctr']
        for col in numeric_columns:
            if col in category_metrics.columns:
                category_metrics[col] = category_metrics[col].round(2)
        
        # Seletor de métrica para comparação
        video_metric = st.selectbox(
            "Selecione a métrica para comparar categorias",
            options=["Visualizações", "Likes", "Comentários", "Compartilhamentos", "Tempo Assistido (min)", "Impressões", "CTR (%)"],
            index=0
        )
        
        # Mapear seleção para coluna
        metric_mapping = {
            "Visualizações": "visualizacoes",
            "Likes": "likes",
            "Comentários": "comentarios",
            "Compartilhamentos": "compartilhamentos",
            "Tempo Assistido (min)": "tempo_assistido",
            "Impressões": "impressoes",
            "CTR (%)": "ctr"
        }
        
        selected_col = metric_mapping[video_metric]
        
        # Criar gráfico de barras
        fig = px.bar(
            category_metrics,
            x='categoria',
            y=selected_col,
            title=f"{video_metric} Média por Categoria",
            labels={'categoria': 'Categoria', selected_col: video_metric},
            color='categoria',
            height=400
        )
        
        # Ajustar layout
        fig.update_layout(
            xaxis_title="Categoria",
            yaxis_title=video_metric,
            template="plotly_white"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Análise de duração do vídeo vs. desempenho
    if 'duracao' in data_videos.columns and 'visualizacoes' in data_videos.columns:
        st.subheader("Relação entre Duração e Desempenho")
        
        # Converter duração para minutos se estiver em formato de string (HH:MM:SS)
        if data_videos['duracao'].dtype == 'object':
            try:
                # Tentar converter de formato HH:MM:SS para minutos
                data_videos['duracao_min'] = data_videos['duracao'].apply(
                    lambda x: sum(int(x) * 60 ** i for i, x in enumerate(reversed(x.split(':'))))
                ) / 60
            except:
                # Se falhar, tentar converter diretamente para número
                data_videos['duracao_min'] = pd.to_numeric(data_videos['duracao'], errors='coerce')
        else:
            # Se já for numérico, assumir que está em segundos e converter para minutos
            data_videos['duracao_min'] = data_videos['duracao'] / 60
        
        # Seletor de métrica para comparação
        perf_metric = st.selectbox(
            "Selecione a métrica de desempenho",
            options=["Visualizações", "Likes", "Comentários", "Tempo Médio de Visualização", "CTR (%)"],
            index=0,
            key="duration_metric"
        )
        
        # Mapear seleção para coluna
        perf_mapping = {
            "Visualizações": "visualizacoes",
            "Likes": "likes",
            "Comentários": "comentarios",
            "Tempo Médio de Visualização": "tempo_medio_visualizacao",
            "CTR (%)": "ctr"
        }
        
        selected_perf = perf_mapping[perf_metric]
        
        # Verificar se a coluna selecionada existe
        if selected_perf in data_videos.columns:
            # Criar gráfico de dispersão
            fig = px.scatter(
                data_videos,
                x='duracao_min',
                y=selected_perf,
                title=f"Relação entre Duração do Vídeo e {perf_metric}",
                labels={'duracao_min': 'Duração (minutos)', selected_perf: perf_metric},
                hover_name='titulo',
                size='visualizacoes',
                color='categoria' if 'categoria' in data_videos.columns else None,
                height=500
            )
            
            # Adicionar linha de tendência
            fig.update_layout(
                xaxis_title="Duração (minutos)",
                yaxis_title=perf_metric,
                template="plotly_white"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"A métrica {perf_metric} não está disponível nos dados.")
    
    # Melhores horários para publicar
    if 'data_publicacao' in data_videos.columns:
        st.subheader("Melhores Horários para Publicar")
        
        # Extrair hora do dia
        data_videos['hora'] = data_videos['data_publicacao'].dt.hour
        
        # Verificar qual métrica usar para avaliar desempenho
        perf_cols = ['visualizacoes', 'likes', 'comentarios', 'taxa_engajamento']
        available_perf = [col for col in perf_cols if col in data_videos.columns]
        
        if available_perf:
            # Usar a primeira métrica disponível
            perf_col = available_perf[0]
            
            # Agrupar por hora
            hourly_performance = data_videos.groupby('hora').agg({
                perf_col: 'mean'
            }).reset_index()
            
            # Criar gráfico
            fig = px.bar(
                hourly_performance,
                x='hora',
                y=perf_col,
                title=f"{perf_col.capitalize().replace('_', ' ')} Média por Hora do Dia",
                labels={'hora': 'Hora do Dia', perf_col: perf_col.capitalize().replace('_', ' ')},
                color_discrete_sequence=['#FF0000']
            )
            
            # Ajustar layout
            fig.update_layout(
                xaxis_title="Hora do Dia",
                yaxis_title=perf_col.capitalize().replace('_', ' '),
                template="plotly_white",
                height=400,
                xaxis=dict(
                    tickmode='linear',
                    tick0=0,
                    dtick=1
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Top vídeos
    st.subheader("Top Vídeos por Visualizações")
    
    # Ordenar por visualizações
    top_videos = data_videos.sort_values('visualizacoes', ascending=False).head(5)
    
    # Exibir cards para os top vídeos
    for _, video in top_videos.iterrows():
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if 'thumbnail' in video and video['thumbnail']:
                st.image(video['thumbnail'], caption=f"Vídeo de {video['data_publicacao'].strftime('%d/%m/%Y')}")
            else:
                st.write("Thumbnail não disponível")
        
        with col2:
            if 'titulo' in video:
                st.write(f"**Título:** {video['titulo']}")
            
            if 'categoria' in video:
                st.write(f"**Categoria:** {video['categoria']}")
            
            if 'data_publicacao' in video:
                st.write(f"**Data:** {video['data_publicacao'].strftime('%d/%m/%Y %H:%M')}")
            
            if 'duracao' in video:
                st.write(f"**Duração:** {video['duracao']}")
            
            # Métricas do vídeo
            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
            
            with metrics_col1:
                st.metric("Visualizações", f"{video['visualizacoes']:,.0f}")
            
            with metrics_col2:
                st.metric("Likes", f"{video['likes']:,.0f}")
            
            with metrics_col3:
                if 'tempo_assistido' in video:
                    st.metric("Tempo Assistido", f"{video['tempo_assistido']:,.0f} min")
            
            with metrics_col4:
                if 'ctr' in video:
                    st.metric("CTR", f"{video['ctr']:.2f}%")
        
        st.markdown("---")
    
    # Tabela completa de vídeos
    st.subheader("Todos os Vídeos")
    
    # Formatar tabela
    formatted_videos = data_videos.copy()
    formatted_videos['data_publicacao'] = formatted_videos['data_publicacao'].dt.strftime('%d/%m/%Y %H:%M')
    
    # Formatar colunas numéricas
    numeric_columns = ['visualizacoes', 'likes', 'comentarios', 'compartilhamentos', 'tempo_assistido', 'impressoes']
    for col in numeric_columns:
        if col in formatted_videos.columns:
            formatted_videos[col] = formatted_videos[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
    
    # Formatar CTR
    if 'ctr' in formatted_videos.columns:
        formatted_videos['ctr'] = formatted_videos['ctr'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
    
    # Selecionar e renomear colunas para exibição
    display_columns = ['data_publicacao', 'titulo', 'duracao', 'categoria', 'visualizacoes', 'likes', 'comentarios', 'tempo_assistido', 'ctr']
    display_columns = [col for col in display_columns if col in formatted_videos.columns]
    
    column_mapping = {
        'data_publicacao': 'Data',
        'titulo': 'Título',
        'duracao': 'Duração',
        'categoria': 'Categoria',
        'visualizacoes': 'Visualizações',
        'likes': 'Likes',
        'comentarios': 'Comentários',
        'compartilhamentos': 'Compartilhamentos',
        'tempo_assistido': 'Tempo Assistido (min)',
        'impressoes': 'Impressões',
        'ctr': 'CTR'
    }
    
    formatted_videos = formatted_videos[display_columns].rename(columns={col: column_mapping.get(col, col) for col in display_columns})
    
    # Exibir tabela
    st.dataframe(formatted_videos, use_container_width=True)

def main():
    st.title("📊 Dashboard PSI - YouTube Insights")
    
    # Obter credenciais
    creds = get_credentials()
    if creds is None:
        return
    
    # Conectar ao Google Sheets
    client = gspread.authorize(creds)
    
    # Carregar dados do YouTube
    data_channel, data_daily, data_videos = load_youtube_data(client)
    
    # Processar dados
    data_channel, data_daily, data_videos = process_youtube_data(data_channel, data_daily, data_videos)
    
    if data_channel is None and data_daily is None and data_videos is None:
        st.warning("Não foi possível processar os dados do YouTube. Verifique se as planilhas estão configuradas corretamente.")
        
        # Mostrar exemplo de estrutura esperada
        st.subheader("Estrutura esperada das planilhas")
        
        st.write("Planilha: [PAX] YOUTUBE INSIGHTS")
        
        st.write("Aba 'canal':")
        example_channel = pd.DataFrame({
            'id_conta': ['123456789', '987654321'],
            'nome_canal': ['PSI Principal', 'PSI Secundário'],
            'descricao': ['Canal principal da PSI', 'Canal secundário da PSI'],
            'url_canal': ['https://youtube.com/c/psiprincipal', 'https://youtube.com/c/psisecundario'],
            'data_criacao': ['2020-01-01', '2021-01-01'],
            'inscritos': [10000, 5000],
            'videos': [120, 80],
            'visualizacoes': [500000, 250000],
            'horas_assistidas': [25000, 12000],
            'data_atualizacao': ['2025-04-01', '2025-04-01']
        })
        st.dataframe(example_channel)
        
        st.write("Aba 'metricas_diarias':")
        example_daily = pd.DataFrame({
            'id_conta': ['123456789', '123456789', '987654321', '987654321'],
            'data': ['2025-04-01', '2025-04-02', '2025-04-01', '2025-04-02'],
            'inscritos': [10000, 10050, 5000, 5020],
            'visualizacoes': [2500, 2600, 1200, 1250],
            'horas_assistidas': [125, 130, 60, 62],
            'novos_inscritos': [50, 55, 20, 22],
            'impressoes': [10000, 10500, 5000, 5200],
            'ctr': [4.5, 4.6, 4.2, 4.3]
        })
        st.dataframe(example_daily)
        
        st.write("Aba 'videos':")
        example_videos = pd.DataFrame({
            'id_conta': ['123456789', '123456789', '987654321', '987654321'],
            'id_video': ['video1', 'video2', 'video3', 'video4'],
            'titulo': ['Vídeo 1', 'Vídeo 2', 'Vídeo 3', 'Vídeo 4'],
            'descricao': ['Descrição do vídeo 1', 'Descrição do vídeo 2', 'Descrição do vídeo 3', 'Descrição do vídeo 4'],
            'thumbnail': ['https://exemplo.com/img1.jpg', 'https://exemplo.com/img2.jpg', 'https://exemplo.com/img3.jpg', 'https://exemplo.com/img4.jpg'],
            'categoria': ['Educação', 'Saúde', 'Educação', 'Saúde'],
            'duracao': ['10:30', '15:45', '08:20', '12:15'],
            'data_publicacao': ['2025-04-01 10:00', '2025-04-02 15:30', '2025-04-01 12:00', '2025-04-02 18:00'],
            'visualizacoes': [1500, 1800, 800, 900],
            'likes': [120, 150, 70, 80],
            'comentarios': [30, 40, 15, 20],
            'compartilhamentos': [50, 60, 25, 30],
            'tempo_assistido': [250, 300, 120, 140],
            'impressoes': [5000, 5500, 2500, 2700],
            'ctr': [5.2, 5.5, 4.8, 5.0]
        })
        st.dataframe(example_videos)
        
        return
    
    # Verificar se há múltiplas contas
    has_multiple_accounts = False
    account_column = None
    
    for df in [data_channel, data_daily, data_videos]:
        if df is not None and 'id_conta' in df.columns and len(df['id_conta'].unique()) > 1:
            has_multiple_accounts = True
            account_column = 'id_conta'
            break
    
    if has_multiple_accounts and account_column:
        # Coletar informações de contas de todos os dataframes
        accounts = []
        
        if data_channel is not None and account_column in data_channel.columns:
            channel_accounts = data_channel[[account_column, 'nome_canal']].drop_duplicates()
            accounts.append(channel_accounts)
        
        if data_daily is not None and account_column in data_daily.columns:
            daily_accounts = data_daily[[account_column]].drop_duplicates()
            if 'nome_canal' not in daily_accounts.columns:
                daily_accounts['nome_canal'] = daily_accounts[account_column]
            accounts.append(daily_accounts)
        
        if data_videos is not None and account_column in data_videos.columns:
            videos_accounts = data_videos[[account_column]].drop_duplicates()
            if 'nome_canal' not in videos_accounts.columns:
                videos_accounts['nome_canal'] = videos_accounts[account_column]
            accounts.append(videos_accounts)
        
        # Mesclar informações de contas
        unique_accounts = pd.concat(accounts).drop_duplicates(subset=[account_column])
        
        # Adicionar opção para visualizar todas as contas
        all_accounts_option = pd.DataFrame({
            account_column: ['all'],
            'nome_canal': ['Todos os Canais']
        })
        unique_accounts = pd.concat([all_accounts_option, unique_accounts])
        
        # Seletor de conta
        selected_account = st.sidebar.selectbox(
            "Selecione o Canal",
            options=unique_accounts[account_column].tolist(),
            format_func=lambda x: unique_accounts.loc[unique_accounts[account_column] == x, 'nome_canal'].iloc[0],
            index=0
        )
        
        if selected_account == 'all':
            # Mostrar dados de todas as contas
            st.header("Visão Geral - Todos os Canais")
            
            # Mostrar métricas por conta
            st.header("Métricas por Canal")
            
            # Exibir métricas para cada conta
            for _, account in unique_accounts[unique_accounts[account_column] != 'all'].iterrows():
                account_id = account[account_column]
                account_name = account['nome_canal']
                
                st.markdown(f"""
                <div class="account-header">
                    <h3>{account_name} (ID: {account_id})</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Criar abas para diferentes visualizações
                tab1, tab2, tab3 = st.tabs(["Canal", "Métricas Diárias", "Vídeos"])
                
                with tab1:
                    create_channel_visualizations(data_channel, account_id)
                
                with tab2:
                    create_daily_visualizations(data_daily, account_id)
                
                with tab3:
                    create_videos_visualizations(data_videos, account_id)
        else:
            # Mostrar dados da conta selecionada
            account_name = unique_accounts.loc[unique_accounts[account_column] == selected_account, 'nome_canal'].iloc[0]
            st.header(f"Canal: {account_name}")
            
            # Criar abas para diferentes visualizações
            tab1, tab2, tab3 = st.tabs(["Canal", "Métricas Diárias", "Vídeos"])
            
            with tab1:
                create_channel_visualizations(data_channel, selected_account)
            
            with tab2:
                create_daily_visualizations(data_daily, selected_account)
            
            with tab3:
                create_videos_visualizations(data_videos, selected_account)
    else:
        # Apenas uma conta, mostrar dados diretamente
        # Criar abas para diferentes visualizações
        tab1, tab2, tab3 = st.tabs(["Canal", "Métricas Diárias", "Vídeos"])
        
        with tab1:
            create_channel_visualizations(data_channel)
        
        with tab2:
            create_daily_visualizations(data_daily)
        
        with tab3:
            create_videos_visualizations(data_videos)

if __name__ == "__main__":
    main()
