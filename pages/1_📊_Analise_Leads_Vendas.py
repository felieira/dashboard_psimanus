import gspread
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import locale
from datetime import datetime
import os
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import re

def create_comparison_analysis(dados_filtrados_vendas, dados_filtrados_leads):
    # Mapping of similar fields between leads and sales
    field_mapping = {
        'Idade': {
            'leads': 'Qual a sua idade?',
            'vendas': 'Qual a sua idade?'
        },
        'Estado Civil': {
            'leads': 'Qual é o seu estado civil?',
            'vendas': 'Qual é o seu estado civil?'
        },
        'Escolaridade': {
            'leads': 'Qual é o seu nível de escolaridade?',
            'vendas': 'Qual é o seu nível de escolaridade?'
        },
        'Experiência com TCC': {
            'leads': 'Já fez terapia com uma psicóloga da abordagem da TCC (Terapia Cognitivo Comportamental) antes?',
            'vendas': 'Já fez terapia com uma psicóloga da abordagem da TCC Terapia Cognitivo Comportamental antes?'
        },
        'Motivo Terapia': {
            'leads': 'Qual seria o principal motivo para buscar terapia?',
            'vendas': 'Qual seria o principal motivo para buscar terapia?'
        },
        'Renda': {
            'leads': 'Selecione a sua média de renda familiar.',
            'vendas': 'Selecione a sua média de renda familiar.'
        },
        'Estado Emocional': {
            'leads': 'Como você se sente hoje com relação a suas emoções e relacionamentos?',
            'vendas': 'Como você se sente hoje com relação a suas emoções e relacionamentos?'
        },
        'Maior Desafio': {
            'leads': 'Com base na sua resposta anterior, qual está sendo o seu maior desafio?',
            'vendas': 'Com base na sua resposta anterior, qual está sendo o seu maior desafio?'
        },
        'Capacidade de Lidar': {
            'leads': 'Você se sente capaz de lidar com as demandas diárias ou está se sentindo sobrecarregado(a)?',
            'vendas': 'Você se sente capaz de lidar com as demandas diárias ou está se sentindo sobrecarregado(a)?'
        },
        'Necessidade de Ajuda': {
            'leads': 'Você sente que precisa de ajuda para lidar com essas dificuldades?',
            'vendas': 'Você sente que precisa de ajuda para lidar com essas dificuldades?'
        },
        'Investimento': {
            'leads': 'Escolha o investimento ideal para você:',
            'vendas': 'Escolha o investimento ideal para você:'
        },
        'Origem': {
            'leads': 'utm_source',
            'vendas': 'Source'
        },
        'Meio': {
            'leads': 'utm_medium',
            'vendas': 'Medium'
        },
        'Campanha': {
            'leads': 'utm_campaign',
            'vendas': 'Campaign'
        }
    }

    comparisons = {}
    
    for field_name, field_data in field_mapping.items():
        leads_field = field_data['leads']
        vendas_field = field_data['vendas']
        
        leads_dist = dados_filtrados_leads[leads_field].value_counts().to_dict()
        total_leads = len(dados_filtrados_leads)
        
        vendas_dist = dados_filtrados_vendas[vendas_field].value_counts().to_dict()
        total_vendas = len(dados_filtrados_vendas)
        
        all_values = set(leads_dist.keys()) | set(vendas_dist.keys())
        
        comparison_data = []
        for value in all_values:
            leads_count = leads_dist.get(value, 0)
            vendas_count = vendas_dist.get(value, 0)
            leads_percent = (leads_count / total_leads * 100) if total_leads > 0 else 0
            vendas_percent = (vendas_count / total_vendas * 100) if total_vendas > 0 else 0
            conversion_rate = (vendas_count / leads_count * 100) if leads_count > 0 else 0
            
            comparison_data.append({
                'Valor': value,
                'Qtd Leads': leads_count,
                '% Leads': round(leads_percent, 2),
                'Qtd Vendas': vendas_count,
                '% Vendas': round(vendas_percent, 2),
                'Taxa Conversão (%)': round(conversion_rate, 2)
            })
        
        # Criar DataFrame e ordenar por taxa de conversão
        df = pd.DataFrame(comparison_data)
        # Ordenar excluindo a linha de total
        df_sem_total = df.sort_values('Taxa Conversão (%)', ascending=False)
        
        # Adicionar totais ao final do DataFrame
        totals = pd.DataFrame([{
            'Valor': 'TOTAL',
            'Qtd Leads': total_leads,
            '% Leads': 100,
            'Qtd Vendas': total_vendas,
            '% Vendas': 100,
            'Taxa Conversão (%)': (total_vendas / total_leads * 100) if total_leads > 0 else 0
        }])
        
        # Concatenar mantendo a ordem
        df = pd.concat([df_sem_total, totals])
        
        comparisons[field_name] = df
    
    return comparisons

def create_word_clouds(dados_filtrados_leads, dados_filtrados_vendas):
    # Campos para análise
    campos = {
        'emocional': 'Como você se sente hoje com relação a suas emoções e relacionamentos?',
        'desafio': 'Com base na sua resposta anterior, qual está sendo o seu maior desafio?'
    }
    
    # Stop words expandidas para cobrir ambos os contextos
    stop_words = set(['e', 'de', 'a', 'o', 'que', 'em', 'para', 'com', 'não', 'uma', 'os', 'no', 'se', 
                     'na', 'por', 'mais', 'as', 'me', 'meu', 'minha', 'muito', 'bem', 'mal', 'hoje', 
                     'sinto', 'estou', 'está', 'vezes', 'ser', 'ter', 'também', 'ainda', 'isso', 'este',
                     'esta', 'esse', 'essa', 'porque', 'pois', 'como', 'mas', 'ou', 'quando', 'onde',
                     'quem', 'qual', 'meus', 'minhas', 'seu', 'sua', 'seus', 'suas', 'pelo', 'pela'])
    
    def limpar_texto(texto):
        # Remover pontuações e números
        texto = re.sub(r'[^\w\s]', ' ', texto)
        texto = re.sub(r'\d+', ' ', texto)
        # Remover stopwords
        palavras = texto.split()
        palavras = [p for p in palavras if p not in stop_words and len(p) > 2]
        return ' '.join(palavras)
    
    word_clouds = {}
    
    for campo_nome, campo in campos.items():
        # Preparar textos para leads e vendas
        leads_text = ' '.join(dados_filtrados_leads[campo].fillna('').astype(str).str.lower())
        vendas_text = ' '.join(dados_filtrados_vendas[campo].fillna('').astype(str).str.lower())
        
        # Limpar textos
        leads_text = limpar_texto(leads_text)
        vendas_text = limpar_texto(vendas_text)
        
        # Criar nuvens de palavras
        wc_leads = WordCloud(
            width=800, 
            height=400,
            background_color='white',
            colormap='Blues',
            max_words=50,
            min_font_size=10,
            random_state=42
        ).generate(leads_text)
        
        wc_vendas = WordCloud(
            width=800, 
            height=400,
            background_color='white',
            colormap='Greens',
            max_words=50,
            min_font_size=10,
            random_state=42
        ).generate(vendas_text)
        
        word_clouds[campo_nome] = (wc_leads, wc_vendas)
    
    return word_clouds

def main():
    # Configurar o idioma para português
    try:
        locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
    except locale.Error:
        st.warning("Não foi possível configurar o locale pt_BR.UTF-8. Usando locale padrão.")

    # Início do bloco try principal
    try:
        # Obter a data atual
        hoje = datetime.today()
        
        # Configuração de acesso ao Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Verificar se o arquivo de credenciais existe
        creds_path = './credenciais.json'
        if not os.path.exists(creds_path):
            st.error(f"Arquivo de credenciais não encontrado em: {creds_path}")
            return
            
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)

        # Carregar as planilhas com tratamento de erro
        try:
            sheet_vendas = client.open("[PAX] CENTRAL DADOS").worksheet('central_vendas')
            sheet_leads = client.open("[PAX] CENTRAL DADOS").worksheet('central_leads')
        except gspread.exceptions.SpreadsheetNotFound:
            st.error("Planilha não encontrada. Verifique o nome da planilha e as permissões.")
            return
        except Exception as e:
            st.error(f"Erro ao acessar as planilhas: {str(e)}")
            return

        # Carregar dados com tratamento de erro
        try:
            data_vendas = pd.DataFrame(sheet_vendas.get_all_records())
            data_leads = pd.DataFrame(sheet_leads.get_all_records())
        except Exception as e:
            st.error(f"Erro ao carregar os dados: {str(e)}")
            return

        # Converter e limpar datas
        try:
            data_vendas["Data"] = pd.to_datetime(data_vendas["Data"], dayfirst=True)
            data_leads["Submitted At"] = pd.to_datetime(data_leads["Submitted At"], dayfirst=True)
        except Exception as e:
            st.error(f"Erro ao processar as datas: {str(e)}")
            return

        # Interface do Streamlit
        st.title("Análise de Vendas e Leads")
        
        # Inputs para o usuário selecionar o período
        st.sidebar.header("Escolha o período")
        data_inicio = st.sidebar.date_input("Data de Início", value=datetime(hoje.year, hoje.month, 1))
        data_fim = st.sidebar.date_input("Data de Fim", value=hoje)

        # Converter as datas selecionadas para datetime
        data_inicio = pd.to_datetime(data_inicio)
        data_fim = pd.to_datetime(data_fim)

        # Filtrar os dados
        dados_filtrados_vendas = data_vendas[
            (data_vendas["Data"] >= data_inicio) & 
            (data_vendas["Data"] <= data_fim) &
            (data_vendas["Status"] == "Pago") &
            (data_vendas["Recebedores"] == "Recebedor padrão")
        ]

        dados_filtrados_leads = data_leads[
            (data_leads["Submitted At"] >= data_inicio) & 
            (data_leads["Submitted At"] <= data_fim)
        ]

        # Criar coluna de mês/ano para ambos os dataframes
        dados_filtrados_vendas['mes_ano'] = dados_filtrados_vendas['Data'].dt.strftime('%m/%Y')
        dados_filtrados_leads['mes_ano'] = dados_filtrados_leads['Submitted At'].dt.strftime('%m/%Y')

        # Contar leads por mês
        leads_por_mes = dados_filtrados_leads.groupby('mes_ano').size().reset_index(name='Quantidade de Leads')

        # Contar vendas por mês
        vendas_por_mes = dados_filtrados_vendas.groupby('mes_ano').size().reset_index(name='Quantidade de Vendas')

        # Mesclar os dois dataframes
        comparativo = pd.merge(leads_por_mes, vendas_por_mes, on='mes_ano', how='outer').fillna(0)
        
        # Ordenar por mês/ano
        comparativo['mes_ano_date'] = pd.to_datetime(comparativo['mes_ano'], format='%m/%Y')
        comparativo = comparativo.sort_values('mes_ano_date')
        comparativo = comparativo.drop('mes_ano_date', axis=1)

        # Calcular taxa de conversão
        comparativo['Taxa de Conversão (%)'] = (comparativo['Quantidade de Vendas'] / comparativo['Quantidade de Leads'] * 100).round(2)

        # Mostrar métricas gerais
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Leads no Período", f"{int(comparativo['Quantidade de Leads'].sum())}")
        with col2:
            st.metric("Total de Vendas no Período", f"{int(comparativo['Quantidade de Vendas'].sum())}")
        with col3:
            taxa_conversao_total = (comparativo['Quantidade de Vendas'].sum() / comparativo['Quantidade de Leads'].sum() * 100)
            st.metric("Conversão no Período", f"{taxa_conversao_total:.2f}%")

        # Exibir o comparativo mensal
        st.write("### Comparativo Mensal de Leads e Vendas")
        st.dataframe(comparativo.style.format({
            'Quantidade de Leads': '{:.0f}',
            'Quantidade de Vendas': '{:.0f}',
            'Taxa de Conversão (%)': '{:.2f}%'
        }))

        # Criar e exibir análise comparativa detalhada
        comparisons = create_comparison_analysis(dados_filtrados_vendas, dados_filtrados_leads)

        st.write("### Análise Detalhada por Campo")
        
        for field_name, comparison_df in comparisons.items():
            st.write(f"#### {field_name}")
            
            # Reset do índice para garantir índices únicos
            comparison_df = comparison_df.reset_index(drop=True)
            
            # Função para destacar a linha TOTAL
            def highlight_total(row):
                if row['Valor'] == 'TOTAL':
                    return ['background-color: #e6f3ff'] * len(row)
                return [''] * len(row)
            
            st.dataframe(comparison_df.style
                        .apply(highlight_total, axis=1)
                        .format({
                            'Qtd Leads': '{:.0f}',
                            '% Leads': '{:.2f}%',
                            'Qtd Vendas': '{:.0f}',
                            '% Vendas': '{:.2f}%',
                            'Taxa Conversão (%)': '{:.2f}%'
                        }))
            
            # Adicionar espaço entre as tabelas
            st.write("")
            
        # Criar e exibir nuvens de palavras
        st.write("### Análise de Texto - Nuvens de Palavras")
        
        word_clouds = create_word_clouds(dados_filtrados_leads, dados_filtrados_vendas)
        
        # Estado Emocional
        st.write("#### Estado Emocional")
        st.write("Visualização das palavras mais frequentes nas respostas sobre estado emocional")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("##### Leads")
            fig_leads, ax_leads = plt.subplots(figsize=(10, 6))
            ax_leads.imshow(word_clouds['emocional'][0], interpolation='bilinear')
            ax_leads.axis('off')
            st.pyplot(fig_leads)
            
        with col2:
            st.write("##### Compradores")
            fig_vendas, ax_vendas = plt.subplots(figsize=(10, 6))
            ax_vendas.imshow(word_clouds['emocional'][1], interpolation='bilinear')
            ax_vendas.axis('off')
            st.pyplot(fig_vendas)
        
        # Maior Desafio
        st.write("#### Maior Desafio")
        st.write("Visualização das palavras mais frequentes nas respostas sobre os maiores desafios")
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.write("##### Leads")
            fig_leads2, ax_leads2 = plt.subplots(figsize=(10, 6))
            ax_leads2.imshow(word_clouds['desafio'][0], interpolation='bilinear')
            ax_leads2.axis('off')
            st.pyplot(fig_leads2)
            
        with col4:
            st.write("##### Compradores")
            fig_vendas2, ax_vendas2 = plt.subplots(figsize=(10, 6))
            ax_vendas2.imshow(word_clouds['desafio'][1], interpolation='bilinear')
            ax_vendas2.axis('off')
            st.pyplot(fig_vendas2)

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {str(e)}")

if __name__ == "__main__":
    main()
