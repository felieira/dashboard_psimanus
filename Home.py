import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import locale
import os
import plotly.express as px

st.set_page_config(
    page_title="Dashboard PSI - Resumo",
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
        background-color: #fff6f6 !important;
        padding: 10px;
        border-radius: 20px;
        margin-bottom: 20px;
        border: none !important;
    }
    
    /* Pills */
    [role="tab"] {
        background-color: #FFFFFF !important;
        color: #6d7174 !important;
        border: 1px solid rgba(255, 102, 108, 0.2) !important;
        border-radius: 20px !important;
        padding: 8px 16px !important;
        margin: 0 5px !important;
        font-size: 14px !important;
        transition: all 0.2s ease !important;
    }
    
    /* Pill selecionada */
    [role="tab"][aria-selected="true"] {
        background-color: #ff666c !important;
        color: white !important;
        border-color: #ff666c !important;
    }
    
    /* Hover da pill */
    [role="tab"]:hover {
        background-color: #fff6f6 !important;
        border-color: #ff666c !important;
    }
    
    /* Métricas */
    [data-testid="metric-container"] {
        background-color: #fff6f6;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(255, 102, 108, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

def get_week_dates(year, month):
    try:
        # Primeiro dia do mês
        first_day = datetime(year, month, 1)
        
        # Último dia do mês
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        last_day = next_month - timedelta(days=1)
        
        periods = [{
            'start': first_day,
            'end': last_day,
            'label': f"Mês Completo"
        }]
        
        # Encontrar o último domingo antes ou no primeiro dia do mês
        start_date = first_day - timedelta(days=(first_day.weekday() + 1) % 7)
        
        # Encontrar o primeiro sábado após ou no último dia do mês
        end_date = last_day + timedelta(days=(5 - last_day.weekday() + 7) % 7)
        
        current_date = start_date
        week_num = 1
        
        while current_date <= end_date:
            week_end = current_date + timedelta(days=6)
            periods.append({
                'start': max(current_date, first_day),
                'end': min(week_end, last_day),
                'label': f"Semana {week_num}"
            })
            current_date = week_end + timedelta(days=1)
            week_num += 1
        
        return periods
    
    except Exception as e:
        print(f"Erro ao gerar períodos: {str(e)}")
        return [{
            'start': datetime(year, month, 1),
            'end': (datetime(year, month + 1, 1) if month < 12 
                   else datetime(year + 1, 1, 1)) - timedelta(days=1),
            'label': "Mês Atual"
        }]

def get_comparison_metrics(data_vendas, data_leads, selected_start, selected_end):
    try:
        # Calcular o período anterior mantendo os mesmos dias
        days_in_period = (selected_end - selected_start).days
        
        # Calcular datas do período anterior
        previous_end = selected_start - timedelta(days=1)  # Dia anterior ao início do período atual
        previous_start = previous_end - timedelta(days=days_in_period)
        
        print(f"\nPeríodos de comparação:")
        print(f"Atual: {selected_start.strftime('%d/%m/%Y')} a {selected_end.strftime('%d/%m/%Y')}")
        print(f"Anterior: {previous_start.strftime('%d/%m/%Y')} a {previous_end.strftime('%d/%m/%Y')}")
        
        # Período atual - Leads
        current_leads_mask = (data_leads['Submitted At'] >= selected_start) & \
                           (data_leads['Submitted At'] <= selected_end)
        leads_current = len(data_leads.loc[current_leads_mask])
        
        # Período anterior - Leads
        previous_leads_mask = (data_leads['Submitted At'] >= previous_start) & \
                            (data_leads['Submitted At'] <= previous_end)
        leads_previous = len(data_leads.loc[previous_leads_mask])
        
        # Período atual - Vendas
        current_vendas_mask = (data_vendas['Data'] >= selected_start) & \
                            (data_vendas['Data'] <= selected_end) & \
                            (data_vendas['Status'] == 'Pago')
        
        # Período anterior - Vendas
        previous_vendas_mask = (data_vendas['Data'] >= previous_start) & \
                             (data_vendas['Data'] <= previous_end) & \
                             (data_vendas['Status'] == 'Pago')
        
        # Primeira Sessão
        primeira_sessao_current = len(data_vendas.loc[current_vendas_mask & 
                                                    (data_vendas['Recebedores'] == 'Recebedor padrão')])
        primeira_sessao_previous = len(data_vendas.loc[previous_vendas_mask & 
                                                     (data_vendas['Recebedores'] == 'Recebedor padrão')])
        
        # Primeiro Pacote
        primeiro_pacote_current = len(data_vendas.loc[current_vendas_mask & 
                                                    (data_vendas['Pacote'] == '1º Pacote')])
        primeiro_pacote_previous = len(data_vendas.loc[previous_vendas_mask & 
                                                     (data_vendas['Pacote'] == '1º Pacote')])
        
        # Cálculos de variação
        def calc_variation(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return ((current - previous) / previous) * 100
        
        leads_var = calc_variation(leads_current, leads_previous)
        sessao_var = calc_variation(primeira_sessao_current, primeira_sessao_previous)
        pacote_var = calc_variation(primeiro_pacote_current, primeiro_pacote_previous)
        
        print(f"\nComparações:")
        print(f"Leads: {leads_current} vs {leads_previous} = {leads_var:.1f}%")
        print(f"1ª Sessão: {primeira_sessao_current} vs {primeira_sessao_previous} = {sessao_var:.1f}%")
        print(f"1º Pacote: {primeiro_pacote_current} vs {primeiro_pacote_previous} = {pacote_var:.1f}%")
        
        return {
            'leads': (leads_current, leads_var, leads_previous),
            'sessao': (primeira_sessao_current, sessao_var, primeira_sessao_previous),
            'pacote': (primeiro_pacote_current, pacote_var, primeiro_pacote_previous)
        }
        
    except Exception as e:
        print(f"Erro ao calcular métricas: {str(e)}")
        return None

def create_daily_evolution_chart(data_vendas, data_leads, selected_start, selected_end):
    try:
        # Preparar dados para o gráfico usando loc
        leads_dia = (
            data_leads.loc[
                (data_leads["Submitted At"] >= selected_start) &
                (data_leads["Submitted At"] <= selected_end)
            ]
            .groupby(data_leads["Submitted At"].dt.date)
            .size()
            .reset_index(name="Leads")
        )
        leads_dia["Submitted At"] = pd.to_datetime(leads_dia["Submitted At"]).dt.strftime('%d/%m/%Y')
        
        sessao_1_dia = (
            data_vendas.loc[
                (data_vendas["Recebedores"] == "Recebedor padrão") &
                (data_vendas["Data"] >= selected_start) &
                (data_vendas["Data"] <= selected_end)
            ]
            .groupby(data_vendas["Data"].dt.date)
            .size()
            .reset_index(name="Primeiras Sessões")
        )
        sessao_1_dia["Data"] = pd.to_datetime(sessao_1_dia["Data"]).dt.strftime('%d/%m/%Y')
        
        pacote_1_dia = (
            data_vendas.loc[
                (data_vendas["Pacote"] == "1º Pacote") &
                (data_vendas["Data"] >= selected_start) &
                (data_vendas["Data"] <= selected_end)
            ]
            .groupby(data_vendas["Data"].dt.date)
            .size()
            .reset_index(name="Primeiros Pacotes")
        )
        pacote_1_dia["Data"] = pd.to_datetime(pacote_1_dia["Data"]).dt.strftime('%d/%m/%Y')
        
        # Unir dados
        dados_grafico = (
            leads_dia.rename(columns={"Submitted At": "Data"})
            .merge(sessao_1_dia, on="Data", how="outer")
            .merge(pacote_1_dia, on="Data", how="outer")
            .fillna(0)
        )
        
        return dados_grafico
        
    except Exception as e:
        print(f"Erro ao criar dados do gráfico: {str(e)}")
        return pd.DataFrame()

def main():
    try:
        locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
    except locale.Error:
        st.warning("Não foi possível configurar o locale pt_BR.UTF-8. Usando locale padrão.")

    st.title("📊 Dashboard PSI - Resumo Geral")

    try:
        # Conexão com Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_path = './credenciais.json'
        
        if not os.path.exists(creds_path):
            st.error(f"Arquivo de credenciais não encontrado em: {creds_path}")
            return
            
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)

        # Carregar dados
        sheet_vendas = client.open("[PAX] CENTRAL DADOS").worksheet('central_vendas')
        sheet_leads = client.open("[PAX] CENTRAL DADOS").worksheet('central_leads')
        
        data_vendas = pd.DataFrame(sheet_vendas.get_all_records())
        data_leads = pd.DataFrame(sheet_leads.get_all_records())
        
        # Converter datas
        data_vendas['Data'] = pd.to_datetime(data_vendas['Data'], dayfirst=True)
        data_leads['Submitted At'] = pd.to_datetime(data_leads['Submitted At'], dayfirst=True)
        
        # Obter mês e ano atual
        hoje = datetime.today()
        mes_atual = hoje.month
        ano_atual = hoje.year
        
        # Criar seletor de períodos
        periods = get_week_dates(ano_atual, mes_atual)
        if not periods:
            st.error("Não foi possível gerar os períodos do mês.")
            return
            
        # Extrair labels dos períodos
        period_labels = [period['label'] for period in periods]
        
        # Usar st.pills para seleção
        selected_period_label = st.pills(
            "Selecione o período",
            options=period_labels,
            default=period_labels[0]  # Mês completo como padrão
        )
        
        # Encontrar o período selecionado
        selected_period = next((period for period in periods if period['label'] == selected_period_label), None)
        if not selected_period:
            st.error("Período selecionado não encontrado.")
            return
            
        selected_start = selected_period['start']
        selected_end = selected_period['end']
        
        # Calcular métricas
        metrics = get_comparison_metrics(data_vendas, data_leads, selected_start, selected_end)
        
        if not metrics:
            st.error("Não foi possível calcular as métricas.")
            return

        # Exibir métricas
        col1, col2, col3 = st.columns(3)

        # Formatação e exibição das métricas
        if isinstance(metrics, dict) and all(key in metrics for key in ['leads', 'sessao', 'pacote']):
            # Verifica se há leads suficientes
            if len(metrics['leads']) >= 3:
                col1.metric(
                    "Total de Leads no período",
                    metrics['leads'][0],
                    f"{metrics['leads'][1]:+.1f}% (ant: {metrics['leads'][2]})"
                )
            
            # Verifica se há sessões suficientes
            if len(metrics['sessao']) >= 3:
                col2.metric(
                    "Total de 1ª Sessões no período",
                    metrics['sessao'][0],
                    f"{metrics['sessao'][1]:+.1f}% (ant: {metrics['sessao'][2]})"
                )
            
            # Verifica se há pacotes suficientes
            if len(metrics['pacote']) >= 3:
                col3.metric(
                    "Total de 1º Pacotes no período",
                    metrics['pacote'][0],
                    f"{metrics['pacote'][1]:+.1f}% (ant: {metrics['pacote'][2]})"
                )
            
            # Criar e exibir gráfico apenas se temos métricas válidas
            dados_grafico = create_daily_evolution_chart(data_vendas, data_leads, selected_start, selected_end)
            
            if not dados_grafico.empty:
                fig = px.line(
                    dados_grafico.melt(id_vars="Data", var_name="Categoria", value_name="Quantidade"),
                    x="Data",
                    y="Quantidade",
                    color="Categoria",
                    title="Evolução Diária de Leads, 1ª Sessões e 1º Pacotes",
                    markers=True
                )
                
                fig.update_layout(
                    xaxis_title="Dia do Mês",
                    yaxis_title="Quantidade",
                    legend_title="Categoria",
                    template="plotly_white",
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {str(e)}")
        print(f"Erro detalhado: {str(e)}")
        return

if __name__ == "__main__":
    main()
