# Instruções para Execução do Dashboard PSI

Este documento contém instruções para executar o Dashboard PSI que acessa dados do Google Sheets.

## Requisitos

Para executar o dashboard, você precisará ter instalado:

1. Python 3.6 ou superior
2. As seguintes bibliotecas Python:
   - streamlit
   - pandas
   - gspread
   - oauth2client
   - plotly
   - matplotlib
   - wordcloud

## Instalação das Dependências

Caso não tenha as bibliotecas necessárias instaladas, você pode instalá-las usando o pip:

```bash
pip install streamlit pandas gspread oauth2client plotly matplotlib wordcloud
```

## Estrutura de Arquivos

O dashboard está organizado da seguinte forma:

- `Home.py` - Página principal com resumo geral de leads e vendas
- `pages/1_📊_Analise_Leads_Vendas.py` - Página de análise detalhada
- `credenciais.json` - Arquivo de credenciais para acesso ao Google Sheets

## Executando o Dashboard

1. Extraia o arquivo `dashboard_psi.zip` em uma pasta de sua preferência
2. Abra um terminal ou prompt de comando
3. Navegue até a pasta onde os arquivos foram extraídos
4. Execute o comando:

```bash
streamlit run Home.py
```

5. O dashboard será iniciado e abrirá automaticamente em seu navegador padrão
6. Caso não abra automaticamente, acesse o endereço indicado no terminal (geralmente http://localhost:8501)

## Funcionalidades do Dashboard

### Página Principal (Home.py)

- Resumo geral de leads e vendas
- Métricas comparativas entre o período atual e o anterior
- Gráfico de evolução diária
- Seletor de períodos por semanas do mês

### Página de Análise Detalhada (1_📊_Analise_Leads_Vendas.py)

- Comparativo mensal de leads e vendas
- Análise detalhada por campo (idade, estado civil, escolaridade, etc.)
- Taxas de conversão por diferentes atributos
- Nuvens de palavras para análise de texto de respostas abertas

## Observações Importantes

- O arquivo de credenciais incluído já está configurado para acessar a planilha "[PAX] CENTRAL DADOS"
- Certifique-se de que o arquivo de credenciais tem permissões para acessar a planilha
- O dashboard acessa as abas 'central_vendas' e 'central_leads' da planilha

## Suporte

Caso encontre algum problema na execução do dashboard, verifique:

1. Se todas as dependências foram instaladas corretamente
2. Se o arquivo de credenciais está no local correto
3. Se a conta de serviço nas credenciais tem acesso à planilha

Para qualquer dúvida adicional, entre em contato.
